import os
from pathlib import Path

import pytest

from pbrecipe.database.database import Database
from pbrecipe.models import (
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Source,
    Technique,
    Unit,
)


def test_create_php_test_db():
    """Crée la base SQLite utilisée par la suite PHPUnit.

    Skippé quand PBRECIPE_TEST_DB n'est pas défini (make test normal).
    """
    path_str = os.environ.get("PBRECIPE_TEST_DB")
    if not path_str:
        pytest.skip("PBRECIPE_TEST_DB non défini — réservé à make test-php")

    db_path = Path(path_str)
    if db_path.exists():
        db_path.unlink()

    db = Database(f"sqlite:///{db_path}")
    db.connect()
    db.create_schema()

    cat_dessert = db.save_category(Category(name="Dessert"))
    cat_entree = db.save_category(Category(name="Entrée"))
    unit_g = db.save_unit(Unit(name="g", name_plural="g"))
    unit_ml = db.save_unit(Unit(name="ml", name_plural="ml"))
    ing_farine = db.save_ingredient(Ingredient(name="Farine", name_plural="Farines"))
    ing_sucre = db.save_ingredient(Ingredient(name="Sucre", name_plural="Sucres"))
    source = db.save_source(Source(name="Mon livre"))

    db.save_technique(
        Technique(
            code="BRUNOISE",
            title="Brunoise",
            description="<p>Couper en petits dés.</p>",
        )
    )
    db.save_technique(
        Technique(
            code="JULIENNE",
            title="Julienne",
            description="<p>Couper en fines lamelles. [TECH:BRUNOISE]</p>",
        )
    )

    db.save_recipe(
        Recipe(
            code="GATEAU",
            name="Gâteau au chocolat",
            difficulty=2,
            prep_time=30,
            wait_time=45,
            description="<p>Mélanger les ingrédients. [TECH:BRUNOISE]</p>",
            comments="<p>Excellent avec de la crème. [RECIPE:TARTE]</p>",
            source_id=source.id,
            categories=[cat_dessert.id],
            ingredients=[
                RecipeIngredient(
                    recipe_code="GATEAU",
                    position=0,
                    quantity="200",
                    unit_id=unit_g.id,
                    separator="de",
                    ingredient_id=ing_farine.id,
                ),
                RecipeIngredient(
                    recipe_code="GATEAU",
                    position=1,
                    quantity="100",
                    unit_id=unit_ml.id,
                    separator="de",
                    ingredient_id=ing_sucre.id,
                    suffix="vanillé",
                ),
            ],
        )
    )
    db.save_recipe(
        Recipe(
            code="TARTE",
            name="Tarte aux pommes",
            difficulty=1,
            prep_time=20,
            wait_time=40,
            description="<p>Préparer la pâte brisée.</p>",
            categories=[cat_entree.id],
        )
    )

    db.disconnect()

    assert db_path.exists()
