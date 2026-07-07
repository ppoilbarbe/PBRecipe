"""Sphinx configuration for PBRecipe."""

import re
import shutil
import sys
from pathlib import Path

# Make the src layout importable by autodoc without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pbrecipe import __version__

project = "PBRecipe"
author = "Philippe Poilbarbe"
copyright = "2026, Philippe Poilbarbe"
release = __version__
version = ".".join(__version__.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinxcontrib.mermaid",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
}

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css", "mermaid_zoom.css"]
html_js_files = ["mermaid_zoom.js"]
html_logo = "_static/pbrecipe.png"
html_favicon = "_static/pbrecipe.png"
html_theme_options = {
    "navigation_depth": 4,
    "titles_only": False,
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"

# Mock heavy or optional imports that are not available in the doc build
# environment or that cause autodoc to fail (PySide6 C extensions, optional
# spell-check backends).
autodoc_mock_imports = [
    "PySide6",
    "language_tool_python",
    "pygrammalecte",
]

napoleon_google_docstring = False
napoleon_numpy_docstring = False

autosummary_generate = True


# ---------------------------------------------------------------------------
# Shared Markdown → RST helpers
# ---------------------------------------------------------------------------

_UNDERLINES = {1: "=", 2: "-", 3: "^"}
_LINK = re.compile(r"^\[[^\]]+\]:\s*https?://")


def _heading(out: list[str], title: str, level: int) -> None:
    char = _UNDERLINES[level]
    while out and out[-1] == "":
        out.pop()
    out.append("")
    out.append(title)
    out.append(char * len(title))


def _md_inline(text: str) -> str:
    """Convert inline Markdown to RST (inline code, bold)."""
    text = re.sub(r"`([^`]+)`", r"``\1``", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", text)
    return text


# ---------------------------------------------------------------------------
# Changelog — generated from CHANGELOG.md at build time
# ---------------------------------------------------------------------------

# Match versioned headings: ## [YYYY.x] — YYYY-MM-DD  (em dash or plain hyphen)
_H2_CHANGELOG = re.compile(r"^## \[([^\]]+)\]\s+[—–-]\s+(\d{4}-\d{2}-\d{2})\s*$")
_H2_UNRELEASED = re.compile(r"^## \[Unreleased\]\s*$")
_H3_CHANGELOG = re.compile(r"^### (.+)$")
_NESTED_BULLET = re.compile(r"^ {2,}- ")


def _convert_section(title: str, body_lines: list[str]) -> list[str] | None:
    """Render one ``## [...]`` section (h3 subsections + content) to RST lines.

    Returns ``None`` if the section has no actual content under any of its
    subsections (e.g. an "Unreleased" section with only empty Added/Changed
    headings), so callers can drop it instead of emitting orphan titles.
    """
    out: list[str] = []
    has_content = False

    for line in body_lines:
        m3 = _H3_CHANGELOG.match(line)
        if m3:
            _heading(out, m3.group(1), 3)
            continue

        converted = _md_inline(line)

        # RST nested bullet lists require a blank line before the first nested
        # item; insert one automatically when transitioning into a nested list.
        if _NESTED_BULLET.match(line) and out and out[-1] != "":
            out.append("")

        if converted == "" and out and out[-1] == "":
            continue
        if converted.strip():
            has_content = True
        out.append(converted)

    if not has_content:
        return None

    heading: list[str] = []
    _heading(heading, title, 2)
    return heading + out


def _convert_changelog(md_path: Path) -> str:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        if _LINK.match(line):
            continue

        m2 = _H2_CHANGELOG.match(line)
        m2_unreleased = _H2_UNRELEASED.match(line)
        if m2 or m2_unreleased:
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = f"{m2.group(1)} ({m2.group(2)})" if m2 else "Unreleased"
            current_body = []
            continue

        if current_title is not None:
            current_body.append(line)

    if current_title is not None:
        sections.append((current_title, current_body))

    out: list[str] = []
    for title, body in sections:
        rendered = _convert_section(title, body)
        if rendered is not None:
            out.extend(rendered)

    header = ["Changelog", "=" * len("Changelog")]
    preamble = [
        "",
        "All notable changes to this project are documented here.",
        "The format is based on `Keep a Changelog"
        " <https://keepachangelog.com/en/1.1.0/>`_.",
    ]
    return "\n".join(header + preamble + out).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Generate derived RST files
# ---------------------------------------------------------------------------

_DOCS_DIR = Path(__file__).parent
_ROOT = _DOCS_DIR.parent

_CHANGELOG_RST = _DOCS_DIR / "changelog.rst"
_CHANGELOG_RST.write_text(_convert_changelog(_ROOT / "CHANGELOG.md"), encoding="utf-8")


# ---------------------------------------------------------------------------
# Logo / favicon — copied from the app's own icon at build time, so the
# artwork has a single source of truth
# (src/pbrecipe/resources/icons/pbrecipe-512x512.png).
# ---------------------------------------------------------------------------

_APP_ICON = _ROOT / "src" / "pbrecipe" / "resources" / "icons" / "pbrecipe-512x512.png"
_STATIC_ICON = _DOCS_DIR / "_static" / "pbrecipe.png"

shutil.copyfile(_APP_ICON, _STATIC_ICON)
