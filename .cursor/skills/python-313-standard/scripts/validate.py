#!/usr/bin/env python3
"""Validate Python 3.13 standard compliance for this project."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PYPROJECT = ROOT / "pyproject.toml"
SRC = ROOT / "src" / "medical_chat"


def check_requires_python() -> list[str]:
    errors: list[str] = []
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
    if not match:
        errors.append("pyproject.toml: missing requires-python")
    elif not match.group(1).startswith(">=3.13"):
        errors.append(
            f"pyproject.toml: requires-python must be >=3.13, got {match.group(1)!r}"
        )
    return errors


def check_no_docker() -> list[str]:
    errors: list[str] = []
    for name in ("Dockerfile", "docker-compose.yml", ".dockerignore"):
        if (ROOT / name).exists():
            errors.append(f"{name}: Docker packaging is not used in this project")
    return errors


def check_no_legacy_typing() -> list[str]:
    errors: list[str] = []
    patterns = [
        (r"\bfrom typing import .*\bOptional\b", "use X | None instead of Optional"),
        (r"\bfrom typing import .*\bList\b", "use list[...] instead of List"),
        (r"\bfrom typing import .*\bDict\b", "use dict[...] instead of Dict"),
    ]
    for path in SRC.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern, message in patterns:
            if re.search(pattern, content):
                rel = path.relative_to(ROOT)
                errors.append(f"{rel}: {message}")
    return errors


def main() -> int:
    errors = [
        *check_requires_python(),
        *check_no_docker(),
        *check_no_legacy_typing(),
    ]
    if errors:
        print("Python 3.13 standard validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Python 3.13 standard validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
