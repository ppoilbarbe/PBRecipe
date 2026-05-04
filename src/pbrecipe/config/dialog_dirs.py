"""Persist the last directory used for each named file dialog."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from ruamel.yaml import YAML

_log = logging.getLogger(__name__)


def _dialog_dirs_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "pbrecipe" / "dialog_dirs.yaml"


class DialogDirs:
    """Maps dialog keys to their last-used directory.

    Saved to ``~/.config/pbrecipe/dialog_dirs.yaml``.
    """

    def __init__(self, dirs: dict[str, str] | None = None) -> None:
        self._dirs: dict[str, str] = dirs or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, fallback: str = "") -> str:
        """Return the last directory for *key*, or *fallback* if not set."""
        return self._dirs.get(key, fallback)

    def record(self, key: str, chosen: str, *, is_dir: bool = False) -> None:
        """Update *key* from a dialog result and persist immediately.

        *chosen* is the path returned by the dialog (empty = cancelled).
        If *is_dir* is True the path itself is the directory; otherwise the
        parent directory is extracted from a file path.
        """
        if not chosen:
            return
        directory = str(Path(chosen) if is_dir else Path(chosen).parent)
        if self._dirs.get(key) == directory:
            return
        self._dirs[key] = directory
        self.save()
        _log.debug("Répertoire mémorisé (%s) : %s", key, directory)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> DialogDirs:
        path = _dialog_dirs_path()
        if not path.exists():
            _log.debug("Répertoires de dialogues absents, valeurs par défaut utilisées")
            return cls()
        yaml = YAML()
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.load(fh) or {}
        except Exception as exc:  # noqa: BLE001
            _log.warning("Lecture dialog_dirs impossible (%s), ignoré", exc)
            return cls()
        dirs = {str(k): str(v) for k, v in data.items() if v}
        _log.debug("Répertoires de dialogues chargés : %d entrées", len(dirs))
        return cls(dirs)

    def save(self) -> None:
        path = _dialog_dirs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        yaml = YAML()
        yaml.default_flow_style = False
        with open(path, "w", encoding="utf-8") as fh:
            yaml.dump(dict(self._dirs), fh)
        _log.debug("Répertoires de dialogues sauvegardés")
