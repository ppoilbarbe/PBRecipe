# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Source unique du répertoire de configuration de l'application.

Le répertoire peut être surchargé via ``set_config_dir()`` (option ``--config-dir``
de la ligne de commande) avant le premier accès.

Valeurs par défaut selon la plateforme :
- Linux  : ``$XDG_CONFIG_HOME/pbrecipe``  (défaut : ``~/.config/pbrecipe``)
- macOS  : ``~/Library/Preferences/pbrecipe``
- Windows: ``%APPDATA%/pbrecipe``          (défaut : ``~/AppData/Roaming/pbrecipe``)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_override: Path | None = None


def set_config_dir(path: Path) -> None:
    """Surcharge le répertoire de configuration.

    À appeler avant tout ``AppConfig.load()``.
    """
    global _override
    _override = Path(path)


def _default_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "pbrecipe"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Preferences" / "pbrecipe"
    # Linux / freedesktop XDG — la valeur doit être non vide et absolue
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    xdg_path = Path(xdg) if xdg else None
    base = (
        xdg_path if (xdg_path and xdg_path.is_absolute()) else Path.home() / ".config"
    )
    return base / "pbrecipe"


def get_config_dir() -> Path:
    """Retourne le répertoire de configuration pbrecipe."""
    return _override if _override is not None else _default_config_dir()
