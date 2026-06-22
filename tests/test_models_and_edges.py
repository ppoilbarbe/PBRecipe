"""Tests du modèle Recipe et de branches d'import YAML rarement atteintes."""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from pbrecipe.database.database import Database
from pbrecipe.export.yaml_io import YamlImport
from pbrecipe.models import Recipe


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def test_total_time_none_when_unset():
    assert Recipe(code="R", name="R").total_time is None


def test_total_time_partial():
    assert Recipe(code="R", name="R", prep_time=30).total_time == 30
    assert Recipe(code="R", name="R", cook_time=10, wait_time=5).total_time == 15


def _write(path: Path, doc) -> None:
    yaml = YAML()
    with open(path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)


def test_import_globals_not_dict(db, tmp_path):
    path = tmp_path / "g.yaml"
    _write(path, {"globals": "notadict"})
    YamlImport(db).run(str(path))
    assert db.get_globals() == {}


def test_import_recipe_with_non_dict_sub_entries(db, tmp_path):
    doc = {
        "recipes": [
            {
                "code": "R",
                "name": "R",
                "ingredients": ["notadict", {"ingredient": "Sel"}],
                "media": ["notadict"],
            }
        ]
    }
    path = tmp_path / "r.yaml"
    _write(path, doc)
    YamlImport(db).run(str(path))
    loaded = db.get_recipe("R")
    assert len(loaded.ingredients) == 1
    assert loaded.media == []
