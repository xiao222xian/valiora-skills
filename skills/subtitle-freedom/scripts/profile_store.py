#!/usr/bin/env python3
"""Read and persist this Skill's shared user Profile context."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "user-profile/v1"
SKILL_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SAFE_ROOTS = {"user", "brand", "workspace", "preferences"}
SENSITIVE_PARTS = {
    "token",
    "secret",
    "password",
    "credential",
    "cookie",
    "api_key",
    "apikey",
}


def profile_path(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser()
    configured = (
        os.environ.get("SKILL_PROFILE_PATH")
        or os.environ.get("SKILLS_PROFILE_PATH")
        or os.environ.get("LOVSTUDIO_SKILLS_PROFILE")
    )
    if configured:
        return Path(os.path.expandvars(configured)).expanduser()
    candidates = (
        Path.home() / ".lovstudio" / "skills" / "profile.json",
        Path.home() / ".skill-publisher" / "skills" / "profile.json",
        Path.home() / ".config" / "agent-skills" / "profile.json",
    )
    return next((candidate for candidate in candidates if candidate.exists()), candidates[-1])


def read_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"profile cannot be read: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("profile root must be an object")
    return value


def profile_skeleton(skill_id: str) -> dict[str, Any]:
    return {
        "schema": "skill-profile/v1",
        "profile_id": f"profile-{skill_id}",
        "revision": 1,
        "status": "draft",
        "identity": {},
        "purpose": {},
        "brand": {},
        "user": {},
        "workspace": {},
        "skills": {},
        "extensions": {},
    }


def set_path(root: dict[str, Any], parts: list[str], value: Any) -> None:
    current = root
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def target_parts(skill_id: str, requested_path: str) -> tuple[list[str], str]:
    if not SKILL_ID_RE.fullmatch(skill_id):
        raise ValueError("skill_id must be kebab-case")
    parts = [part for part in requested_path.strip().strip(".").split(".") if part]
    if not parts or any(not re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in parts):
        raise ValueError("path must contain valid segments")
    if any(part.casefold() in SENSITIVE_PARTS for part in parts):
        raise ValueError("profile records do not accept secret-like fields")
    if parts[0] == "records":
        target = ["skills", skill_id, "records", *parts[1:]]
        return target, ".".join(target)
    if parts[0] == "profile":
        target = ["skills", skill_id, "profile", *parts[1:]]
        return target, ".".join(target)
    if parts[:3] in (["skills", skill_id, "records"], ["skills", skill_id, "profile"]):
        return parts, ".".join(parts)
    if parts[0] in SAFE_ROOTS:
        return parts, ".".join(parts)
    raise ValueError("path must use records.<field> or a shared Profile scope")


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary_name = handle.name
            handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()


def read_command(args: argparse.Namespace) -> dict[str, Any]:
    path = profile_path(args.profile)
    profile = read_profile(path)
    skills = profile.get("skills", {})
    skill = skills.get(args.skill_id, {}) if isinstance(skills, dict) else {}
    if not isinstance(skill, dict):
        skill = {}
    user = profile.get("user", profile.get("identity", {}))
    brand = profile.get("brand", {})
    workspace = profile.get("workspace", {})
    preferences = profile.get("preferences", {})
    records = skill.get("records", {})
    return {
        "status": "ready",
        "schema": SCHEMA,
        "skill_id": args.skill_id,
        "profile_path": str(path),
        "user": user if isinstance(user, dict) else {},
        "brand": brand if isinstance(brand, dict) else {},
        "workspace": workspace if isinstance(workspace, dict) else {},
        "preferences": preferences if isinstance(preferences, dict) else {},
        "skill": skill,
        "records": records if isinstance(records, dict) else {},
    }


def record_command(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm:
        raise PermissionError("record requires --confirm after a direct user statement")
    parts, canonical_path = target_parts(args.skill_id, args.path)
    path = profile_path(args.profile)
    profile = read_profile(path) or profile_skeleton(args.skill_id)
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    set_path(profile, parts, value)
    revision = profile.get("revision")
    if isinstance(revision, int) and not isinstance(revision, bool):
        profile["revision"] = revision + 1
    atomic_write(path, profile)
    return {"status": "saved", "schema": SCHEMA, "skill_id": args.skill_id, "profile_path": str(path), "path": canonical_path}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    read_parser = subparsers.add_parser("read")
    read_parser.add_argument("--skill-id", required=True)
    read_parser.add_argument("--pretty", action="store_true")
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("--skill-id", required=True)
    record_parser.add_argument("--path", required=True)
    record_parser.add_argument("--value", required=True)
    record_parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    try:
        result = read_command(args) if args.command == "read" else record_command(args)
    except (OSError, PermissionError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if getattr(args, "pretty", False) else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
