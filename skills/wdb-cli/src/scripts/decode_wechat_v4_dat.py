#!/usr/bin/env python3
"""Decode a WeChat 4.x encrypted media file (`.dat`, header 0708 5632) to an image.

Format (WeChat 4.x, V2 container):

    bytes[0:6]    07 08 56 32 08 07           magic
    bytes[6:10]   uint32le  aes_size           plaintext length of the AES section
    bytes[10:14]  uint32le  xor_size           tail length (single-byte XOR)
    bytes[14]     flags (0x01)
    bytes[15:15+aligned]             AES-128-ECB(ciphertext), PKCS#7 padded
    bytes[15+aligned:len-xor_size]   plaintext passthrough
    bytes[len-xor_size:len]          tail, each byte XOR key_material.xor_key

`aligned = (aes_size // 16 + 1) * 16`: PKCS#7 always adds at least one byte, so the
ciphertext is the next 16-byte block boundary *strictly above* aes_size. When aes_size is
already a multiple of 16 the encrypted span is one full block longer, and reading it as
plaintext corrupts the middle of the image (PNG IDAT CRC fails) while still looking
decodable at a glance — always verify with the decoded file's own checksums.

Key material is derived from the per-account kvcomm code table that WeChat keeps in
`<xwechat base>/app_data/net/kvcomm/key_<code>_*`:

    aes_key  = md5(f"{code}{wxid}").hexdigest()[:16].encode()   # ASCII, not hex-decoded
    xor_key  = code & 0xff

This mirrors `decode_wechat_v4_dat_with_key` in wdb-pro
(`packages/wechat-db-manager/src-tauri/src/database.rs`). Used by lov-wdb-cli to read
images that arrive as messages, e.g. the 蒋程宇 ten-city poster.

Only the V2 container is supported; V1 uses a bundled constant key that is not shipped here.

The decrypted payload is not always JPEG/PNG. Mid-size and HD images are often `wxgf`:
WeChat's own wrapper around Annex-B HEVC. After a small header (and sometimes an ICC
profile) it holds one colour stream, or a grayscale alpha stream *followed by* the colour
stream. Each stream starts with a VPS NAL (`00 00 00 01 40 01`); streams are told apart
by ffprobe's `pix_fmt`, never by order. ffmpeg turns the colour stream into JPEG, or
alpha-merges both into PNG. Without ffmpeg/ffprobe a wxgf file fails with a clear error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

HEADER_LEN = 0x0F
MAGIC = b"\x07\x08V2\x08\x07"
IMAGE_SIGNATURES: List[Tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"RIFF", "webp"),
    (b"BM", "bmp"),
    (b"wxgf", "wxgf"),
]
HEVC_VPS = b"\x00\x00\x00\x01\x40\x01"


class DecodeError(RuntimeError):
    """Raised when the container or the key material cannot be used."""


def aes_ecb_decrypt(key: bytes, data: bytes) -> bytes:
    """AES-128-ECB decrypt, preferring `cryptography` and falling back to openssl."""
    if len(data) % 16 or not data:
        raise DecodeError("ciphertext length is not a positive multiple of 16")
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        pass
    else:
        decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
        return decryptor.update(data) + decryptor.finalize()

    openssl = shutil.which("openssl")
    if not openssl:
        raise DecodeError("need either the `cryptography` package or an `openssl` binary")
    proc = subprocess.run(
        [openssl, "enc", "-d", "-aes-128-ecb", "-nopad", "-K", key.hex()],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise DecodeError(f"openssl failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def strip_pkcs7(data: bytes) -> bytes:
    if not data:
        return data
    pad = data[-1]
    if 0 < pad <= 16 and data[-pad:] == bytes([pad]) * pad:
        return data[:-pad]
    return data


def image_kind(data: bytes) -> Optional[str]:
    for signature, kind in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return kind
    return None


def png_chunk_crc_ok(data: bytes) -> Optional[bool]:
    """Validate every PNG chunk CRC. Returns None when the payload is not a PNG.

    A wrong AES span still yields a file that starts with the PNG signature, so the chunk
    CRCs are the cheapest way to prove the middle of the image was decrypted, not copied.
    """
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    import zlib

    offset = 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            return False
        payload = data[offset + 8 : offset + 8 + length]
        expected = struct.unpack(">I", data[offset + 8 + length : end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected:
            return False
        offset = end
        if kind == b"IEND":
            return offset == len(data)
    return False


def wxgf_streams(payload: bytes) -> List[bytes]:
    starts = []
    offset = payload.find(HEVC_VPS)
    while offset != -1:
        starts.append(offset)
        offset = payload.find(HEVC_VPS, offset + len(HEVC_VPS))
    if not starts:
        raise DecodeError("wxgf payload holds no HEVC stream (no VPS start code)")
    bounds = starts + [len(payload)]
    return [payload[bounds[i] : bounds[i + 1]] for i in range(len(starts))]


def convert_wxgf(payload: bytes) -> Tuple[bytes, str, dict]:
    """Render a wxgf payload to JPEG (colour only) or PNG (colour + alpha) with ffmpeg."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise DecodeError("wxgf (HEVC) image needs `ffmpeg` and `ffprobe` on PATH")
    streams = wxgf_streams(payload)
    with tempfile.TemporaryDirectory(prefix="wxgf-") as workdir:
        colour: Optional[Path] = None
        alpha: Optional[Path] = None
        for index, stream in enumerate(streams):
            path = Path(workdir) / f"stream{index}.hevc"
            path.write_bytes(stream)
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-f", "hevc", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            pix_fmt = probe.stdout.decode().strip()
            if pix_fmt.startswith("gray"):
                alpha = alpha or path
            elif pix_fmt:
                colour = colour or path
        if colour is None:
            raise DecodeError("wxgf payload has no decodable colour stream")
        kind = "png" if alpha else "jpg"
        target = Path(workdir) / f"out.{kind}"
        command = [ffmpeg, "-v", "error", "-y", "-f", "hevc", "-i", str(colour)]
        if alpha:
            command += ["-f", "hevc", "-i", str(alpha), "-filter_complex", "[0:v][1:v]alphamerge"]
        else:
            command += ["-q:v", "2"]
        command += ["-frames:v", "1", str(target)]
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0 or not target.is_file() or not target.stat().st_size:
            raise DecodeError(f"ffmpeg could not render wxgf: {proc.stderr.decode(errors='replace').strip()}")
        return target.read_bytes(), kind, {"container": "wxgf", "streams": len(streams), "alpha": bool(alpha)}


def parse_container(raw: bytes) -> Tuple[int, int, int, int]:
    if len(raw) <= HEADER_LEN:
        raise DecodeError("file is smaller than the 15-byte container header")
    if not raw.startswith(MAGIC):
        if raw.startswith(b"\x07\x08V1"):
            raise DecodeError("this is a WeChat 4.x V1 container; its bundled key is not shipped")
        raise DecodeError("not a WeChat 4.x V2 container (expected magic 07 08 56 32 08 07)")
    aes_size, xor_size = struct.unpack("<II", raw[6:14])
    aligned = (aes_size // 16 + 1) * 16
    aes_end = HEADER_LEN + aligned
    raw_end = len(raw) - xor_size
    if aes_end > len(raw) or aes_end > raw_end:
        raise DecodeError(f"inconsistent container sizes: aes={aes_size} xor={xor_size} len={len(raw)}")
    return aes_size, xor_size, aes_end, raw_end


def decode_with_key(raw: bytes, aes_key: bytes, xor_key: int) -> bytes:
    _aes_size, _xor_size, aes_end, raw_end = parse_container(raw)
    plain = strip_pkcs7(aes_ecb_decrypt(aes_key, raw[HEADER_LEN:aes_end]))
    plain += raw[aes_end:raw_end]
    plain += bytes(byte ^ xor_key for byte in raw[raw_end:])
    return plain


def xwechat_base_from_path(path: Path) -> Optional[Path]:
    parts = list(path.resolve().parts)
    if "xwechat_files" not in parts:
        return None
    index = parts.index("xwechat_files")
    if index + 1 >= len(parts):
        return None
    return Path(*parts[: index + 2])


def kvcomm_dirs(xwechat_base: Path) -> List[Path]:
    parts = list(xwechat_base.resolve().parts)
    candidates: List[Path] = []
    if "xwechat_files" in parts:
        index = parts.index("xwechat_files")
        documents_root = Path(*parts[:index]) if index else Path("/")
        candidates.append(documents_root / "app_data/net/kvcomm")
        candidates.append(documents_root / "xwechat/net/kvcomm")
        if index >= 1:
            container_root = Path(*parts[: index - 1]) if index - 1 else Path("/")
            candidates.append(
                container_root
                / "Library/Application Support/com.tencent.xinWeChat/xwechat/net/kvcomm"
            )
            candidates.append(
                container_root / "Library/Application Support/com.tencent.xinWeChat/net/kvcomm"
            )
    seen, ordered = set(), []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def collect_codes(dirs: Iterable[Path]) -> List[int]:
    codes = set()
    for directory in dirs:
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.name.startswith("key_"):
                continue
            head = entry.name[len("key_"):].split("_", 1)[0]
            if head.isdigit():
                codes.add(int(head))
    return sorted(codes)


def wxid_candidates(xwechat_base: Path) -> List[str]:
    raw = xwechat_base.name
    ordered = []
    if raw.startswith("wxid_") and "_" in raw[5:]:
        ordered.append(f"wxid_{raw[5:].split('_', 1)[0]}")
    ordered.append(raw)
    seen, result = set(), []
    for item in ordered:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def decode_file(path: Path, codes: Optional[List[int]] = None) -> Tuple[bytes, dict]:
    raw = path.read_bytes()
    base = xwechat_base_from_path(path)
    if base is None:
        raise DecodeError("cannot locate the xwechat_files/<wxid> base from the given path")
    if codes is None:
        codes = collect_codes(kvcomm_dirs(base))
    if not codes:
        raise DecodeError("no kvcomm key_<code>_* entries found; pass --code explicitly")

    attempts = 0
    for code in codes:
        xor_key = code & 0xFF
        for wxid in wxid_candidates(base):
            aes_key = hashlib.md5(f"{code}{wxid}".encode()).hexdigest()[:16].encode()
            attempts += 1
            try:
                plain = decode_with_key(raw, aes_key, xor_key)
            except DecodeError:
                continue
            kind = image_kind(plain)
            if kind:
                if png_chunk_crc_ok(plain) is False:
                    continue
                extra = {"container": None, "streams": None, "alpha": None}
                if kind == "wxgf":
                    plain, kind, extra = convert_wxgf(plain)
                return plain, {
                    "code": code,
                    "wxid": wxid,
                    "xor_key": xor_key,
                    "kind": kind,
                    "attempts": attempts,
                    "png_crc_ok": png_chunk_crc_ok(plain),
                    **extra,
                }
    raise DecodeError(f"no key material decoded this file ({attempts} attempts)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a WeChat 4.x .dat media file into a viewable image."
    )
    parser.add_argument("input", help="path to the .dat file, e.g. msg/attach/<hash>/<YYYY-MM>/Img/<id>_h.dat")
    parser.add_argument(
        "-o",
        "--output",
        help="output image path (default: ./<input name>.<ext> in the current directory, never inside the WeChat data dir)",
    )
    parser.add_argument("--code", type=int, action="append", help="kvcomm code to try (repeatable); default: auto-detect")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    args = parser.parse_args(argv)

    path = Path(args.input).expanduser()
    if not path.is_file():
        raise SystemExit(f"input not found: {path}")

    try:
        plain, meta = decode_file(path, args.code)
    except DecodeError as exc:
        raise SystemExit(f"decode failed: {exc}")

    # Never default to writing inside the WeChat container: decoded copies belong outside it.
    target = Path(args.output).expanduser() if args.output else Path.cwd() / f"{path.stem}.{meta['kind']}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not args.output:
        stem, suffix = target.stem, target.suffix
        target = target.with_name(f"{stem}-decoded{suffix}")
    target.write_bytes(plain)

    report = {
        "status": "decoded",
        "input": str(path),
        "output": str(target),
        "bytes": len(plain),
        "image": meta["kind"],
        "code": meta["code"],
        "xor_key": meta["xor_key"],
        "attempts": meta["attempts"],
        "png_crc_ok": meta["png_crc_ok"],
        "container": meta["container"],
        "streams": meta["streams"],
        "alpha": meta["alpha"],
    }
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['status']}: {report['output']} ({report['image']}, {report['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
