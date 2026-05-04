from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_log = logging.getLogger(__name__)


@dataclass
class DbConfig:
    type: str = "sqlite"
    # SQLite
    path: str = "~/recipes.db"
    # MariaDB / PostgreSQL
    host: str = "localhost"
    port: int = 3306
    database: str = "recipes"
    user: str = ""
    password: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DbConfig:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "path": self.path,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }


_DEFAULT_STRINGS: dict[str, str] = {
    # Application
    "window_title": "Mes Recettes",
    "recipe_singular": "Recette",
    "recipe_plural": "Recettes",
    # Recipe fields
    "serving_label": "Quantité",
    "category_label": "Catégorie",
    "categories_label": "Catégories",
    "difficulty_label": "Difficulté",
    "duration_label": "Durée",
    "prep_label": "Préparation",
    "wait_label": "Attente",
    "cook_label": "Cuisson",
    "ingredients_label": "Ingrédients",
    "description_label": "Réalisation",
    "comments_label": "Commentaires",
    "source_label": "Source",
    "techniques_label": "Techniques",
    # Web site
    "site_title": "Mes Recettes",
    "site_description": "Ma collection de recettes",
    "search_placeholder": "Rechercher une recette...",
    "all_categories": "Toutes catégories",
    "all_difficulties": "Toutes difficultés",
    "search_by_ingredient": "Par ingrédient",
    "show_techniques": "Afficher une technique",
    "no_results": "Aucune recette trouvée.",
}


@dataclass
class RecipeConfig:
    name: str = "Mes Recettes"
    db: DbConfig = field(default_factory=DbConfig)
    strings: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_STRINGS))
    php_export_dir: str = ""
    yaml_export_file: str = ""
    site_type: str = "recettes"

    _path: Path | None = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path) -> RecipeConfig:
        yaml = YAML()
        yaml.version = (1, 2)
        with open(path, encoding="utf-8") as fh:
            data = yaml.load(fh) or {}
        cfg = cls(
            name=data.get("name", "Mes Recettes"),
            db=DbConfig.from_dict(data.get("db", {})),
            strings={**_DEFAULT_STRINGS, **data.get("strings", {})},
            php_export_dir=data.get("php_export_dir", ""),
            yaml_export_file=data.get("yaml_export_file", ""),
            site_type=data.get("site_type", "recettes"),
        )
        cfg._path = Path(path)
        _log.info("Configuration recettes chargée : %s («%s»)", cfg._path, cfg.name)
        return cfg

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path else self._path
        if target is None:
            raise ValueError("No file path specified for save().")
        if target.suffix not in {".yaml", ".yml"}:
            target = target.with_suffix(".yaml")
        yaml = YAML()
        yaml.version = (1, 2)
        yaml.default_flow_style = False
        with open(target, "w", encoding="utf-8") as fh:
            yaml.dump(self.to_dict(), fh)
        self._path = target
        _log.info("Configuration recettes sauvegardée : %s", target)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "db": self.db.to_dict(),
            "strings": self.strings,
        }
        if self.php_export_dir:
            d["php_export_dir"] = self.php_export_dir
        if self.yaml_export_file:
            d["yaml_export_file"] = self.yaml_export_file
        if self.site_type:
            d["site_type"] = self.site_type
        return d

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def string(self, key: str) -> str:
        return self.strings.get(key, _DEFAULT_STRINGS.get(key, key))

    @property
    def path(self) -> Path | None:
        return self._path
