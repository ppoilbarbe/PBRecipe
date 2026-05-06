# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PBRecipe — exécutable monofichier, Linux / Windows / macOS."""

import sys
from pathlib import Path

SRC = Path("src/pbrecipe")
RESOURCES = SRC / "resources"

_icons = {
    "win32":  RESOURCES / "icons" / "pbrecipe.ico",
    "darwin": RESOURCES / "icons" / "pbrecipe.icns",
}
icon = str(_icons.get(sys.platform, RESOURCES / "icons" / "pbrecipe-512x512.png"))

datas = [
    (str(RESOURCES / "icons"), "pbrecipe/resources/icons"),
    (str(RESOURCES / "php"),   "pbrecipe/resources/php"),
]

hiddenimports = [
    "ruamel.yaml",
    "ruamel.yaml.clib",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.postgresql",
    "pymysql",
    "psycopg2",
]

a = Analysis(
    ["src/pbrecipe/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "pre_commit"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,   # tout embarqué dans l'exécutable
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

# macOS : bundle .app autour du binaire monofichier
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="PBRecipe.app",
        icon=icon,
        bundle_identifier="net.cardolan.pbrecipe",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "0.1.0",
        },
    )
