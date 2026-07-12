#!/usr/bin/env python3
"""Append the exact stock Samsung recovery trailer and enforce the PIT limit."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

LIMIT = 39_845_888
MARKER = b"SEANDROIDENFORCE"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--trailer",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "prebuilt" / "samsung-recovery-trailer.bin",
    )
    args = parser.parse_args()

    image = args.image.read_bytes()
    trailer = args.trailer.read_bytes()
    if not trailer.startswith(MARKER):
        raise SystemExit("refusing trailer without SEANDROIDENFORCE marker")

    if image.endswith(trailer):
        print("Samsung trailer already present; leaving image unchanged")
    else:
        # A source build should not already contain a different Samsung trailer.
        tail_marker = image.rfind(MARKER, max(0, len(image) - 4096))
        if tail_marker != -1:
            raise SystemExit("image already has a different Samsung trailer near EOF")
        image += trailer
        args.image.write_bytes(image)
        print(f"appended {len(trailer)}-byte stock Samsung trailer")

    size = len(image)
    if size > LIMIT:
        raise SystemExit(f"recovery image is {size} bytes; PIT limit is {LIMIT}")

    print(f"image={args.image}")
    print(f"size={size}")
    print(f"headroom={LIMIT - size}")
    print(f"sha256={sha256(image)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
