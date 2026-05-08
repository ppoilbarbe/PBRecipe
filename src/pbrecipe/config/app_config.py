from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML

from pbrecipe.config.dialog_dirs import DialogDirs

_log = logging.getLogger(__name__)

_MAX_RECENT = 10


def _config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "pbrecipe" / "app.yaml"


_VALID_LEVELS = {"DEBUG", "INFO", "WARNING"}


@dataclass
class AppConfig:
    recent_files: list[str] = field(default_factory=list)
    log_level: str = "INFO"
    dialog_dirs: DialogDirs = field(default_factory=DialogDirs.load)
    window_geometry: dict = field(default_factory=dict)
    splitter_sizes: list[int] = field(default_factory=list)
    toolbar_state: str = ""

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls) -> AppConfig:
        path = _config_path()
        if not path.exists():
            _log.debug("Configuration programme absente, valeurs par défaut utilisées")
            return cls()
        yaml = YAML()
        yaml.version = (1, 2)
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.load(fh) or {}
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "Lecture configuration programme impossible (%s),"
                " valeurs par défaut utilisées",
                exc,
            )
            return cls()
        raw_level = str(data.get("log_level", "INFO")).upper()
        log_level = raw_level if raw_level in _VALID_LEVELS else "INFO"
        raw_geom = data.get("window_geometry", {})
        window_geometry = raw_geom if isinstance(raw_geom, dict) else {}
        raw_sizes = data.get("splitter_sizes", [])
        splitter_sizes = (
            [int(s) for s in raw_sizes] if isinstance(raw_sizes, list) else []
        )
        toolbar_state = str(data.get("toolbar_state", ""))
        cfg = cls(
            recent_files=list(data.get("recent_files", [])),
            log_level=log_level,
            window_geometry=window_geometry,
            splitter_sizes=splitter_sizes,
            toolbar_state=toolbar_state,
        )
        _log.debug("Configuration programme chargée : %s (log=%s)", path, cfg.log_level)
        return cfg

    def save(self) -> None:
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        yaml = YAML()
        yaml.version = (1, 2)
        yaml.default_flow_style = False
        with open(path, "w", encoding="utf-8") as fh:
            yaml.dump(
                {
                    "recent_files": self.recent_files,
                    "log_level": self.log_level,
                    "window_geometry": self.window_geometry,
                    "splitter_sizes": self.splitter_sizes,
                    "toolbar_state": self.toolbar_state,
                },
                fh,
            )
        _log.debug("Configuration programme sauvegardée : %s", path)

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def clear_recent(self) -> None:
        self.recent_files = []
        _log.debug("Fichiers récents effacés")

    def add_recent(self, file_path: str | Path) -> None:
        p = str(Path(file_path).resolve())
        already = p in self.recent_files
        if already:
            self.recent_files.remove(p)
        self.recent_files.insert(0, p)
        self.recent_files = self.recent_files[:_MAX_RECENT]
        _log.debug(
            "%s fichiers récents : %s",
            "Déplacé en tête des" if already else "Ajouté aux",
            p,
        )

    @property
    def last_file(self) -> str | None:
        return self.recent_files[0] if self.recent_files else None
