from __future__ import annotations

import logging
import shutil
from pathlib import Path
from string import Template

from pbrecipe.config import RecipeConfig
from pbrecipe.database import Database

_log = logging.getLogger(__name__)


class PhpExport:
    """Export the PHP site files to a target directory.

    Layout of the target directory after export:
      target/
        index.php
        lib/
          .htaccess     ← deny directory browsing
          config.php    ← generated from config.php.tpl
          db.php
          media.php     ← serves images from DB (with disk cache in media/)
          recipe.php
          display.php
          technique.php
          search.php
        css/
          base.css
          recipes.css
        js/
          recipe.js
        media/          ← cache disque pour lib/media.php (créé vide à l'export)
    """

    def __init__(self, config: RecipeConfig, db: Database, target: Path) -> None:
        self._config = config
        self._db = db
        self._target = target

    def run(self) -> None:
        _log.info("Début de l'export PHP → %s", self._target)
        self._target.mkdir(parents=True, exist_ok=True)
        # Cache images : vidé à l'export pour forcer le rechargement depuis la DB
        media_dir = self._target / "media"
        if media_dir.is_dir():
            for _f in media_dir.iterdir():
                if _f.is_file():
                    _f.unlink()
            _log.debug("Cache media/ vidé")
        else:
            media_dir.mkdir(exist_ok=True)

        resources_root = Path(__file__).parent.parent / "resources" / "php"

        static_files = [
            "index.php",
            "lib/.htaccess",
            "lib/db.php",
            "lib/media.php",
            "lib/recipe.php",
            "lib/display.php",
            "lib/technique.php",
            "lib/search.php",
            "css/base.css",
            "css/recipes.css",
            "js/recipe.js",
        ]
        for rel in static_files:
            src = resources_root / rel
            dst = self._target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            _log.debug("Copié : %s", rel)
        _log.debug("%d fichiers statiques copiés", len(static_files))

        tpl_path = resources_root / "lib" / "config.php.tpl"
        self._write_config(tpl_path)
        _log.info("Export PHP terminé → %s", self._target)

    def _write_config(self, tpl_path: Path) -> None:
        _log.debug("Génération de lib/config.php depuis %s", tpl_path.name)
        db = self._config.db
        php_db_type = {
            "sqlite": "sqlite",
            "mariadb": "mysql",
            "postgresql": "pgsql",
        }.get(db.type, "mysql")
        mapping = {
            "DB_TYPE": php_db_type,
            "DB_HOST": db.host,
            "DB_PORT": str(db.port),
            "DB_NAME": db.database,
            "DB_USER": db.user,
            "DB_PASS": db.password,
            "DB_PATH": str(Path(db.path).expanduser()) if db.path else db.path,
            "STRINGS_PHP": self._strings_to_php(self._config.strings),
            "SITE_TITLE": self._config.string("site_title"),
            "SITE_TYPE": self._config.site_type,
        }
        tpl = Template(tpl_path.read_text(encoding="utf-8"))
        (self._target / "lib" / "config.php").write_text(
            tpl.safe_substitute(mapping), encoding="utf-8"
        )

    @staticmethod
    def _strings_to_php(strings: dict[str, str]) -> str:
        lines = []
        for key, value in strings.items():
            escaped = value.replace("'", "\\'")
            lines.append(f"    '{key}' => '{escaped}',")
        return "\n".join(lines)
