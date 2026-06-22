"""Tests d'export et import YAML (round-trip complet)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from pbrecipe.database.database import Database
from pbrecipe.export.yaml_io import YamlExport, YamlImport
from pbrecipe.models import (
    Category,
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


def _populate(db):
    cat = db.save_category(Category(name="Dessert"))
    unit = db.save_unit(Unit(name="g", name_plural="g"))
    ing = db.save_ingredient(Ingredient(name="Farine", name_plural="Farines"))
    src = db.save_source(Source(name="Grand-mère"))
    db.save_technique(Technique(code="ZESTE", title="Zester", description="<p>x</p>"))
    db.set_globals({"site_title": "Recettes"})
    dl = db.get_difficulty_level(1)
    dl.data = b"icondata"
    dl.hide_label = True
    db.save_difficulty_level(dl)
    recipe = Recipe(
        code="GATEAU",
        name="Gâteau",
        difficulty=2,
        serving="6 parts",
        prep_time=30,
        cook_time=45,
        description="<p>Cuire.</p>",
        comments="<p>Bon.</p>",
        source_id=src.id,
        categories=[cat.id],
        ingredients=[
            RecipeIngredient(
                recipe_code="GATEAU",
                position=0,
                prefix="environ",
                quantity="200",
                unit_id=unit.id,
                ingredient_id=ing.id,
                separator="de",
                suffix="tamisée",
                unit_plural=False,
                ingredient_plural=True,
            )
        ],
        media=[RecipeMedia(recipe_code="GATEAU", position=0, code="IMG1", data=b"jpg")],
    )
    db.save_recipe(recipe)


def test_export_creates_file(db, tmp_path):
    _populate(db)
    out = tmp_path / "export.yaml"
    YamlExport(db).run(str(out))
    assert out.exists()
    yaml = YAML()
    doc = yaml.load(out.read_text(encoding="utf-8"))
    assert doc["globals"] == {"site_title": "Recettes"}
    assert "Dessert" in doc["categories"]
    assert doc["recipes"][0]["code"] == "GATEAU"
    assert doc["recipes"][0]["source"] == "Grand-mère"
    assert doc["recipes"][0]["ingredients"][0]["ingredient"] == "Farine"
    assert doc["recipes"][0]["media"][0]["data"] == base64.b64encode(b"jpg").decode()


def test_export_with_progress(db, tmp_path):
    _populate(db)
    calls = []
    YamlExport(db).run(str(tmp_path / "e.yaml"), progress=lambda *a: calls.append(a))
    assert calls


def test_roundtrip_import(db, tmp_path):
    _populate(db)
    out = tmp_path / "export.yaml"
    YamlExport(db).run(str(out))

    db2 = Database(f"sqlite:///{tmp_path / 'dest.db'}")
    db2.connect()
    db2.create_schema()
    stats = YamlImport(db2).run(str(out))
    assert stats["recipes_created"] == 1
    loaded = db2.get_recipe("GATEAU")
    assert loaded.name == "Gâteau"
    assert loaded.serving == "6 parts"
    assert len(loaded.ingredients) == 1
    assert loaded.ingredients[0].ingredient_plural is True
    assert len(loaded.media) == 1
    assert loaded.media[0].data == b"jpg"
    cats = {c.id: c.name for c in db2.list_categories()}
    assert "Dessert" in cats.values()
    assert db2.get_globals()["site_title"] == "Recettes"
    assert db2.get_technique("ZESTE") is not None
    dl = db2.get_difficulty_level(1)
    assert dl.data == b"icondata"
    assert dl.hide_label is True
    db2.disconnect()


def test_import_updates_existing(db, tmp_path):
    _populate(db)
    out = tmp_path / "e.yaml"
    YamlExport(db).run(str(out))
    stats = YamlImport(db).run(str(out))
    assert stats["recipes_updated"] == 1
    assert stats["recipes_created"] == 0


def test_import_replace_clears(db, tmp_path):
    _populate(db)
    out = tmp_path / "e.yaml"
    YamlExport(db).run(str(out))
    db.save_recipe(Recipe(code="EXTRA", name="Extra"))
    YamlImport(db).run(str(out), replace=True)
    assert db.get_recipe("EXTRA") is None
    assert db.get_recipe("GATEAU") is not None


def test_import_progress(db, tmp_path):
    _populate(db)
    out = tmp_path / "e.yaml"
    YamlExport(db).run(str(out))
    calls = []
    YamlImport(db).run(str(out), progress=lambda *a: calls.append(a))
    assert calls


def _write_yaml(path: Path, doc: dict) -> None:
    yaml = YAML()
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)


def test_import_creates_missing_entities_on_the_fly(db, tmp_path):
    doc = {
        "recipes": [
            {
                "code": "R",
                "name": "R",
                "categories": ["NouvelleCat"],
                "source": "NouvelleSource",
                "ingredients": [{"unit": "NouvelleUnite", "ingredient": "NouvelIng"}],
            }
        ]
    }
    path = tmp_path / "i.yaml"
    _write_yaml(path, doc)
    YamlImport(db).run(str(path))
    assert any(c.name == "NouvelleCat" for c in db.list_categories())
    assert any(s.name == "NouvelleSource" for s in db.list_sources())
    assert any(u.name == "NouvelleUnite" for u in db.list_units())
    assert any(i.name == "NouvelIng" for i in db.list_ingredients())


def test_import_units_and_ingredients_update_plural(db, tmp_path):
    db.save_unit(Unit(name="g", name_plural="old"))
    db.save_ingredient(Ingredient(name="Sel", name_plural="old"))
    doc = {
        "units": [{"name": "g", "name_plural": "grammes"}],
        "ingredients": [{"name": "Sel", "name_plural": "Sels"}],
    }
    path = tmp_path / "u.yaml"
    _write_yaml(path, doc)
    YamlImport(db).run(str(path))
    assert next(u for u in db.list_units() if u.name == "g").name_plural == "grammes"
    assert (
        next(i for i in db.list_ingredients() if i.name == "Sel").name_plural == "Sels"
    )


def test_import_rejects_non_dict_root(db, tmp_path):
    path = tmp_path / "bad.yaml"
    yaml = YAML()
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump([1, 2, 3], fh)
    with pytest.raises(ValueError):
        YamlImport(db).run(str(path))


def test_import_skips_invalid_entries(db, tmp_path):
    doc = {
        "techniques": [
            "notadict",
            {"title": "sans code"},
            {"code": "OK", "title": "T"},
        ],
        "difficulty_levels": [
            "notadict",
            {"level": 99},
            {"level": 1, "label": "Facile", "data": "###invalid base64###"},
        ],
        "units": [{"name": ""}],
        "ingredients": [{"name": ""}],
        "recipes": ["notadict", {"name": "sans code"}],
    }
    path = tmp_path / "x.yaml"
    _write_yaml(path, doc)
    stats = YamlImport(db).run(str(path))
    assert db.get_technique("OK") is not None
    assert stats["recipes_created"] == 0


def test_import_difficulty_too_large_raises(db, tmp_path, monkeypatch):
    # On abaisse la limite pour éviter de générer 22 Mo en mémoire.
    monkeypatch.setattr("pbrecipe.export.yaml_io.MAX_MEDIA_BYTES", 100)
    big = base64.b64encode(b"\x00" * 101).decode()
    doc = {"difficulty_levels": [{"level": 1, "data": big}]}
    path = tmp_path / "big.yaml"
    _write_yaml(path, doc)
    with pytest.raises(ValueError):
        YamlImport(db).run(str(path))


def test_import_media_invalid_base64_skipped(db, tmp_path):
    doc = {
        "recipes": [
            {
                "code": "R",
                "name": "R",
                "media": [{"code": "X", "data": "###invalid###"}],
            }
        ]
    }
    path = tmp_path / "m.yaml"
    _write_yaml(path, doc)
    YamlImport(db).run(str(path))
    assert db.get_recipe("R").media == []


def test_import_media_too_large_raises(db, tmp_path, monkeypatch):
    # On abaisse la limite pour éviter de générer 22 Mo en mémoire.
    monkeypatch.setattr("pbrecipe.export.yaml_io.MAX_MEDIA_BYTES", 100)
    big = base64.b64encode(b"\x00" * 101).decode()
    doc = {
        "recipes": [{"code": "R", "name": "R", "media": [{"code": "X", "data": big}]}]
    }
    path = tmp_path / "mb.yaml"
    _write_yaml(path, doc)
    with pytest.raises(ValueError):
        YamlImport(db).run(str(path))
