"""Export and import the full database content as YAML."""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Any

from ruamel.yaml import YAML

from pbrecipe.database import Database
from pbrecipe.models import (
    Category,
    DifficultyLevel,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeMedia,
    Source,
    Technique,
    Unit,
)

_log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────


class YamlExport:
    """Serialize the full database to a YAML file."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def run(self, path) -> None:
        _log.info("Export YAML → %s", path)
        doc = self._build_document()
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.width = 120
        with open(path, "w", encoding="utf-8") as fh:
            yaml.dump(doc, fh)
        recipes = len(doc.get("recipes", []))
        _log.info(
            "Export YAML terminé : %d recettes, %d catégories, %d ingrédients, "
            "%d unités, %d sources, %d techniques, %d niveaux de difficulté",
            recipes,
            len(doc.get("categories", [])),
            len(doc.get("ingredients", [])),
            len(doc.get("units", [])),
            len(doc.get("sources", [])),
            len(doc.get("techniques", [])),
            len(doc.get("difficulty_levels", [])),
        )

    # ------------------------------------------------------------------

    def _build_document(self) -> dict[str, Any]:
        categories = self._db.list_categories()
        units = self._db.list_units()
        ingredients = self._db.list_ingredients()
        sources = self._db.list_sources()
        techniques = self._db.list_techniques()
        difficulty_levels = self._db.list_difficulty_levels()
        recipe_stubs = self._db.list_recipes()

        cat_by_id = {c.id: c.name for c in categories}
        unit_by_id = {u.id: u.name for u in units}
        ing_by_id = {i.id: i.name for i in ingredients}
        src_by_id = {s.id: s.name for s in sources}

        return {
            "categories": [c.name for c in sorted(categories, key=lambda x: x.name)],
            "units": [u.name for u in sorted(units, key=lambda x: x.name)],
            "ingredients": [i.name for i in sorted(ingredients, key=lambda x: x.name)],
            "sources": [s.name for s in sorted(sources, key=lambda x: x.name)],
            "techniques": [
                {
                    "code": t.code,
                    "title": t.title,
                    "description": t.description or "",
                }
                for t in sorted(techniques, key=lambda x: x.code)
            ],
            "difficulty_levels": [
                {
                    "level": dl.level,
                    "label": dl.label,
                    "mime_type": dl.mime_type,
                    "data": base64.b64encode(dl.data).decode("ascii")
                    if dl.data
                    else "",
                }
                for dl in difficulty_levels
            ],
            "recipes": [
                self._serialize_recipe(
                    self._db.get_recipe(stub.code),
                    cat_by_id,
                    unit_by_id,
                    ing_by_id,
                    src_by_id,
                )
                for stub in recipe_stubs
                if self._db.get_recipe(stub.code) is not None
            ],
        }

    def _serialize_recipe(
        self,
        recipe: Recipe,
        cat_by_id: dict,
        unit_by_id: dict,
        ing_by_id: dict,
        src_by_id: dict,
    ) -> dict[str, Any]:
        ingredients = [
            {
                "position": ri.position,
                "prefix": ri.prefix,
                "quantity": ri.quantity,
                "unit": unit_by_id.get(ri.unit_id, "")
                if ri.unit_id is not None
                else "",
                "ingredient": ing_by_id.get(ri.ingredient_id, "")
                if ri.ingredient_id is not None
                else "",
                "separator": ri.separator,
                "suffix": ri.suffix,
            }
            for ri in recipe.ingredients
        ]
        media = [
            {
                "position": m.position,
                "code": m.code,
                "mime_type": m.mime_type,
                "data": base64.b64encode(m.data).decode("ascii") if m.data else "",
            }
            for m in recipe.media
        ]
        return {
            "code": recipe.code,
            "name": recipe.name,
            "difficulty": recipe.difficulty,
            "serving": recipe.serving or "",
            "prep_time": recipe.prep_time,
            "wait_time": recipe.wait_time,
            "cook_time": recipe.cook_time,
            "description": recipe.description or "",
            "comments": recipe.comments or "",
            "source": src_by_id.get(recipe.source_id)
            if recipe.source_id is not None
            else None,
            "categories": [
                cat_by_id[cid] for cid in recipe.categories if cid in cat_by_id
            ],
            "ingredients": ingredients,
            "media": media,
        }


# ──────────────────────────────────────────────────────────────────────────────


class YamlImport:
    """Deserialize a YAML file and merge its content into the database."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def run(self, path, *, replace: bool = False) -> dict[str, int]:
        """Import the file at *path*.

        If *replace* is True, all existing data is deleted before import.
        Returns a summary dict with counts of created/updated items.
        """
        _log.info("Import YAML ← %s (replace=%s)", path, replace)
        if replace:
            self._db.clear_all_data()
        yaml = YAML()
        with open(path, encoding="utf-8") as fh:
            doc = yaml.load(fh)
        if not isinstance(doc, dict):
            raise ValueError(
                "Le fichier YAML ne contient pas un dictionnaire à la racine."
            )

        stats: dict[str, int] = {
            "categories": 0,
            "units": 0,
            "ingredients": 0,
            "sources": 0,
            "techniques": 0,
            "difficulty_levels": 0,
            "recipes_created": 0,
            "recipes_updated": 0,
        }

        self._import_difficulty_levels(doc.get("difficulty_levels", []), stats)

        cat_map = self._import_simple_list(
            doc.get("categories", []),
            self._db.list_categories(),
            self._db.save_category,
            lambda name: Category(name=name),
            stats,
            "categories",
        )
        unit_map = self._import_simple_list(
            doc.get("units", []),
            self._db.list_units(),
            self._db.save_unit,
            lambda name: Unit(name=name),
            stats,
            "units",
        )
        ing_map = self._import_simple_list(
            doc.get("ingredients", []),
            self._db.list_ingredients(),
            self._db.save_ingredient,
            lambda name: Ingredient(name=name),
            stats,
            "ingredients",
        )
        src_map = self._import_simple_list(
            doc.get("sources", []),
            self._db.list_sources(),
            self._db.save_source,
            lambda name: Source(name=name),
            stats,
            "sources",
        )

        self._import_techniques(doc.get("techniques", []), stats)

        for recipe_data in doc.get("recipes", []):
            self._import_recipe(recipe_data, cat_map, unit_map, ing_map, src_map, stats)

        _log.info(
            "Import YAML terminé : +%d cat, +%d unités, +%d ing,"
            " +%d sources, +%d techniques, %d niveaux de difficulté,"
            " %d recettes créées, %d recettes mises à jour",
            stats["categories"],
            stats["units"],
            stats["ingredients"],
            stats["sources"],
            stats["techniques"],
            stats["difficulty_levels"],
            stats["recipes_created"],
            stats["recipes_updated"],
        )
        return stats

    # ------------------------------------------------------------------

    def _import_simple_list(
        self,
        names: list[str],
        existing: list,
        save_fn,
        make_fn,
        stats: dict,
        key: str,
    ) -> dict[str, int]:
        """Ensure every name in *names* exists in DB. Return name→id map."""
        by_name = {item.name: item.id for item in existing}
        for raw in names:
            name = str(raw)
            if name not in by_name:
                item = save_fn(make_fn(name))
                by_name[name] = item.id
                stats[key] += 1
                _log.debug("Créé (%s) : «%s»", key, name)
        # Also refresh from DB to capture any items not in the export list
        # but already in the DB (needed for recipe resolution).
        for item in existing:
            by_name.setdefault(item.name, item.id)
        return by_name

    def _import_difficulty_levels(self, levels: list, stats: dict) -> None:
        for entry in levels:
            if not isinstance(entry, dict):
                _log.warning(
                    "Niveau de difficulté ignoré (format invalide) : %r", entry
                )
                continue
            level = entry.get("level")
            if level is None or not isinstance(level, int) or not (0 <= level <= 3):
                _log.warning("Niveau de difficulté ignoré : valeur invalide %r", level)
                continue
            raw_data = entry.get("data", "")
            try:
                data = base64.b64decode(raw_data) if raw_data else None
            except binascii.Error:
                _log.warning(
                    "Niveau de difficulté %d : données binaires invalides,"
                    " icône ignorée",
                    level,
                )
                data = None
            self._db.save_difficulty_level(
                DifficultyLevel(
                    level=level,
                    label=str(entry.get("label", "")),
                    mime_type=str(entry.get("mime_type", "image/jpeg")),
                    data=data,
                )
            )
            stats["difficulty_levels"] += 1

    def _import_techniques(self, techniques: list, stats: dict) -> None:
        for entry in techniques:
            if not isinstance(entry, dict):
                _log.warning("Technique ignorée (format invalide) : %r", entry)
                continue
            code = str(entry.get("code", "")).strip().upper()
            if not code:
                _log.warning("Technique ignorée : code absent")
                continue
            t = Technique(
                code=code,
                title=str(entry.get("title", "")),
                description=str(entry.get("description", "")),
            )
            self._db.save_technique(t)
            stats["techniques"] += 1

    def _import_recipe(
        self,
        data: dict,
        cat_map: dict[str, int],
        unit_map: dict[str, int],
        ing_map: dict[str, int],
        src_map: dict[str, int],
        stats: dict,
    ) -> None:
        if not isinstance(data, dict):
            _log.warning("Recette ignorée (format invalide) : %r", data)
            return
        code = str(data.get("code", "")).strip()
        if not code:
            _log.warning("Recette ignorée : code absent")
            return

        # Resolve category IDs — create missing ones on the fly
        category_ids: list[int] = []
        for cat_name in data.get("categories", []):
            name = str(cat_name)
            if name not in cat_map:
                created = self._db.save_category(Category(name=name))
                cat_map[name] = created.id
                _log.debug("Catégorie créée à la volée : «%s»", name)
            cid = cat_map[name]
            if cid is not None:
                category_ids.append(cid)

        # Resolve source ID — create if missing
        source_id: int | None = None
        src_name = data.get("source")
        if src_name:
            name = str(src_name)
            if name not in src_map:
                created = self._db.save_source(Source(name=name))
                src_map[name] = created.id
                _log.debug("Source créée à la volée : «%s»", name)
            source_id = src_map.get(name)

        # Build ingredients — resolve unit/ingredient IDs, create if missing
        ingredients: list[RecipeIngredient] = []
        for pos, ri_data in enumerate(data.get("ingredients", [])):
            if not isinstance(ri_data, dict):
                continue
            unit_name = str(ri_data.get("unit", ""))
            unit_id: int | None = None
            if unit_name != "":
                if unit_name not in unit_map:
                    created = self._db.save_unit(Unit(name=unit_name))
                    unit_map[unit_name] = created.id
                    _log.debug("Unité créée à la volée : «%s»", unit_name)
                unit_id = unit_map.get(unit_name)

            ing_name = str(ri_data.get("ingredient", ""))
            ing_id: int | None = None
            if ing_name:
                if ing_name not in ing_map:
                    created = self._db.save_ingredient(Ingredient(name=ing_name))
                    ing_map[ing_name] = created.id
                    _log.debug("Ingrédient créé à la volée : «%s»", ing_name)
                ing_id = ing_map.get(ing_name)

            ingredients.append(
                RecipeIngredient(
                    recipe_code=code,
                    position=int(ri_data.get("position", pos)),
                    prefix=str(ri_data.get("prefix", "")),
                    quantity=str(ri_data.get("quantity", "1")),
                    unit_id=unit_id,
                    separator=str(ri_data.get("separator", "")),
                    ingredient_id=ing_id,
                    suffix=str(ri_data.get("suffix", "")),
                )
            )

        # Build media
        media: list[RecipeMedia] = []
        for pos, m_data in enumerate(data.get("media", [])):
            if not isinstance(m_data, dict):
                continue
            raw_data = m_data.get("data", "")
            try:
                media_bytes = base64.b64decode(raw_data) if raw_data else b""
            except binascii.Error:
                _log.warning(
                    "Média ignoré (base64 invalide) : code=%s", m_data.get("code")
                )
                continue
            media.append(
                RecipeMedia(
                    recipe_code=code,
                    position=int(m_data.get("position", pos)),
                    code=str(m_data.get("code", "")).upper(),
                    mime_type=str(m_data.get("mime_type", "image/jpeg")),
                    data=media_bytes,
                )
            )

        existing = self._db.get_recipe(code)
        recipe = Recipe(
            code=code,
            name=str(data.get("name", "")),
            difficulty=int(data.get("difficulty", 0)),
            serving=str(data.get("serving", "")),
            prep_time=data.get("prep_time") or None,
            wait_time=data.get("wait_time") or None,
            cook_time=data.get("cook_time") or None,
            description=str(data.get("description", "")),
            comments=str(data.get("comments", "")),
            source_id=source_id,
            categories=category_ids,
            ingredients=ingredients,
            media=media,
        )
        self._db.save_recipe(recipe)
        if existing:
            stats["recipes_updated"] += 1
        else:
            stats["recipes_created"] += 1
