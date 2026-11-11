#!/usr/bin/env python3
"""Create a static raster watermark as a Blu-ray PGS subtitle stream.

The video remains untouched and the generated SUP file is suitable as an
external image subtitle. An optional text lockup is rendered beside the source
Logo; the Logo pixels stay separate from the text palette until composition.
"""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont


TIME_RE = re.compile(
    r"^(?:(?P<hours>\d+):)?(?P<minutes>\d{1,2}):"
    r"(?P<seconds>\d{1,2})[.,](?P<fraction>\d{1,3})$"
)


DEFAULT_FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
    Path("/System/Library/Fonts/Hiragino Mincho ProN.ttc"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
)


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def parse_time(value: str) -> int:
    text = value.strip().replace(",", ".")
    match = TIME_RE.fullmatch(text)
    if match is None:
        fail(f"invalid time {value!r}; expected HH:MM:SS.mmm")
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    fraction = match.group("fraction").ljust(3, "0")[:3]
    return (((hours * 60) + minutes) * 60 + seconds) * 1000 + int(fraction)


def parse_size(value: str) -> Tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except ValueError:
        fail(f"invalid size {value!r}; expected WIDTHxHEIGHT")
    if width <= 0 or height <= 0 or width > 65535 or height > 65535:
        fail("video dimensions must be between 1 and 65535")
    return width, height


def parse_position(value: str) -> Tuple[int, int]:
    try:
        x_text, y_text = value.split(":", 1)
        x, y = int(x_text), int(y_text)
    except ValueError:
        fail(f"invalid position {value!r}; expected X:Y")
    if x < 0 or y < 0:
        fail("subtitle position must not be negative")
    return x, y


def parse_color(value: str) -> Tuple[int, int, int, int]:
    try:
        parsed = ImageColor.getcolor(value, "RGBA")
    except ValueError:
        fail(f"invalid text color {value!r}; expected #RRGGBB or #RRGGBBAA")
    return tuple(int(channel) for channel in parsed)


def resolve_font(path: Optional[str], size: int) -> ImageFont.FreeTypeFont:
    candidates = [Path(path).expanduser()] if path else []
    candidates.extend(DEFAULT_FONT_CANDIDATES)
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    requested = path or "a system font"
    fail(f"could not load {requested} for the raster lockup")


def quantize_alpha(mask: Image.Image, levels: int) -> Image.Image:
    if levels < 2 or levels > 256:
        fail("text alpha levels must be between 2 and 256")
    step = 255 / float(levels - 1)
    lut = [int(round(round(value / step) * step)) for value in range(256)]
    return mask.point(lut)


def reduce_pgs_palette(image: Image.Image) -> Image.Image:
    pixels = list(image.getdata())
    if len(set(pixels)) <= 254:
        return image
    quantize_enum = getattr(Image, "Quantize", Image)
    dither_enum = getattr(Image, "Dither", Image)
    return image.quantize(
        colors=254,
        method=quantize_enum.FASTOCTREE,
        dither=dither_enum.NONE,
    ).convert("RGBA")


def compose_lockup(
    logo: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    text_color: Tuple[int, int, int, int],
    gap: int,
    alpha_levels: int,
    rule: bool = True,
    rule_color: Tuple[int, int, int, int] = (217, 179, 117, 224),
    rule_gap: int = 8,
    rule_height: int = 2,
) -> Image.Image:
    if gap < 0:
        fail("Logo/text gap must not be negative")
    if rule and (rule_gap < 0 or rule_height <= 0):
        fail("watermark rule dimensions must be positive")
    if not text.strip():
        fail("raster lockup text must not be empty")
    logo = logo.convert("RGBA")
    probe = Image.new("L", (1, 1), 0)
    probe_draw = ImageDraw.Draw(probe)
    left, top, right, bottom = probe_draw.textbbox((0, 0), text, font=font)
    text_width = max(1, right - left)
    text_height = max(1, bottom - top)
    content_height = max(logo.height, text_height)
    rule_padding = rule_gap + rule_height if rule else 0
    canvas_width = logo.width + gap + text_width
    canvas_height = content_height + rule_padding

    mask = Image.new("L", (canvas_width, canvas_height), 0)
    draw = ImageDraw.Draw(mask)
    text_x = logo.width + gap - left
    text_y = rule_padding + (content_height - text_height) // 2 - top
    draw.text((text_x, text_y), text, font=font, fill=255)
    mask = quantize_alpha(mask, alpha_levels)

    text_layer = Image.new("RGBA", (canvas_width, canvas_height), text_color)
    text_layer.putalpha(
        Image.eval(mask, lambda value: int(round(value * text_color[3] / 255)))
    )
    composed = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    if rule:
        line_width = max(1, min(canvas_width, round(text_width * 0.86)))
        line = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        line_draw = ImageDraw.Draw(line)
        text_center_x = logo.width + gap + text_width / 2
        line_left = round(text_center_x - line_width / 2)
        line_draw.rectangle(
            (line_left, 0, line_left + line_width - 1, rule_height - 1),
            fill=rule_color,
        )
        composed.alpha_composite(line)
    shadow_mask = Image.new("L", (canvas_width, canvas_height), 0)
    shadow_draw = ImageDraw.Draw(shadow_mask)
    shadow_color = (24, 18, 12, 190)
    shadow_draw.text(
        (text_x + 1, text_y + 1),
        text,
        font=font,
        fill=255,
        stroke_width=1,
        stroke_fill=255,
    )
    shadow_mask = quantize_alpha(shadow_mask, min(8, alpha_levels))
    shadow = Image.new("RGBA", (canvas_width, canvas_height), shadow_color)
    shadow.putalpha(
        Image.eval(shadow_mask, lambda value: int(round(value * shadow_color[3] / 255)))
    )
    composed.alpha_composite(shadow)
    composed.alpha_composite(text_layer)
    composed.alpha_composite(
        logo,
        (0, rule_padding + (content_height - logo.height) // 2),
    )
    return composed


def segment(pts: int, segment_type: int, payload: bytes) -> bytes:
    if len(payload) > 65535:
        fail(f"PGS segment is too large: {len(payload)} bytes")
    # SUP/PGS stores timestamps in 90 kHz units and uses big-endian fields.
    return struct.pack(">2sIIBH", b"PG", pts, pts, segment_type, len(payload)) + payload


def ycbcr709(red: int, green: int, blue: int) -> Tuple[int, int, int]:
    y = round(16 + (65.481 * red + 128.553 * green + 24.966 * blue) / 255)
    cb = round(128 + (-37.797 * red - 74.203 * green + 112.0 * blue) / 255)
    cr = round(128 + (112.0 * red - 93.786 * green - 18.214 * blue) / 255)
    return tuple(max(0, min(255, value)) for value in (y, cr, cb))


def palette_and_indices(
    pixels: Sequence[Tuple[int, int, int, int]],
) -> Tuple[List[Tuple[int, int, int, int]], List[int]]:
    palette: List[Tuple[int, int, int, int]] = [(0, 0, 0, 0)]
    lookup = {palette[0]: 0}
    indices: List[int] = []
    for pixel in pixels:
        red, green, blue, alpha = pixel
        normalized = (red, green, blue, alpha) if alpha else palette[0]
        index = lookup.get(normalized)
        if index is None:
            if len(palette) >= 256:
                fail("raster watermark has more than 255 visible colors")
            index = len(palette)
            palette.append(normalized)
            lookup[normalized] = index
        indices.append(index)
    return palette, indices


def encode_zero_run(output: bytearray, run: int) -> None:
    while run:
        chunk = min(run, 0x3FFF)
        if chunk <= 0x3F:
            output.extend((0x00, chunk))
        else:
            output.extend((0x00, 0x40 | (chunk >> 8), chunk & 0xFF))
        run -= chunk


def encode_rle(indices: Sequence[int], width: int, height: int) -> bytes:
    output = bytearray()
    for row in range(height):
        line = indices[row * width : (row + 1) * width]
        column = 0
        while column < width:
            color = line[column]
            end = column + 1
            while end < width and line[end] == color:
                end += 1
            run = end - column
            if color == 0:
                encode_zero_run(output, run)
            else:
                # A literal non-zero palette index is one pixel in PGS RLE.
                # Splitting long runs this way keeps the encoder simple and
                # remains well within the segment size for a small watermark.
                output.extend(bytes([color]) * run)
            column = end
        # A zero-length run marks the end of one bitmap scanline.
        output.extend((0x00, 0x00))
    return bytes(output)


def palette_segment(palette: Iterable[Tuple[int, int, int, int]]) -> bytes:
    payload = bytearray((0, 0))  # palette id, palette version
    for color_id, (red, green, blue, alpha) in enumerate(palette):
        y, cr, cb = ycbcr709(red, green, blue)
        payload.extend((color_id, y, cr, cb, alpha))
    return bytes(payload)


def window_segment(x: int, y: int, width: int, height: int) -> bytes:
    return bytes((1, 0)) + struct.pack(">HHHH", x, y, width, height)


def presentation_segment(
    video_width: int,
    video_height: int,
    composition_number: int,
    state: int,
    palette_id: int,
    object_count: int,
    object_x: int = 0,
    object_y: int = 0,
    object_id: int = 1,
) -> bytes:
    payload = bytearray(
        struct.pack(
            ">HHBHBBBB",
            video_width,
            video_height,
            0,
            composition_number,
            state,
            0x80 if object_count else 0,
            palette_id,
            object_count,
        )
    )
    if object_count:
        payload.extend(struct.pack(">HBBHH", object_id, 0, 0xC0, object_x, object_y))
    return bytes(payload)


def object_segment(
    object_id: int,
    width: int,
    height: int,
    rle: bytes,
) -> bytes:
    # The PGS object-data length includes the four bytes for bitmap dimensions.
    payload = bytearray(struct.pack(">HBB", object_id, 0, 0xC0))
    payload.extend((len(rle) + 4).to_bytes(3, "big"))
    payload.extend(struct.pack(">HH", width, height))
    payload.extend(rle)
    return bytes(payload)


def build_sup(
    image_path: Path,
    output_path: Path,
    video_size: Tuple[int, int],
    position: Tuple[int, int],
    start_ms: int,
    end_ms: int,
    text: Optional[str] = None,
    font_path: Optional[str] = None,
    font_size: int = 24,
    text_color: Tuple[int, int, int, int] = (228, 197, 143, 255),
    logo_gap: int = 8,
    logo_height: int = 24,
    text_alpha_levels: int = 32,
) -> dict:
    if end_ms <= start_ms:
        fail("end time must be after start time")
    if logo_height <= 0:
        fail("Logo height must be positive")
    image = Image.open(image_path).convert("RGBA")
    if image.height != logo_height:
        logo_width = max(1, round(image.width * logo_height / image.height))
        resampling = getattr(Image, "Resampling", Image)
        image = image.resize((logo_width, logo_height), resampling.LANCZOS)
    rendered_logo_height = image.height
    if text is not None:
        if font_size <= 0:
            fail("text font size must be positive")
        image = compose_lockup(
            image,
            text,
            resolve_font(font_path, font_size),
            text_color,
            logo_gap,
            text_alpha_levels,
        )
    image_width, image_height = image.size
    video_width, video_height = video_size
    x, y = position
    if x + image_width > video_width or y + image_height > video_height:
        fail("watermark image does not fit inside the video canvas")
    image = reduce_pgs_palette(image)
    palette, indices = palette_and_indices(list(image.getdata()))
    rle = encode_rle(indices, image_width, image_height)
    start_pts = start_ms * 90
    end_pts = end_ms * 90
    output = bytearray()
    output.extend(
        segment(
            start_pts,
            0x16,
            presentation_segment(
                video_width,
                video_height,
                1,
                0x80,
                0,
                1,
                x,
                y,
            ),
        )
    )
    output.extend(segment(start_pts, 0x17, window_segment(x, y, image_width, image_height)))
    output.extend(segment(start_pts, 0x14, palette_segment(palette)))
    output.extend(segment(start_pts, 0x15, object_segment(1, image_width, image_height, rle)))
    output.extend(segment(start_pts, 0x80, b""))
    output.extend(
        segment(
            end_pts,
            0x16,
            presentation_segment(video_width, video_height, 2, 0x80, 0, 0),
        )
    )
    output.extend(segment(end_pts, 0x80, b""))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return {
        "output": str(output_path),
        "image": f"{image_width}x{image_height}",
        "video": f"{video_width}x{video_height}",
        "position": f"{x}:{y}",
        "text": text,
        "logo_height": rendered_logo_height,
        "palette": len(palette),
        "start": start_ms,
        "end": end_ms,
        "bytes": len(output),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="RGBA PNG watermark")
    parser.add_argument("--output", required=True, type=Path, help="raw SUP/PGS output")
    parser.add_argument("--video-size", default="1920x1080", help="PGS canvas WIDTHxHEIGHT")
    parser.add_argument("--position", required=True, help="top-left position X:Y")
    parser.add_argument("--start", default="00:00:00.000", help="show time")
    parser.add_argument("--end", required=True, help="hide time")
    parser.add_argument(
        "--text",
        help="optional brand text rendered immediately beside the original Logo",
    )
    parser.add_argument("--font", help="font file for --text; defaults to a system serif font")
    parser.add_argument("--font-size", type=int, default=24, help="font size for --text; default 24")
    parser.add_argument(
        "--text-color",
        default="#E4C58F",
        help="RGBA text color for --text; default #E4C58F",
    )
    parser.add_argument("--logo-gap", type=int, default=8, help="gap in pixels between Logo and text; default 8")
    parser.add_argument(
        "--logo-height",
        type=int,
        default=24,
        help="rendered Logo height in pixels; default 24; source aspect ratio is preserved",
    )
    parser.add_argument(
        "--text-alpha-levels",
        type=int,
        default=32,
        help="anti-alias alpha levels for --text; default 32",
    )
    parser.add_argument("--force", action="store_true", help="replace existing output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    image_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not image_path.is_file():
        fail(f"input image does not exist: {image_path}")
    if output_path.exists() and not args.force:
        fail(f"output exists; pass --force: {output_path}")
    summary = build_sup(
        image_path,
        output_path,
        parse_size(args.video_size),
        parse_position(args.position),
        parse_time(args.start),
        parse_time(args.end),
        text=args.text,
        font_path=args.font,
        font_size=args.font_size,
        text_color=parse_color(args.text_color),
        logo_gap=args.logo_gap,
        logo_height=args.logo_height,
        text_alpha_levels=args.text_alpha_levels,
    )
    import json

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
