"""Tests des dialogues Techniques et Niveaux de difficulté."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from pbrecipe.database.database import Database
from pbrecipe.models import Technique
from pbrecipe.ui.dialogs import difficulty_dialog as dd
from pbrecipe.ui.dialogs.difficulty_dialog import (
    DifficultyDialog,
    _mime_from_path,
    _pixmap_from_bytes,
)
from pbrecipe.ui.dialogs.technique_dialog import (
    TechniqueDialog,
    TechniqueEditDialog,
)

# Un PNG 2x2 valide (généré par Qt).
_PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd49a73"
    "000000097048597300000f6100000f6101a83fa7690000001649444154089963fc"
    "cfc0c0c0c0c0c4c0c0c0c0c000000d1d01030cc7e7890000000049454e44ae426082"
)


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


# --- TechniqueEditDialog ---


def test_technique_edit_accept(qtbot, db):
    dlg = TechniqueEditDialog(Technique(code="abc", title="T"), db)
    qtbot.addWidget(dlg)
    dlg._code_edit.setText("xyz")
    dlg._title_edit.setText("Titre")
    dlg._accept()
    assert dlg.technique.code == "XYZ"
    assert dlg.technique.title == "Titre"


def test_technique_edit_check_spelling(qtbot, db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.run_spellcheck",
        lambda items, parent: captured.setdefault("items", items),
    )
    dlg = TechniqueEditDialog(Technique(code="X", title="Titre"), db)
    qtbot.addWidget(dlg)
    dlg._check_spelling()
    assert captured["items"][0][0] == "Titre"


# --- TechniqueDialog ---


def test_technique_dialog_refresh(qtbot, db):
    db.save_technique(Technique(code="BR", title="Brunoise"))
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 1
    assert "BR" in dlg._list.item(0).text()


def test_technique_dialog_add(qtbot, db, monkeypatch):
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)

    def fake_exec(self):
        self._technique.code = "NEW"
        self._technique.title = "Nouvelle"
        return 1

    monkeypatch.setattr(TechniqueEditDialog, "exec", fake_exec)
    dlg._add()
    assert db.get_technique("NEW") is not None


def test_technique_dialog_add_duplicate(qtbot, db, monkeypatch):
    db.save_technique(Technique(code="DUP", title="Existante"))
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)

    def fake_exec(self):
        self._technique.code = "DUP"
        self._technique.title = "Doublon"
        return 1

    monkeypatch.setattr(TechniqueEditDialog, "exec", fake_exec)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", True)
    )
    dlg._add()
    assert warned.get("w") is True
    assert db.get_technique("DUP").title == "Existante"


def test_technique_dialog_edit(qtbot, db, monkeypatch):
    db.save_technique(Technique(code="ED", title="Avant"))
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)

    def fake_exec(self):
        self._technique.title = "Après"
        return 1

    monkeypatch.setattr(TechniqueEditDialog, "exec", fake_exec)
    dlg._edit()
    assert db.get_technique("ED").title == "Après"


def test_technique_dialog_edit_no_selection(qtbot, db):
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)
    dlg._edit()


def test_technique_dialog_delete(qtbot, db, monkeypatch):
    db.save_technique(Technique(code="DEL", title="Suppr"))
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    dlg._delete()
    assert db.get_technique("DEL") is None


def test_technique_dialog_delete_no_selection(qtbot, db):
    dlg = TechniqueDialog(db)
    qtbot.addWidget(dlg)
    dlg._delete()


# --- DifficultyDialog ---


def test_mime_from_path():
    assert _mime_from_path("x.png") == "image/png"
    assert _mime_from_path("x.unknown") == "image/jpeg"


def test_pixmap_from_bytes():
    px = _pixmap_from_bytes(_PNG_1PX)
    assert not px.isNull()


def test_difficulty_dialog_loads_levels(qtbot, db):
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 4
    assert dlg._current_row == 0


def test_difficulty_dialog_edit_label(qtbot, db):
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(1)
    dlg._label_edit.setText("Très facile")
    dlg._hide_label_cb.setChecked(True)
    dlg._save_current()
    assert db.get_difficulty_level(1).label == "Très facile"
    assert db.get_difficulty_level(1).hide_label is True


def test_difficulty_dialog_load_and_clear_image(qtbot, db, tmp_path, monkeypatch):
    img = tmp_path / "icon.png"
    img.write_bytes(_PNG_1PX)
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(2)

    monkeypatch.setattr(dd.QFileDialog, "exec", lambda self: 1)
    monkeypatch.setattr(dd.QFileDialog, "selectedFiles", lambda self: [str(img)])
    dlg._load_image()
    assert db.get_difficulty_level(2).data == _PNG_1PX
    assert db.get_difficulty_level(2).mime_type == "image/png"

    dlg._clear_image()
    assert db.get_difficulty_level(2).data is None


def test_difficulty_dialog_load_image_cancelled(qtbot, db, monkeypatch):
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(1)
    monkeypatch.setattr(dd.QFileDialog, "exec", lambda self: 0)
    dlg._load_image()
    assert db.get_difficulty_level(1).data is None


def test_difficulty_dialog_close_saves(qtbot, db):
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(3)
    dlg._label_edit.setText("Expert")
    dlg._on_close()
    assert db.get_difficulty_level(3).label == "Expert"


def test_difficulty_dialog_thumbnail(qtbot, db):
    dl = db.get_difficulty_level(1)
    dl.data = _PNG_1PX
    db.save_difficulty_level(dl)
    dlg = DifficultyDialog(db)
    qtbot.addWidget(dlg)
    assert not dlg._list.item(1).icon().isNull()
