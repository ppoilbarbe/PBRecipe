from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import (
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

from pbrecipe.database.schema import (
    metadata,
    t_categories,
    t_difficulty_levels,
    t_ingredients,
    t_recipe_categories,
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
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeMedia,
    Source,
    Technique,
    Unit,
)

_log = logging.getLogger(__name__)

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


def _safe_url(url: str) -> str:
    return re.sub(r"(://[^:@/]+:)[^@/]+(@)", r"\1***\2", url)


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
            self._migrate(conn)
        _log.debug("Schéma vérifié/créé")

    def clear_all_data(self) -> None:
        """Delete all rows from every table, preserving the schema."""
        assert self._engine
        with self._engine.begin() as conn:
            for tbl in (
                t_recipe_media,
                t_recipe_ingredients,
                t_recipe_categories,
                t_recipes,
                t_techniques,
                t_sources,
                t_ingredients,
                t_units,
                t_categories,
                t_difficulty_levels,
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

        # v2 : ajout de cook_time
        existing_cols = {c["name"] for c in inspect(conn).get_columns("recipes")}
        if "cook_time" not in existing_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN cook_time INTEGER"))
            _log.info("Migration : colonne recipes.cook_time ajoutée")

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
            [Unit(id=r.id, name=r.name) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_unit(self, unit: Unit) -> Unit:
        with self._tx() as conn:
            if unit.id is None:
                result = conn.execute(insert(t_units).values(name=unit.name))
                unit.id = result.inserted_primary_key[0]
                _log.info("Unité créée : «%s» (id=%s)", unit.name, unit.id)
            else:
                conn.execute(
                    update(t_units)
                    .where(t_units.c.id == unit.id)
                    .values(name=unit.name)
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
            [Ingredient(id=r.id, name=r.name) for r in rows],
            key=lambda x: _sort_key(x.name),
        )

    def save_ingredient(self, ingredient: Ingredient) -> Ingredient:
        with self._tx() as conn:
            if ingredient.id is None:
                result = conn.execute(
                    insert(t_ingredients).values(name=ingredient.name)
                )
                ingredient.id = result.inserted_primary_key[0]
                _log.info(
                    "Ingrédient créé : «%s» (id=%s)", ingredient.name, ingredient.id
                )
            else:
                conn.execute(
                    update(t_ingredients)
                    .where(t_ingredients.c.id == ingredient.id)
                    .values(name=ingredient.name)
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
    # Sources
    # ------------------------------------------------------------------

    def list_sources(self) -> list[Source]:
        with self._tx() as conn:
            rows = conn.execute(select(t_sources)).fetchall()
        _log.debug("Sources : %d trouvées", len(rows))
        return sorted(
            [Source(id=r.id, name=r.name) for r in rows],
            key=lambda x: _sort_key(re.sub(r"<[^>]+>", "", x.name)),
        )

    def save_source(self, source: Source) -> Source:
        with self._tx() as conn:
            if source.id is None:
                result = conn.execute(insert(t_sources).values(name=source.name))
                source.id = result.inserted_primary_key[0]
                _log.info("Source créée : «%s» (id=%s)", source.name, source.id)
            else:
                conn.execute(
                    update(t_sources)
                    .where(t_sources.c.id == source.id)
                    .values(name=source.name)
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
                mime_type=r.mime_type,
                data=bytes(r.data) if r.data else None,
            )
            for r in rows
        ]

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
            mime_type=row.mime_type,
            data=bytes(row.data) if row.data else None,
        )

    def save_difficulty_level(self, dl: DifficultyLevel) -> DifficultyLevel:
        if not (0 <= dl.level <= 3):
            raise ValueError(
                f"Niveau de difficulté invalide : {dl.level} (attendu 0–3)"
            )
        vals = {"label": dl.label, "mime_type": dl.mime_type, "data": dl.data}
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
            recipe.ingredients = [
                RecipeIngredient(
                    id=r.id,
                    recipe_code=code,
                    position=r.position,
                    prefix=r.prefix,
                    quantity=r.quantity,
                    unit_id=r.unit_id,
                    separator=r.separator,
                    ingredient_id=r.ingredient_id,
                    suffix=r.suffix,
                )
                for r in conn.execute(
                    select(t_recipe_ingredients)
                    .where(t_recipe_ingredients.c.recipe_code == code)
                    .order_by(t_recipe_ingredients.c.position)
                ).fetchall()
            ]
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
            "Recette chargée : %s — %d catégories, %d ingrédients, %d médias",
            code,
            len(recipe.categories),
            len(recipe.ingredients),
            len(recipe.media),
        )
        return recipe

    def save_recipe(self, recipe: Recipe) -> Recipe:
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
        with self._tx() as conn:
            exists = conn.execute(
                select(t_recipes.c.code).where(t_recipes.c.code == recipe.code)
            ).fetchone()
            if exists:
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

            conn.execute(
                delete(t_recipe_ingredients).where(
                    t_recipe_ingredients.c.recipe_code == recipe.code
                )
            )
            if recipe.ingredients:
                conn.execute(
                    insert(t_recipe_ingredients),
                    [
                        {
                            "recipe_code": recipe.code,
                            "position": i.position,
                            "prefix": i.prefix,
                            "quantity": i.quantity,
                            "unit_id": i.unit_id,
                            "separator": i.separator,
                            "ingredient_id": i.ingredient_id,
                            "suffix": i.suffix,
                        }
                        for i in recipe.ingredients
                    ],
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
        if name:
            stmt = stmt.where(t_recipes.c.name.ilike(f"%{name}%"))
        if difficulty is not None:
            stmt = stmt.where(t_recipes.c.difficulty == difficulty)

        with self._tx() as conn:
            rows = conn.execute(stmt).fetchall()
        _log.debug(
            "Recherche recettes : name=%r cat=%s ing=%s diff=%s → %d résultats",
            name,
            category_id,
            ingredient_id,
            difficulty,
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
