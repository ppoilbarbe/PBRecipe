from pathlib import Path

import pytest

from pbrecipe.database.database import Database
from pbrecipe.models import (
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Technique,
    Unit,
)


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def test_category_crud(db):
    cat = db.save_category(Category(name="Entrée"))
    assert cat.id is not None
    cats = db.list_categories()
    assert any(c.name == "Entrée" for c in cats)
    cat.name = "Plat"
    db.save_category(cat)
    assert db.list_categories()[0].name == "Plat"
    db.delete_category(cat.id)
    assert db.list_categories() == []


def test_recipe_roundtrip(db):
    unit = db.save_unit(Unit(name="g"))
    ing = db.save_ingredient(Ingredient(name="Farine"))
    cat = db.save_category(Category(name="Dessert"))

    recipe = Recipe(
        code="GATEAU_CHOCOLAT",
        name="Gâteau au chocolat",
        difficulty=2,
        prep_time=30,
        wait_time=60,
        description="<p>Mélanger.</p>",
        comments="<p>Excellent.</p>",
        categories=[cat.id],
        ingredients=[
            RecipeIngredient(
                recipe_code="GATEAU_CHOCOLAT",
                position=0,
                quantity="200",
                unit_id=unit.id,
                ingredient_id=ing.id,
            )
        ],
    )
    db.save_recipe(recipe)

    loaded = db.get_recipe("GATEAU_CHOCOLAT")
    assert loaded is not None
    assert loaded.name == "Gâteau au chocolat"
    assert loaded.total_time == 90
    assert cat.id in loaded.categories
    assert len(loaded.ingredients) == 1
    assert loaded.ingredients[0].unit_id == unit.id
    assert loaded.media == []


def test_search_recipes(db):
    cat = db.save_category(Category(name="Dessert"))
    db.save_recipe(
        Recipe(code="R1", name="Tarte Tatin", difficulty=1, categories=[cat.id])
    )
    db.save_recipe(Recipe(code="R2", name="Mousse Chocolat", difficulty=3))

    results = db.search_recipes(name="tarte")
    assert len(results) == 1
    assert results[0].code == "R1"

    results = db.search_recipes(difficulty=3)
    assert len(results) == 1
    assert results[0].code == "R2"

    results = db.search_recipes(category_id=cat.id)
    assert len(results) == 1


def test_sort_ligature_oe(db):
    # œ doit trier avec 'o', pas après 't' (bug : NFD n'expand pas les ligatures)
    for name in ["Tartare", "Œuf cocotte", "Omelette", "Salade"]:
        db.save_ingredient(Ingredient(name=name))
    names = [i.name for i in db.list_ingredients()]
    # "œuf" → "oeuf" : 'e' < 'm', donc avant "Omelette"
    assert names == ["Œuf cocotte", "Omelette", "Salade", "Tartare"]


def test_sort_ligature_ae(db):
    # æ doit trier avec 'a'
    for name in ["Basilic", "Æbleskiver", "Aneth", "Cerfeuil"]:
        db.save_ingredient(Ingredient(name=name))
    names = [i.name for i in db.list_ingredients()]
    assert names == ["Æbleskiver", "Aneth", "Basilic", "Cerfeuil"]


def test_technique_crud(db):
    tech = Technique(
        code="BRUNOISE", title="Brunoise", description="<p>Couper en dés.</p>"
    )
    db.save_technique(tech)
    fetched = db.get_technique("BRUNOISE")
    assert fetched is not None
    assert fetched.title == "Brunoise"
    db.delete_technique("BRUNOISE")
    assert db.get_technique("BRUNOISE") is None
