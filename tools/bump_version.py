#!/usr/bin/env python3
"""Increment or force-set the project version.

Updates src/pbrecipe/__init__.py and pyproject.toml in one pass.
Usage:
  python tools/bump_version.py release       # 2026.5 → 2026.6
  python tools/bump_version.py year          # 2026.5 → 2027.1
  python tools/bump_version.py set <AAAA.x>  # must be > current version
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
INIT_PY = ROOT / "src" / "pbrecipe" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"

VERSION_RE = re.compile(r"^(\d{4})\.(\d+)$")


def parse_version(ver: str) -> tuple[int, int]:
    m = VERSION_RE.match(ver)
    if not m:
        raise ValueError(f"Format de version invalide : {ver!r} (attendu AAAA.x)")
    return int(m.group(1)), int(m.group(2))


def replace_version(text: str, pattern: str, new_ver: str) -> tuple[str, str]:
    """Return (new_text, old_ver)."""
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Version introuvable avec le motif : {pattern!r}")
    old_ver = m.group(1)
    return text[: m.start(1)] + new_ver + text[m.end(1) :], old_ver


def compute_new_version(old_ver: str, component: str) -> str:
    year, release = parse_version(old_ver)
    if component == "year":
        return f"{year + 1}.1"
    return f"{year}.{release + 1}"


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("release", "year", "set"):
        print(
            "Usage: bump_version.py release|year\n       bump_version.py set <AAAA.x>",
            file=sys.stderr,
        )
        sys.exit(1)

    init_src = INIT_PY.read_text(encoding="utf-8")
    pyproject_src = PYPROJECT.read_text(encoding="utf-8")

    _, old_ver = replace_version(init_src, r'__version__\s*=\s*"([^"]+)"', "")

    if argv[0] == "set":
        if len(argv) != 2:
            print("Usage: bump_version.py set <AAAA.x>", file=sys.stderr)
            sys.exit(1)
        new_ver = argv[1]
        try:
            parse_version(new_ver)
        except ValueError as e:
            print(f"erreur : {e}", file=sys.stderr)
            sys.exit(1)
        if parse_version(new_ver) <= parse_version(old_ver):
            print(
                f"erreur : {new_ver} n'est pas supérieur"
                f" à la version actuelle {old_ver}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        new_ver = compute_new_version(old_ver, argv[0])

    init_new, _ = replace_version(init_src, r'__version__\s*=\s*"([^"]+)"', new_ver)
    pyproject_new, _ = replace_version(
        pyproject_src, r'(?m)^version\s*=\s*"([^"]+)"', new_ver
    )

    INIT_PY.write_text(init_new, encoding="utf-8")
    PYPROJECT.write_text(pyproject_new, encoding="utf-8")

    print(f"{old_ver} → {new_ver}")


if __name__ == "__main__":
    main()
