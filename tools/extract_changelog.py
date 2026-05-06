#!/usr/bin/env python3
"""Extrait le corps d'une entrée CHANGELOG.md pour une version donnée.

Format attendu (Keep a Changelog — https://keepachangelog.com/) :

    ## [2026.1] — 2026-05-04
    ### Added
    - …

En CI (variable GITHUB_OUTPUT présente) le corps est écrit dans GITHUB_OUTPUT
pour être consommé par une étape ``softprops/action-gh-release``.
En local, il est imprimé sur stdout.

Usage :
    python3 tools/extract_changelog.py 2026.1   # version explicite
    python3 tools/extract_changelog.py           # lit GITHUB_REF_NAME
"""

import os
import re
import sys
from pathlib import Path


def extract(content: str, version: str) -> str:
    """Retourne le corps de la section *version* dans le changelog, ou ''."""
    pattern = rf"(?m)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(1).strip() if m else ""


def main() -> None:
    tag = os.environ.get("GITHUB_REF_NAME") or (
        sys.argv[1] if len(sys.argv) > 1 else ""
    )
    if not tag:
        print(
            "erreur : fournir une version via GITHUB_REF_NAME ou en argument",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        content = Path("CHANGELOG.md").read_text(encoding="utf-8")
        body = extract(content, tag)
    except FileNotFoundError:
        body = ""

    if not body:
        print(
            f"avertissement : aucune entrée CHANGELOG.md trouvée pour [{tag}]",
            file=sys.stderr,
        )
        body = f"Release {tag}."

    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write("body<<CHANGELOG_EOF\n")
            f.write(body)
            f.write("\nCHANGELOG_EOF\n")
    else:
        print(body)


if __name__ == "__main__":
    main()
