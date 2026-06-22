"""Tests des méthodes de Database non couvertes par test_sqlite_db."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.database.database import Database, _safe_url, _sort_key
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


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def test_check_schema_states(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'schema.db'}")
    d.connect()
    assert d.check_schema() == "empty"
    d.create_schema()
    assert d.check_schema() == "ok"
    d.disconnect()


def test_safe_url_masks_password():
    masked = _safe_url("mysql+pymysql://user:secret@host:3306/db")
    assert "secret" not in masked
    assert "***" in masked


def test_sort_key_ligatures():
    assert _sort_key("Œuf") == "oeuf"
    assert _sort_key("Æbleskiver").startswith("aebleskiver")
    assert _sort_key("Straße") == "strasse"


def test_unit_crud(db):
    u = db.save_unit(Unit(name="g", name_plural="g"))
    assert u.id is not None
    u.name = "kg"
    db.save_unit(u)
    assert any(x.name == "kg" for x in db.list_units())
    db.delete_unit(u.id)
    assert db.list_units() == []


def test_ingredient_crud(db):
    ing = db.save_ingredient(Ingredient(name="Sel"))
    ing.name = "Poivre"
    db.save_ingredient(ing)
    assert db.list_ingredients()[0].name == "Poivre"
    db.delete_ingredient(ing.id)
    assert db.list_ingredients() == []


def test_source_crud(db):
    s = db.save_source(Source(name="Livre"))
    s.name = "Magazine"
    db.save_source(s)
    assert db.list_sources()[0].name == "Magazine"
    db.delete_source(s.id)
    assert db.list_sources() == []


def test_technique_update(db):
    db.save_technique(Technique(code="BRUN", title="Brunoise"))
    db.save_technique(Technique(code="BRUN", title="Brunoise modifiée"))
    assert db.get_technique("BRUN").title == "Brunoise modifiée"
    assert len(db.list_techniques()) == 1


def test_difficulty_levels_defaults_created(db):
    levels = db.list_difficulty_levels()
    assert [dl.level for dl in levels] == [0, 1, 2, 3]


def test_difficulty_level_get_and_save(db):
    dl = db.get_difficulty_level(2)
    assert dl is not None
    dl.label = "Intermédiaire"
    dl.data = b"\x89PNG"
    dl.hide_label = True
    db.save_difficulty_level(dl)
    reloaded = db.get_difficulty_level(2)
    assert reloaded.label == "Intermédiaire"
    assert reloaded.data == b"\x89PNG"
    assert reloaded.hide_label is True
    assert db.get_difficulty_level(99) is None


def test_difficulty_level_invalid(db):
    with pytest.raises(ValueError):
        db.save_difficulty_level(DifficultyLevel(level=5, label="x"))


def test_recipe_rename(db):
    db.save_recipe(Recipe(code="OLD", name="Ancienne"))
    db.save_recipe(Recipe(code="NEW", name="Nouvelle"), original_code="OLD")
    assert db.get_recipe("OLD") is None
    assert db.get_recipe("NEW").name == "Nouvelle"


def test_recipe_update_in_place(db):
    db.save_recipe(Recipe(code="R", name="Un"))
    db.save_recipe(Recipe(code="R", name="Deux"))
    assert db.get_recipe("R").name == "Deux"


def test_recipe_with_media(db):
    recipe = Recipe(
        code="PHOTO",
        name="Avec photo",
        media=[
            RecipeMedia(recipe_code="PHOTO", position=0, code="IMG1", data=b"jpegdata")
        ],
    )
    db.save_recipe(recipe)
    loaded = db.get_recipe("PHOTO")
    assert len(loaded.media) == 1
    assert loaded.media[0].data == b"jpegdata"


def test_list_all_media(db):
    db.save_recipe(
        Recipe(
            code="R",
            name="R",
            media=[RecipeMedia(recipe_code="R", position=0, code="A", data=b"x")],
        )
    )
    media = db.list_all_media()
    assert media == [("R", "A", b"x")]


def test_delete_recipe(db):
    db.save_recipe(Recipe(code="DEL", name="Suppr"))
    db.delete_recipe("DEL")
    assert db.get_recipe("DEL") is None


def test_get_recipe_missing(db):
    assert db.get_recipe("UNKNOWN") is None


def test_search_by_ingredient(db):
    ing = db.save_ingredient(Ingredient(name="Tomate"))
    db.save_recipe(
        Recipe(
            code="SALADE",
            name="Salade",
            ingredients=[
                RecipeIngredient(recipe_code="SALADE", position=0, ingredient_id=ing.id)
            ],
        )
    )
    db.save_recipe(Recipe(code="AUTRE", name="Autre"))
    results = db.search_recipes(ingredient_id=ing.id)
    assert [r.code for r in results] == ["SALADE"]


def test_globals(db):
    assert db.get_globals() == {}
    db.set_globals({"site_title": "Test", "key2": "val"})
    assert db.get_globals() == {"site_title": "Test", "key2": "val"}
    db.set_globals({"only": "one"})
    assert db.get_globals() == {"only": "one"}


def test_clear_all_data(db):
    db.save_category(Category(name="C"))
    db.save_recipe(Recipe(code="R", name="R"))
    db.set_globals({"k": "v"})
    db.clear_all_data()
    assert db.list_categories() == []
    assert db.list_recipes() == []
    assert db.get_globals() == {}
