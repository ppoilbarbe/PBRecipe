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

import site

# Dictionnaires grammalecte (données de graphspell pour la correction orthographique)
_grammalecte_dicts = []
for _sp in site.getsitepackages():
    _d = Path(_sp) / "grammalecte" / "graphspell" / "_dictionaries"
    if _d.is_dir():
        _grammalecte_dicts = [(str(_d), "grammalecte/graphspell/_dictionaries")]
        break

datas += _grammalecte_dicts

# Polices conda : bundlées pour garantir un rendu identique sur toutes les machines.
# Sur Linux, fontconfig cherche les polices via des chemins absolus inscrits dans
# fonts.conf au moment du build ; ces chemins n'existent pas sur la machine cible.
# Le runtime hook hooks/pyi_rth_fonts.py génère un fonts.conf portable au démarrage.
_conda_fonts = Path(sys.prefix) / "fonts"
if _conda_fonts.is_dir():
    datas += [(str(_conda_fonts), "fonts")]

hiddenimports = [
    "ruamel.yaml",
    "ruamel.yaml.clib",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.postgresql",
    "pymysql",
    "psycopg2",
    # Correcteur grammatical (optionnel — absent = vérification désactivée)
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
    binaries=[],
    datas=datas,
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
