"""Tests du helper plural_name_dialog (unité / ingrédient / matériel)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from pbrecipe.constants import MAX_INGREDIENT_NAME, MAX_UNIT_NAME
from pbrecipe.database.database import Database
from pbrecipe.models import Source
from pbrecipe.ui.dialogs import _plural_list_dialog as pld_mod
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
        pld_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    name, plural, ok = pld_mod.plural_name_dialog(
        dlg, "T", MAX_UNIT_NAME, "L", "litres"
    )
    assert ok is True
    assert name == "L"
    assert plural == "litres"


def test_unit_plural_dialog_reject(qtbot, db, monkeypatch):
    monkeypatch.setattr(
        pld_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )
    dlg = UnitDialog(db)
    qtbot.addWidget(dlg)
    _name, _plural, ok = pld_mod.plural_name_dialog(dlg, "T", MAX_UNIT_NAME)
    assert ok is False


def test_ingredient_plural_dialog_accept(qtbot, db, monkeypatch):
    monkeypatch.setattr(
        pld_mod.QDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    dlg = IngredientDialog(db)
    qtbot.addWidget(dlg)
    name, plural, ok = pld_mod.plural_name_dialog(
        dlg, "T", MAX_INGREDIENT_NAME, "Oeuf", "Oeufs"
    )
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
