#!/usr/bin/env python3
"""Génère pbrecipe.ico (Windows) et pbrecipe.icns (macOS) depuis un PNG source.

Usage :
    python tools/make_icons.py <src.png> <dst.ico> <dst.icns>

Dépendances : Pillow
"""

from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image

# Tailles embarquées dans le .ico
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Entrées ICNS avec données PNG compressées (macOS 10.7+)
# format : (OSType 4 octets, largeur)
ICNS_ENTRIES: list[tuple[bytes, int]] = [
    (b"icp4", 16),
    (b"icp5", 32),
    (b"icp6", 64),
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
]


def _png_bytes(img: Image.Image, size: int) -> bytes:
    resized = img.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    return buf.getvalue()


def make_ico(src: Image.Image, dst: Path) -> None:
    src.save(dst, format="ICO", sizes=ICO_SIZES)
    print(f"  {dst}")


def make_icns(src: Image.Image, dst: Path) -> None:
    chunks: list[bytes] = []
    for ostype, size in ICNS_ENTRIES:
        data = _png_bytes(src, size)
        chunk_size = 8 + len(data)  # header (8 octets) + données PNG
        chunks.append(ostype + struct.pack(">I", chunk_size) + data)

    body = b"".join(chunks)
    total_size = 8 + len(body)
    dst.write_bytes(b"icns" + struct.pack(">I", total_size) + body)
    print(f"  {dst}")


def main() -> None:
    if len(sys.argv) != 4:
        print(
            "usage: make_icons.py <src.png> <dst.ico> <dst.icns>",
            file=sys.stderr,
        )
        sys.exit(1)

    src_path = Path(sys.argv[1])
    ico_path = Path(sys.argv[2])
    icns_path = Path(sys.argv[3])

    img = Image.open(src_path).convert("RGBA")
    print(f"Source : {src_path} ({img.width}×{img.height})")
    make_ico(img, ico_path)
    make_icns(img, icns_path)
    print("Icônes générées.")


if __name__ == "__main__":
    main()
