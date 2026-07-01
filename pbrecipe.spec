# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PBRecipe — single-file executable, Linux / Windows / macOS."""

import re
import sys
from pathlib import Path

SRC = Path("src/pbrecipe")

_version = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (SRC / "__init__.py").read_text(encoding="utf-8"),
).group(1)
RESOURCES = SRC / "resources"

_icons = {
    "win32":  RESOURCES / "icons" / "pbrecipe.ico",
    "darwin": RESOURCES / "icons" / "pbrecipe.icns",
}
icon = str(_icons.get(sys.platform, RESOURCES / "icons" / "pbrecipe-512x512.png"))

_datas = [
    (str(RESOURCES / "icons"), "pbrecipe/resources/icons"),
    (str(RESOURCES / "php"),   "pbrecipe/resources/php"),
]

import site

from PyInstaller.utils.hooks import collect_data_files

# LanguageTool data files (integrity.toml, logging.toml — read via
# importlib.resources at import time, not picked up by hiddenimports alone)
_datas += collect_data_files("language_tool_python")

# Grammalecte dictionaries (graphspell data for spell checking)
_grammalecte_dicts = []
for _sp in site.getsitepackages():
    _d = Path(_sp) / "grammalecte" / "graphspell" / "_dictionaries"
    if _d.is_dir():
        _grammalecte_dicts = [(str(_d), "grammalecte/graphspell/_dictionaries")]
        break

_datas += _grammalecte_dicts

# On Linux, PySide6's Qt hook bundles the *system* libssl.so.3/libcrypto.so.3
# for QtNetwork's TLS backend. Since both files share their basename with the
# conda-provided OpenSSL that the interpreter's _ssl module is linked against,
# only one copy survives in the frozen bundle — and the system one (typically
# older, e.g. Ubuntu's OpenSSL 3.0.x) wins, missing symbols conda's _ssl needs
# (e.g. OPENSSL_3.3.0), which breaks every HTTPS connection (requests/urllib3)
# with "SSL module is not available". Force the conda copy explicitly so it
# takes precedence; a newer OpenSSL 3.x remains ABI-compatible for QtNetwork.
_binaries = []
if sys.platform == "linux":
    for _lib in ("libssl.so.3", "libcrypto.so.3"):
        _p = Path(sys.prefix) / "lib" / _lib
        if _p.is_file():
            _binaries.append((str(_p), "."))

# Conda fonts: bundled to guarantee identical rendering across machines.
# On Linux, fontconfig resolves fonts via absolute paths written into fonts.conf
# at build time; those paths do not exist on the target machine.
# The runtime hook hooks/pyi_rth_fonts.py generates a portable fonts.conf at startup.
_conda_fonts = Path(sys.prefix) / "fonts"
if _conda_fonts.is_dir():
    _datas += [(str(_conda_fonts), "fonts")]

hiddenimports = [
    "ruamel.yaml",
    "ruamel.yaml.clib",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.postgresql",
    "pymysql",
    "psycopg2",
    # Grammar/spell checkers (optional — if absent, spell checking is disabled)
    "language_tool_python",
    "language_tool_python.utils",
    "pygrammalecte",
    "pygrammalecte.pygrammalecte",
    "grammalecte",
    "grammalecte.fr",
    "grammalecte.graphspell",
    "grammalecte.graphspell.ibdawg",
    "grammalecte.graphspell.spellchecker",
    "grammalecte.graphspell.tokenizer",
    "grammalecte.grammar_checker",
    "grammalecte.grammalecte_cli",
    "grammalecte.text",
]

a = Analysis(
    ["src/pbrecipe/__main__.py"],
    pathex=["src"],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["hooks/pyi_rth_fonts.py"],
    excludes=["pytest", "ruff", "pre_commit"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,   # everything embedded in the executable
    a.datas,
    name="pbrecipe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=icon,
    onefile=True,
)

# macOS: wrap the single-file binary in a .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="PBRecipe.app",
        icon=icon,
        bundle_identifier="net.cardolan.pbrecipe",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": _version,
        },
    )
