"""Tests des helpers _plural_dialog (unité / ingrédient) sans monkeypatch."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from pbrecipe.database.database import Database
from pbrecipe.models import Source
from pbrecipe.ui.dialogs import ingredient_dialog as ing_mod
from pbrecipe.ui.dialogs import unit_dialog as unit_mod
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


def test_unit_plural_dialog_accept(qtbot, db, monkeypatch):
    monkeypatch.setattr(
        unit_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    name, plural, ok = unit_mod._plural_dialog(dlg, "T", "L", "litres")
    assert ok is True
    assert name == "L"
    assert plural == "litres"


def test_unit_plural_dialog_reject(qtbot, db, monkeypatch):
    monkeypatch.setattr(
        unit_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    _name, _plural, ok = unit_mod._plural_dialog(dlg, "T")
    assert ok is False


def test_ingredient_plural_dialog_accept(qtbot, db, monkeypatch):
    monkeypatch.setattr(
        ing_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    dlg = IngredientDialog(db)
    qtbot.addWidget(dlg)
    name, plural, ok = ing_mod._plural_dialog(dlg, "T", "Oeuf", "Oeufs")
    assert ok is True
    assert (name, plural) == ("Oeuf", "Oeufs")


def test_source_delete_item(qtbot, db, monkeypatch):
    db.save_source(Source(name="Livre"))
    dlg = SourceDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dlg._delete()
    assert db.list_sources() == []
