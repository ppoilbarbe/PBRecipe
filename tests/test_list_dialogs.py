"""Tests des dialogues de gestion de listes (catégories, unités, etc.)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from pbrecipe.config.app_config import AppConfig
from pbrecipe.database.database import Database
from pbrecipe.models import Category, Ingredient, Source
from pbrecipe.ui.dialogs.category_dialog import CategoryDialog
from pbrecipe.ui.dialogs.ingredient_dialog import IngredientDialog
from pbrecipe.ui.dialogs.source_dialog import SourceDialog
from pbrecipe.ui.dialogs.unit_dialog import UnitDialog


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def test_category_dialog_refresh(qtbot, db):
    db.save_category(Category(name="Entrée"))
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 1
    assert dlg._list.item(0).text() == "Entrée"


def test_category_add(qtbot, db, monkeypatch):
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Dessert", True))
    dlg._add()
    assert any(c.name == "Dessert" for c in db.list_categories())


def test_category_add_cancelled(qtbot, db, monkeypatch):
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("", False))
    dlg._add()
    assert db.list_categories() == []


def test_category_edit(qtbot, db, monkeypatch):
    db.save_category(Category(name="Vieux"))
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Neuf", True))
    dlg._edit()
    assert db.list_categories()[0].name == "Neuf"


def test_category_edit_no_selection(qtbot, db):
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    dlg._edit()  # ne doit rien faire, pas de sélection


def test_category_delete_confirmed(qtbot, db, monkeypatch):
    db.save_category(Category(name="X"))
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dlg._delete()
    assert db.list_categories() == []


def test_category_delete_refused(qtbot, db, monkeypatch):
    db.save_category(Category(name="X"))
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )
    dlg._delete()
    assert len(db.list_categories()) == 1


def test_category_delete_no_selection(qtbot, db):
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    dlg._delete()


def test_source_dialog(qtbot, db, monkeypatch):
    db.save_source(Source(name="Livre"))
    dlg = SourceDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 1
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Web", True))
    dlg._add()
    assert any(s.name == "Web" for s in db.list_sources())


def test_unit_dialog_add_edit(qtbot, db, monkeypatch):
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(
        "pbrecipe.ui.dialogs.unit_dialog._plural_dialog",
        lambda *a, **k: ("L", "litres", True),
    )
    dlg._add()
    units = db.list_units()
    assert units[0].name == "L"
    assert units[0].name_plural == "litres"
    assert dlg._list.item(0).text() == "L / litres"

    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        "pbrecipe.ui.dialogs.unit_dialog._plural_dialog",
        lambda *a, **k: ("mL", "millilitres", True),
    )
    dlg._edit()
    assert db.list_units()[0].name == "mL"


def test_unit_dialog_add_cancelled(qtbot, db, monkeypatch):
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(
        "pbrecipe.ui.dialogs.unit_dialog._plural_dialog",
        lambda *a, **k: ("", "", False),
    )
    dlg._add()
    assert db.list_units() == []


def test_unit_dialog_edit_no_selection(qtbot, db):
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    dlg._edit()


def test_ingredient_dialog(qtbot, db, monkeypatch):
    dlg = IngredientDialog(db)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(
        "pbrecipe.ui.dialogs.ingredient_dialog._plural_dialog",
        lambda *a, **k: ("Oeuf", "Oeufs", True),
    )
    dlg._add()
    ings = db.list_ingredients()
    assert ings[0].name == "Oeuf"
    assert dlg._list.item(0).text() == "Oeuf / Oeufs"

    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        "pbrecipe.ui.dialogs.ingredient_dialog._plural_dialog",
        lambda *a, **k: ("Oeuf frais", "", True),
    )
    dlg._edit()
    assert db.list_ingredients()[0].name == "Oeuf frais"


def test_ingredient_item_name_no_plural(qtbot, db):
    db.save_ingredient(Ingredient(name="Sel"))
    dlg = IngredientDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._list.item(0).text() == "Sel"


def test_dialog_geometry_persisted(qtbot, db, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = AppConfig()
    cfg.dialog_geometries["CategoryDialog"] = {
        "x": 50,
        "y": 60,
        "width": 400,
        "height": 300,
    }
    cfg.save()  # _init_geometry relit depuis le disque
    dlg = CategoryDialog(db)
    qtbot.addWidget(dlg)
    assert dlg.width() == 400
    dlg.done(0)
    assert "CategoryDialog" in AppConfig.load().dialog_geometries
