# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Database: full access to the SQLite/MySQL recipe store (CRUD, migration, search)."""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, fields

from sqlalchemy import (
    String,
    Table,
    and_,
    create_engine,
    delete,
    event,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Engine

from pbrecipe.constants import MAX_DIFFICULTY, MAX_SOURCE_SHORTCUT, MIN_DIFFICULTY
from pbrecipe.database.schema import (
    metadata,
    t_categories,
    t_difficulty_levels,
    t_equipment,
    t_globals,
    t_ingredients,
    t_recipe_categories,
    t_recipe_equipment,
    t_recipe_ingredients,
    t_recipe_media,
    t_recipes,
    t_sources,
    t_techniques,
    t_units,
)
from pbrecipe.models import (
    Category,
    DifficultyLevel,
    Equipment,
    Ingredient,
    Recipe,
    RecipeEquipment,
    RecipeIngredient,
    RecipeMedia,
    Source,
    Technique,
    Unit,
)

_log = logging.getLogger(__name__)

# Minimal set identifying a PBRecipe schema. Tables added later (e.g. equipment,
# recipe_equipment) are deliberately left out: older databases lacking them
# must still be recognized, create_schema() then adds them.
_EXPECTED_TABLES = frozenset(
    {
        "categories",
        "difficulty_levels",
        "ingredients",
        "recipe_categories",
        "recipe_ingredients",
        "recipe_media",
        "recipes",
        "sources",
        "techniques",
        "units",
    }
)

_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae", "ß": "ss"})


def _sort_key(s: str) -> str:
    """Clé de tri insensible à la casse, aux diacritiques et aux ligatures."""
    s = s.casefold().translate(_LIGATURES)
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()


def _select_recipe_rows(conn: Connection, table: Table, cls: type, code: str) -> list:
    """Load the ordered child rows of a recipe into dataclasses of type *cls*.

    Dataclass field names must match the table column names.
    """
    rows = conn.execute(
        select(table).where(table.c.recipe_code == code).order_by(table.c.position)
    ).fetchall()
    result = []
    for r in rows:
        values = {f.name: getattr(r, f.name) for f in fields(cls)}
        values.update(
            {f.name: bool(values[f.name]) for f in fields(cls) if f.type == "bool"}
        )
        result.append(cls(**values))
    return result


def _replace_recipe_rows(
    conn: Connection, table: Table, code: str, items: list
) -> None:
    """Replace all child rows of a recipe with *items* (dataclasses, id ignored)."""
    conn.execute(delete(table).where(table.c.recipe_code == code))
    if items:
        rows = []
        for item in items:
            values = asdict(item)
            values.pop("id")
            values["recipe_code"] = code
            rows.append(values)
        conn.execute(insert(table), rows)


def _safe_url(url: str) -> str:
    return re.sub(r"(://[^:@/]+:)[^@/]+(@)", r"\1***\2", url)


class SchemaMismatchError(RuntimeError):
    """The database lacks columns of the current schema (incompatible format)."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        lines = "\n".join(f"  – {col}" for col in missing)
        super().__init__(
            "Le schéma de la base est incompatible avec cette version"
            f" du programme.\nColonnes absentes :\n{lines}"
        )


class Database:
    def __init__(self, url: str) -> None:
        self._url = url
        self._engine: Engine | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self._engine = create_engine(self._url)
        if self._engine.dialect.name == "sqlite":
            event.listen(self._engine, "connect", self._enable_sqlite_fk)
        _log.info("Connecté : %s", _safe_url(self._url))

    def disconnect(self) -> None:
        if self._engine:
            self._engine.dispose()
            self._engine = None
            _log.info("Déconnecté : %s", _safe_url(self._url))

    def check_schema(self) -> str:
        """Inspecte l'état des tables.

        Retourne :
          "empty"   – aucune table présente
          "ok"      – toutes les tables attendues sont présentes
          "foreign" – des tables existent mais le schéma est incompatible
        """
        assert self._engine
        existing = set(inspect(self._engine).get_table_names())
        if not existing:
            return "empty"
        if _EXPECTED_TABLES.issubset(existing):
            return "ok"
        return "foreign"

    def create_schema(self) -> None:
        assert self._engine
        metadata.create_all(self._engine)
        with self._engine.begin() as conn:
            self._ensure_bool_columns(
                conn
            )  # doit précéder _migrate (INSERT inclut hide_label)
            self._ensure_text_columns(conn)
            self._migrate(conn)
            self._ensure_all_varchar_sizes(conn)
            self._ensure_mediumblob(conn)
            missing = self._missing_columns(conn)
            if missing:
                _log.error("Schéma incompatible, colonnes absentes : %s", missing)
                raise SchemaMismatchError(missing)
        _log.info("Schéma vérifié/créé")

    def missing_columns(self) -> list[str]:
        """Return the schema columns absent from existing tables ("table.column")."""
        assert self._engine
        with self._engine.connect() as conn:
            return self._missing_columns(conn)

    @staticmethod
    def _missing_columns(conn: Connection) -> list[str]:
        # Tables absentes ignorées : create_schema() les crée.
        insp = inspect(conn)
        existing = set(insp.get_table_names())
        missing = []
        for table in metadata.sorted_tables:
            if table.name not in existing:
                continue
            present = {c["name"] for c in insp.get_columns(table.name)}
            missing += [
                f"{table.name}.{col.name}"
                for col in table.columns
                if col.name not in present
            ]
        return missing

    def clear_all_data(self) -> None:
        """Delete all rows from every table, preserving the schema."""
        assert self._engine
        with self._engine.begin() as conn:
            for tbl in (
                t_recipe_media,
                t_recipe_equipment,
                t_recipe_ingredients,
                t_recipe_categories,
                t_recipes,
                t_techniques,
                t_sources,
                t_equipment,
                t_ingredients,
                t_units,
                t_categories,
                t_difficulty_levels,
                t_globals,
            ):
                conn.execute(delete(tbl))
        _log.debug("Base vidée")

    _DEFAULT_DIFFICULTY_LEVELS = [
        DifficultyLevel(level=0, label=""),
        DifficultyLevel(level=1, label="Facile"),
        DifficultyLevel(level=2, label="Moyen"),
        DifficultyLevel(level=3, label="Difficile"),
    ]

    def _migrate(self, conn: Connection) -> None:
        existing_levels = {
            row.level
            for row in conn.execute(select(t_difficulty_levels.c.level)).fetchall()
        }
        for dl in self._DEFAULT_DIFFICULTY_LEVELS:
            if dl.level not in existing_levels:
                conn.execute(
                    insert(t_difficulty_levels).values(
                        level=dl.level,
                        label=dl.label,
                        mime_type=dl.mime_type,
                        data=dl.data,
                    )
                )
                _log.info("Niveau de difficulté créé : %d — «%s»", dl.level, dl.label)

    def _ensure_all_varchar_sizes(self, conn: Connection) -> None:
        """Ajuste toutes les colonnes String du schéma à leur longueur déclarée."""
        for table in metadata.tables.values():
            for col in table.columns:
                if not isinstance(col.type, String) or col.type.length is None:
                    continue
                default = (
                    str(col.default.arg)
                    if col.default is not None and not callable(col.default.arg)
                    else ""
                )
                self._ensure_varchar_size(
                    conn,
                    table.name,
                    col.name,
                    col.type.length,
                    not_null=not col.nullable,
                    default=default,
                )

    def _ensure_varchar_size(
        self,
        conn: Connection,
        table: str,
        col: str,
        min_size: int,
        *,
        not_null: bool = True,
        default: str = "",
    ) -> None:
        """Élargit une colonne VARCHAR si sa taille déclarée est trop petite."""
        cols = {c["name"]: c for c in inspect(conn).get_columns(table)}
        if col not in cols:
            return
        current_size = getattr(cols[col]["type"], "length", None)
        if current_size is not None and current_size >= min_size:
            return
        dialect = conn.dialect.name
        if dialect == "sqlite":
            return  # SQLite n'applique pas les tailles VARCHAR
        nn = "NOT NULL" if not_null else ""
        df = f"DEFAULT '{default}'"
        if dialect == "mysql":  # MariaDB
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            conn.execute(
                text(
                    f"ALTER TABLE `{table}`"
                    f" MODIFY COLUMN `{col}` VARCHAR({min_size}) {nn} {df}"
                )
            )
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        elif dialect == "postgresql":
            conn.execute(
                text(
                    f'ALTER TABLE "{table}"'
                    f' ALTER COLUMN "{col}" TYPE VARCHAR({min_size})'
                )
            )
        _log.info("Migration : %s.%s étendu à VARCHAR(%d)", table, col, min_size)

    # (table, column, NOT NULL constraint)
    _BLOB_COLUMNS: list[tuple[str, str, str]] = [
        ("recipe_media", "data", "NOT NULL"),
        ("difficulty_levels", "data", "NULL"),
    ]

    def _ensure_mediumblob(self, conn: Connection) -> None:
        """Pour MariaDB, promeut les colonnes BLOB en MEDIUMBLOB si nécessaire.

        PostgreSQL utilise BYTEA (pas de limite pratique) — aucune action requise.
        SQLite ignore les types de colonnes — aucune action requise.
        """
        if conn.dialect.name != "mysql":
            return
        for table, col, null_constraint in self._BLOB_COLUMNS:
            row = conn.execute(
                text(
                    "SELECT DATA_TYPE FROM information_schema.COLUMNS"
                    " WHERE TABLE_SCHEMA = DATABASE()"
                    " AND TABLE_NAME = :tbl AND COLUMN_NAME = :col"
                ),
                {"tbl": table, "col": col},
            ).fetchone()
            if row is None or row[0].lower() != "blob":
                continue  # Absent, déjà MEDIUMBLOB ou LONGBLOB
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            conn.execute(
                text(
                    f"ALTER TABLE `{table}`"
                    f" MODIFY COLUMN `{col}` MEDIUMBLOB {null_constraint}"
                )
            )
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            _log.info("Migration : %s.%s promu de BLOB en MEDIUMBLOB", table, col)

    # (table, column, SQL type + constraint)
    _BOOL_COLUMNS: list[tuple[str, str, str]] = [
        ("difficulty_levels", "hide_label", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ]

    def _ensure_bool_columns(self, conn: Connection) -> None:
        """Ajoute les colonnes booléennes manquantes dans les schemas existants."""
        # MariaDB/MySQL requiert des backticks ;
        # SQLite et PostgreSQL acceptent les guillemets doubles.
        q = "`" if conn.dialect.name == "mysql" else '"'
        for table, col, definition in self._BOOL_COLUMNS:
            cols = {c["name"] for c in inspect(conn).get_columns(table)}
            if col not in cols:
                conn.execute(
                    text(
                        f"ALTER TABLE {q}{table}{q} ADD COLUMN {q}{col}{q} {definition}"
                    )
                )
                _log.info("Migration : colonne %s.%s ajoutée", table, col)

    # (table, column, SQL type + constraint)
    _TEXT_COLUMNS: list[tuple[str, str, str]] = [
        ("sources", "shortcut", f"VARCHAR({MAX_SOURCE_SHORTCUT}) NOT NULL DEFAULT ''"),
    ]

    def _ensure_text_columns(self, conn: Connection) -> None:
        """Ajoute les colonnes texte manquantes dans les schemas existants."""
        q = "`" if conn.dialect.name == "mysql" else '"'
        for table, col, definition in self._TEXT_COLUMNS:
            cols = {c["name"] for c in inspect(conn).get_columns(table)}
            if col not in cols:
                conn.execute(
                    text(
                        f"ALTER TABLE {q}{table}{q} ADD COLUMN {q}{col}{q} {definition}"
                    )
                )
                _log.info("Migration : colonne %s.%s ajoutée", table, col)

    @staticmethod
    def _enable_sqlite_fk(dbapi_conn, _record) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        _log.debug("Clés étrangères SQLite activées")

    @contextmanager
    def _tx(self) -> Generator[Connection, None, None]:
        assert self._engine, "Not connected"
        with self._engine.begin() as conn:
            yield conn

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def list_categories(self) -> list[Category]:
        with self._tx() as conn:
            rows = conn.execute(select(t_categories)).fetchall()
        _log.debug("Catégories : %d trouvées", len(rows))
        return sorted(
            [Category(id=r.id, name=r.name) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_category(self, category: Category) -> Category:
        with self._tx() as conn:
            if category.id is None:
                result = conn.execute(insert(t_categories).values(name=category.name))
                category.id = result.inserted_primary_key[0]
                _log.info("Catégorie créée : «%s» (id=%s)", category.name, category.id)
            else:
                conn.execute(
                    update(t_categories)
                    .where(t_categories.c.id == category.id)
                    .values(name=category.name)
                )
                _log.info(
                    "Catégorie mise à jour : «%s» (id=%s)", category.name, category.id
                )
        return category

    def delete_category(self, category_id: int) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_categories).where(t_categories.c.id == category_id))
        _log.info("Catégorie supprimée : id=%s", category_id)

    # ------------------------------------------------------------------
    # Units
    # ------------------------------------------------------------------

    def list_units(self) -> list[Unit]:
        with self._tx() as conn:
            rows = conn.execute(select(t_units)).fetchall()
        _log.debug("Unités : %d trouvées", len(rows))
        return sorted(
            [Unit(id=r.id, name=r.name, name_plural=r.name_plural) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_unit(self, unit: Unit) -> Unit:
        with self._tx() as conn:
            if unit.id is None:
                result = conn.execute(
                    insert(t_units).values(name=unit.name, name_plural=unit.name_plural)
                )
                unit.id = result.inserted_primary_key[0]
                _log.info("Unité créée : «%s» (id=%s)", unit.name, unit.id)
            else:
                conn.execute(
                    update(t_units)
                    .where(t_units.c.id == unit.id)
                    .values(name=unit.name, name_plural=unit.name_plural)
                )
                _log.info("Unité mise à jour : «%s» (id=%s)", unit.name, unit.id)
        return unit

    def delete_unit(self, unit_id: int) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_units).where(t_units.c.id == unit_id))
        _log.info("Unité supprimée : id=%s", unit_id)

    # ------------------------------------------------------------------
    # Ingredients
    # ------------------------------------------------------------------

    def list_ingredients(self) -> list[Ingredient]:
        with self._tx() as conn:
            rows = conn.execute(select(t_ingredients)).fetchall()
        _log.debug("Ingrédients : %d trouvés", len(rows))
        return sorted(
            [Ingredient(id=r.id, name=r.name, name_plural=r.name_plural) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_ingredient(self, ingredient: Ingredient) -> Ingredient:
        with self._tx() as conn:
            if ingredient.id is None:
                result = conn.execute(
                    insert(t_ingredients).values(
                        name=ingredient.name, name_plural=ingredient.name_plural
                    )
                )
                ingredient.id = result.inserted_primary_key[0]
                _log.info(
                    "Ingrédient créé : «%s» (id=%s)", ingredient.name, ingredient.id
                )
            else:
                conn.execute(
                    update(t_ingredients)
                    .where(t_ingredients.c.id == ingredient.id)
                    .values(name=ingredient.name, name_plural=ingredient.name_plural)
                )
                _log.info(
                    "Ingrédient mis à jour : «%s» (id=%s)",
                    ingredient.name,
                    ingredient.id,
                )
        return ingredient

    def delete_ingredient(self, ingredient_id: int) -> None:
        with self._tx() as conn:
            conn.execute(
                delete(t_ingredients).where(t_ingredients.c.id == ingredient_id)
            )
        _log.info("Ingrédient supprimé : id=%s", ingredient_id)

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def list_equipment(self) -> list[Equipment]:
        with self._tx() as conn:
            rows = conn.execute(select(t_equipment)).fetchall()
        _log.debug("Matériel : %d éléments trouvés", len(rows))
        return sorted(
            [Equipment(id=r.id, name=r.name, name_plural=r.name_plural) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_equipment(self, equipment: Equipment) -> Equipment:
        with self._tx() as conn:
            if equipment.id is None:
                result = conn.execute(
                    insert(t_equipment).values(
                        name=equipment.name, name_plural=equipment.name_plural
                    )
                )
                equipment.id = result.inserted_primary_key[0]
                _log.info("Matériel créé : «%s» (id=%s)", equipment.name, equipment.id)
            else:
                conn.execute(
                    update(t_equipment)
                    .where(t_equipment.c.id == equipment.id)
                    .values(name=equipment.name, name_plural=equipment.name_plural)
                )
                _log.info(
                    "Matériel mis à jour : «%s» (id=%s)", equipment.name, equipment.id
                )
        return equipment

    def delete_equipment(self, equipment_id: int) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_equipment).where(t_equipment.c.id == equipment_id))
        _log.info("Matériel supprimé : id=%s", equipment_id)

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def list_sources(self) -> list[Source]:
        with self._tx() as conn:
            rows = conn.execute(select(t_sources)).fetchall()
        _log.debug("Sources : %d trouvées", len(rows))
        return sorted(
            [Source(id=r.id, name=r.name, shortcut=r.shortcut) for r in rows],
            key=lambda x: _sort_key(re.sub(r"<[^>]+>", "", x.name)),
        )

    def save_source(self, source: Source) -> Source:
        with self._tx() as conn:
            if source.id is None:
                result = conn.execute(
                    insert(t_sources).values(name=source.name, shortcut=source.shortcut)
                )
                source.id = result.inserted_primary_key[0]
                _log.info("Source créée : «%s» (id=%s)", source.name, source.id)
            else:
                conn.execute(
                    update(t_sources)
                    .where(t_sources.c.id == source.id)
                    .values(name=source.name, shortcut=source.shortcut)
                )
                _log.info("Source mise à jour : «%s» (id=%s)", source.name, source.id)
        return source

    def delete_source(self, source_id: int) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_sources).where(t_sources.c.id == source_id))
        _log.info("Source supprimée : id=%s", source_id)

    # ------------------------------------------------------------------
    # Techniques
    # ------------------------------------------------------------------

    def list_techniques(self) -> list[Technique]:
        with self._tx() as conn:
            rows = conn.execute(select(t_techniques)).fetchall()
        _log.debug("Techniques : %d trouvées", len(rows))
        return sorted(
            [
                Technique(code=r.code, title=r.title, description=r.description)
                for r in rows
            ],
            key=lambda x: _sort_key(x.title),
        )

    def get_technique(self, code: str) -> Technique | None:
        with self._tx() as conn:
            row = conn.execute(
                select(t_techniques).where(t_techniques.c.code == code)
            ).fetchone()
        if row is None:
            _log.debug("Technique introuvable : %s", code)
            return None
        _log.debug("Technique chargée : %s", code)
        return Technique(code=row.code, title=row.title, description=row.description)

    def save_technique(self, technique: Technique) -> Technique:
        with self._tx() as conn:
            exists = conn.execute(
                select(t_techniques.c.code).where(t_techniques.c.code == technique.code)
            ).fetchone()
            if exists:
                conn.execute(
                    update(t_techniques)
                    .where(t_techniques.c.code == technique.code)
                    .values(title=technique.title, description=technique.description)
                )
                _log.info(
                    "Technique mise à jour : %s — %s", technique.code, technique.title
                )
            else:
                conn.execute(
                    insert(t_techniques).values(
                        code=technique.code,
                        title=technique.title,
                        description=technique.description,
                    )
                )
                _log.info("Technique créée : %s — %s", technique.code, technique.title)
        return technique

    def delete_technique(self, code: str) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_techniques).where(t_techniques.c.code == code))
        _log.info("Technique supprimée : %s", code)

    # ------------------------------------------------------------------
    # Difficulty levels
    # ------------------------------------------------------------------

    def list_difficulty_levels(self) -> list[DifficultyLevel]:
        with self._tx() as conn:
            rows = conn.execute(
                select(t_difficulty_levels).order_by(t_difficulty_levels.c.level)
            ).fetchall()
        return [
            DifficultyLevel(
                level=r.level,
                label=r.label,
                hide_label=bool(r.hide_label),
                mime_type=r.mime_type,
                data=bytes(r.data) if r.data else None,
            )
            for r in rows
        ]

    def delete_difficulty_level(self, level: int) -> None:
        if level <= 0:
            raise ValueError("Le niveau 0 ne peut pas être supprimé")
        with self._tx() as conn:
            conn.execute(
                delete(t_difficulty_levels).where(t_difficulty_levels.c.level == level)
            )
        _log.info("Niveau de difficulté supprimé : %d", level)

    def get_difficulty_level(self, level: int) -> DifficultyLevel | None:
        with self._tx() as conn:
            row = conn.execute(
                select(t_difficulty_levels).where(t_difficulty_levels.c.level == level)
            ).fetchone()
        if row is None:
            return None
        return DifficultyLevel(
            level=row.level,
            label=row.label,
            hide_label=bool(row.hide_label),
            mime_type=row.mime_type,
            data=bytes(row.data) if row.data else None,
        )

    def save_difficulty_level(self, dl: DifficultyLevel) -> DifficultyLevel:
        if not (MIN_DIFFICULTY <= dl.level <= MAX_DIFFICULTY):
            raise ValueError(
                f"Niveau de difficulté invalide : {dl.level}"
                f" (attendu {MIN_DIFFICULTY}–{MAX_DIFFICULTY})"
            )
        vals = {
            "label": dl.label,
            "hide_label": dl.hide_label,
            "mime_type": dl.mime_type,
            "data": dl.data,
        }
        with self._tx() as conn:
            exists = conn.execute(
                select(t_difficulty_levels.c.level).where(
                    t_difficulty_levels.c.level == dl.level
                )
            ).fetchone()
            if exists:
                conn.execute(
                    update(t_difficulty_levels)
                    .where(t_difficulty_levels.c.level == dl.level)
                    .values(**vals)
                )
                _log.info(
                    "Niveau de difficulté mis à jour : %d — «%s»", dl.level, dl.label
                )
            else:
                conn.execute(insert(t_difficulty_levels).values(level=dl.level, **vals))
                _log.info("Niveau de difficulté créé : %d — «%s»", dl.level, dl.label)
        return dl

    # ------------------------------------------------------------------
    # Recipes
    # ------------------------------------------------------------------

    def list_recipes(self) -> list[Recipe]:
        with self._tx() as conn:
            rows = conn.execute(
                select(
                    t_recipes.c.code,
                    t_recipes.c.name,
                    t_recipes.c.difficulty,
                    t_recipes.c.prep_time,
                    t_recipes.c.wait_time,
                    t_recipes.c.cook_time,
                )
            ).fetchall()
        _log.debug("Recettes : %d trouvées", len(rows))
        return sorted(
            [
                Recipe(
                    code=r.code,
                    name=r.name,
                    difficulty=r.difficulty,
                    prep_time=r.prep_time,
                    wait_time=r.wait_time,
                    cook_time=r.cook_time,
                )
                for r in rows
            ],
            key=lambda x: _sort_key(x.name),
        )

    def list_all_media(self) -> list[RecipeMedia]:
        """Return every recipe_media row ordered by recipe_code, position."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(t_recipe_media).order_by(
                    t_recipe_media.c.recipe_code, t_recipe_media.c.position
                )
            ).fetchall()
        return [
            RecipeMedia(
                id=r.id,
                recipe_code=r.recipe_code,
                position=r.position,
                code=r.code,
                mime_type=r.mime_type,
                data=bytes(r.data) if r.data else b"",
            )
            for r in rows
        ]

    def list_all_media_keys(self) -> list[tuple[str, str]]:
        """Return (recipe_code, code) pairs for all media, without loading BLOBs."""
        t = t_recipe_media
        with self._engine.connect() as conn:
            rows = conn.execute(
                select(t.c.recipe_code, t.c.code).order_by(
                    t.c.recipe_code, t.c.position
                )
            ).fetchall()
        return [(r.recipe_code, r.code) for r in rows]

    def get_media_data(self, recipe_code: str, code: str) -> bytes:
        """Return the BLOB for a single media entry (empty bytes if not found)."""
        t = t_recipe_media
        with self._engine.connect() as conn:
            row = conn.execute(
                select(t.c.data).where(t.c.recipe_code == recipe_code, t.c.code == code)
            ).fetchone()
        return bytes(row.data) if row and row.data else b""

    def save_recipe_media(self, media: RecipeMedia) -> None:
        """Update mime_type and data of a single recipe_media row (by id)."""
        with self._tx() as conn:
            conn.execute(
                update(t_recipe_media)
                .where(t_recipe_media.c.id == media.id)
                .values(mime_type=media.mime_type, data=media.data)
            )
        _log.debug(
            "Média %s:%s mis à jour (id=%s)", media.recipe_code, media.code, media.id
        )

    def get_recipe(self, code: str) -> Recipe | None:
        with self._tx() as conn:
            row = conn.execute(
                select(t_recipes).where(t_recipes.c.code == code)
            ).fetchone()
            if row is None:
                _log.debug("Recette introuvable : %s", code)
                return None

            recipe = Recipe(
                code=row.code,
                name=row.name,
                difficulty=row.difficulty,
                serving=row.serving or "",
                prep_time=row.prep_time,
                wait_time=row.wait_time,
                cook_time=row.cook_time,
                description=row.description,
                comments=row.comments,
                source_id=row.source_id,
            )
            recipe.categories = [
                r.category_id
                for r in conn.execute(
                    select(t_recipe_categories.c.category_id).where(
                        t_recipe_categories.c.recipe_code == code
                    )
                ).fetchall()
            ]
            recipe.ingredients = _select_recipe_rows(
                conn, t_recipe_ingredients, RecipeIngredient, code
            )
            recipe.equipment = _select_recipe_rows(
                conn, t_recipe_equipment, RecipeEquipment, code
            )
            recipe.media = [
                RecipeMedia(
                    id=r.id,
                    recipe_code=code,
                    position=r.position,
                    code=r.code,
                    mime_type=r.mime_type,
                    data=bytes(r.data) if r.data else b"",
                )
                for r in conn.execute(
                    select(t_recipe_media)
                    .where(t_recipe_media.c.recipe_code == code)
                    .order_by(t_recipe_media.c.position)
                ).fetchall()
            ]
        _log.debug(
            "Recette chargée : %s — %d catégories, %d ingrédients,"
            " %d matériels, %d médias",
            code,
            len(recipe.categories),
            len(recipe.ingredients),
            len(recipe.equipment),
            len(recipe.media),
        )
        return recipe

    def save_recipe(self, recipe: Recipe, original_code: str | None = None) -> Recipe:
        vals = dict(
            name=recipe.name,
            difficulty=recipe.difficulty,
            serving=recipe.serving,
            prep_time=recipe.prep_time,
            wait_time=recipe.wait_time,
            cook_time=recipe.cook_time,
            description=recipe.description,
            comments=recipe.comments,
            source_id=recipe.source_id,
        )
        lookup_code = (
            original_code
            if (original_code and original_code != recipe.code)
            else recipe.code
        )
        with self._tx() as conn:
            exists = conn.execute(
                select(t_recipes.c.code).where(t_recipes.c.code == lookup_code)
            ).fetchone()
            if exists:
                if lookup_code != recipe.code:
                    # Code renamed: delete old sub-tables then update PK
                    for tbl in (
                        t_recipe_categories,
                        t_recipe_ingredients,
                        t_recipe_equipment,
                        t_recipe_media,
                    ):
                        conn.execute(
                            delete(tbl).where(tbl.c.recipe_code == lookup_code)
                        )
                    conn.execute(
                        update(t_recipes)
                        .where(t_recipes.c.code == lookup_code)
                        .values(code=recipe.code, **vals)
                    )
                    _log.info(
                        "Recette renommée : %s → %s — «%s»",
                        lookup_code,
                        recipe.code,
                        recipe.name,
                    )
                else:
                    conn.execute(
                        update(t_recipes)
                        .where(t_recipes.c.code == recipe.code)
                        .values(**vals)
                    )
                    _log.info(
                        "Recette mise à jour : %s — «%s»"
                        " (%d catégories, %d ingrédients, %d médias)",
                        recipe.code,
                        recipe.name,
                        len(recipe.categories),
                        len(recipe.ingredients),
                        len(recipe.media),
                    )
            else:
                conn.execute(insert(t_recipes).values(code=recipe.code, **vals))
                _log.info(
                    "Recette créée : %s — «%s»"
                    " (%d catégories, %d ingrédients, %d médias)",
                    recipe.code,
                    recipe.name,
                    len(recipe.categories),
                    len(recipe.ingredients),
                    len(recipe.media),
                )

            conn.execute(
                delete(t_recipe_categories).where(
                    t_recipe_categories.c.recipe_code == recipe.code
                )
            )
            if recipe.categories:
                conn.execute(
                    insert(t_recipe_categories),
                    [
                        {"recipe_code": recipe.code, "category_id": cid}
                        for cid in recipe.categories
                    ],
                )

            _replace_recipe_rows(
                conn, t_recipe_ingredients, recipe.code, recipe.ingredients
            )
            _replace_recipe_rows(
                conn, t_recipe_equipment, recipe.code, recipe.equipment
            )

            conn.execute(
                delete(t_recipe_media).where(
                    t_recipe_media.c.recipe_code == recipe.code
                )
            )
            if recipe.media:
                conn.execute(
                    insert(t_recipe_media),
                    [
                        {
                            "recipe_code": recipe.code,
                            "position": m.position,
                            "code": m.code,
                            "mime_type": m.mime_type,
                            "data": m.data,
                        }
                        for m in recipe.media
                    ],
                )
        return recipe

    def delete_recipe(self, code: str) -> None:
        with self._tx() as conn:
            conn.execute(delete(t_recipes).where(t_recipes.c.code == code))
        _log.info("Recette supprimée : %s", code)

    def search_recipes(
        self,
        name: str = "",
        category_id: int | None = None,
        ingredient_id: int | None = None,
        difficulty: int | None = None,
        equipment_id: int | None = None,
    ) -> list[Recipe]:
        stmt = select(
            t_recipes.c.code,
            t_recipes.c.name,
            t_recipes.c.difficulty,
            t_recipes.c.prep_time,
            t_recipes.c.wait_time,
            t_recipes.c.cook_time,
        ).distinct()

        if category_id is not None:
            stmt = stmt.join(
                t_recipe_categories,
                and_(
                    t_recipe_categories.c.recipe_code == t_recipes.c.code,
                    t_recipe_categories.c.category_id == category_id,
                ),
            )
        if ingredient_id is not None:
            stmt = stmt.join(
                t_recipe_ingredients,
                and_(
                    t_recipe_ingredients.c.recipe_code == t_recipes.c.code,
                    t_recipe_ingredients.c.ingredient_id == ingredient_id,
                ),
            )
        if equipment_id is not None:
            stmt = stmt.join(
                t_recipe_equipment,
                and_(
                    t_recipe_equipment.c.recipe_code == t_recipes.c.code,
                    t_recipe_equipment.c.equipment_id == equipment_id,
                ),
            )
        if name:
            stmt = stmt.where(t_recipes.c.name.ilike(f"%{name}%"))
        if difficulty is not None:
            stmt = stmt.where(t_recipes.c.difficulty == difficulty)

        with self._tx() as conn:
            rows = conn.execute(stmt).fetchall()
        _log.debug(
            "Recherche recettes : name=%r cat=%s ing=%s diff=%s eq=%s → %d résultats",
            name,
            category_id,
            ingredient_id,
            difficulty,
            equipment_id,
            len(rows),
        )
        return sorted(
            [
                Recipe(
                    code=r.code,
                    name=r.name,
                    difficulty=r.difficulty,
                    prep_time=r.prep_time,
                    wait_time=r.wait_time,
                    cook_time=r.cook_time,
                )
                for r in rows
            ],
            key=lambda x: _sort_key(x.name),
        )

    # ------------------------------------------------------------------
    # Globals
    # ------------------------------------------------------------------

    def get_globals(self) -> dict[str, str]:
        """Retourne tous les paramètres globaux stockés dans la base."""
        with self._tx() as conn:
            rows = conn.execute(select(t_globals)).fetchall()
        return {r.key: r.value for r in rows}

    def set_globals(self, data: dict[str, str]) -> None:
        """Remplace tous les paramètres globaux par ceux fournis."""
        with self._tx() as conn:
            conn.execute(delete(t_globals))
            for key, value in data.items():
                conn.execute(insert(t_globals).values(key=key, value=value))
        _log.info("Paramètres globaux mis à jour : %d clé(s)", len(data))
