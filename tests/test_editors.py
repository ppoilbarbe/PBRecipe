"""Tests des éditeurs : RecipeEditor, MediaTab, IngredientListEditor."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox

from pbrecipe.config import RecipeConfig
from pbrecipe.database.database import Database
from pbrecipe.models import (
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeMedia,
    Source,
    Unit,
)
from pbrecipe.ui import media_tab as mt_mod
from pbrecipe.ui.ingredient_list_editor import IngredientListEditor, IngredientRow
from pbrecipe.ui.media_tab import (
    MediaTab,
    _code_from_filename,
    _mime_from_path,
)
from pbrecipe.ui.recipe_editor import RecipeEditor, _slugify

_PNG = bytes.fromhex(
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


# ===========================================================================
# _slugify / _code_from_filename / _mime_from_path
# ===========================================================================


def test_slugify():
    assert _slugify("Gâteau au Chocolat") == "GATEAU_AU_CHOCOLAT"
    assert _slugify("Crème brûlée !") == "CREME_BRULEE"


def test_code_from_filename():
    assert _code_from_filename("photo_finale.jpg") == "PHOTO_FINALE"
    assert _code_from_filename("@@@.png") == "IMG"
    long = _code_from_filename("un_nom_de_fichier_vraiment_tres_long.jpg")
    assert len(long) <= 20


def test_media_mime_from_path():
    assert _mime_from_path("x.png") == "image/png"
    assert _mime_from_path("x.zzz") == "image/jpeg"


# ===========================================================================
# IngredientRow / IngredientListEditor
# ===========================================================================


def test_ingredient_row_get_data(qtbot, db):
    unit = db.save_unit(Unit(name="g"))
    ing = db.save_ingredient(Ingredient(name="Farine"))
    row = IngredientRow(
        RecipeIngredient(
            prefix="env.",
            quantity="200",
            unit_id=unit.id,
            ingredient_id=ing.id,
            suffix="tamisée",
        ),
        db.list_units(),
        db.list_ingredients(),
    )
    qtbot.addWidget(row)
    data = row.get_data("REC", 3)
    assert data.recipe_code == "REC"
    assert data.position == 3
    assert data.prefix == "env."
    assert data.unit_id == unit.id
    assert data.ingredient_id == ing.id


def test_ingredient_list_editor_load_and_get(qtbot, db):
    db.save_unit(Unit(name="g"))
    ing = db.save_ingredient(Ingredient(name="Sucre"))
    editor = IngredientListEditor()
    qtbot.addWidget(editor)
    editor.load([RecipeIngredient(quantity="100", ingredient_id=ing.id)], db)
    result = editor.get_ingredients("R")
    assert len(result) == 1
    assert result[0].quantity == "100"


def test_ingredient_list_editor_insert_remove(qtbot, db):
    editor = IngredientListEditor()
    qtbot.addWidget(editor)
    editor.load([], db)
    assert not editor._empty_btn.isHidden()
    editor._insert_at(0)
    assert len(editor._rows) == 1
    assert editor._empty_btn.isHidden()
    editor._remove_row(editor._rows[0])
    assert editor._rows == []


def test_ingredient_list_editor_move(qtbot, db):
    db.save_ingredient(Ingredient(name="A"))
    editor = IngredientListEditor()
    qtbot.addWidget(editor)
    editor.load(
        [
            RecipeIngredient(quantity="1"),
            RecipeIngredient(quantity="2"),
            RecipeIngredient(quantity="3"),
        ],
        db,
    )
    first = editor._rows[0]
    editor._move_row_to(first, 2)
    quantities = [r.get_data("R", i).quantity for i, r in enumerate(editor._rows)]
    assert quantities == ["2", "3", "1"]
    editor._move_row_to(editor._rows[0], 0)  # no-op


def test_ingredient_list_editor_clear_reload(qtbot, db):
    db.save_unit(Unit(name="g"))
    editor = IngredientListEditor()
    qtbot.addWidget(editor)
    editor.load([RecipeIngredient(quantity="1")], db)
    editor.clear()
    assert editor._rows == []
    editor.load([RecipeIngredient(quantity="1")], db)
    db.save_unit(Unit(name="kg"))
    editor.reload(db)
    assert editor._rows[0]._unit.count() == 3  # vide + g + kg


def test_ingredient_list_editor_drag(qtbot, db):
    editor = IngredientListEditor()
    qtbot.addWidget(editor)
    editor.load([RecipeIngredient(quantity="1"), RecipeIngredient(quantity="2")], db)
    row = editor._rows[0]
    editor._on_drag_start(row)
    assert editor._drag_row is row
    editor._on_drag_move(row, QPoint(0, 100000))
    editor._on_drag_end(row, QPoint(0, 100000))
    assert editor._drag_row is None


# ===========================================================================
# MediaTab
# ===========================================================================


def test_media_tab_load_and_get(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="IMG1", data=_PNG)])
    assert tab._list.count() == 1
    media = tab.get_media("REC")
    assert media[0].recipe_code == "REC"
    assert media[0].position == 0


def test_media_tab_row_changed_preview(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="A", data=_PNG), RecipeMedia(code="B", data=b"")])
    tab._list.setCurrentRow(0)
    assert tab._current_pixmap is not None
    tab._list.setCurrentRow(1)  # pas de data → pas d'aperçu
    assert tab._current_pixmap is None


def test_media_tab_unique_code(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="PHOTO", data=_PNG)])
    assert tab._unique_code("AUTRE") == "AUTRE"
    assert tab._unique_code("PHOTO") == "PHOTO_2"


def test_media_tab_add(qtbot, tmp_path, monkeypatch):
    img = tmp_path / "ma_photo.png"
    img.write_bytes(_PNG)
    tab = MediaTab()
    qtbot.addWidget(tab)
    monkeypatch.setattr(mt_mod._MediaFileDialog, "exec", lambda self: 1)
    monkeypatch.setattr(
        mt_mod._MediaFileDialog, "selectedFiles", lambda self: [str(img)]
    )
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("MAPHOTO", True))
    tab._add()
    assert tab._media[0].code == "MAPHOTO"
    assert tab._media[0].data == _PNG


def test_media_tab_add_duplicate_code(qtbot, tmp_path, monkeypatch):
    img = tmp_path / "p.png"
    img.write_bytes(_PNG)
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="DUP", data=_PNG)])
    monkeypatch.setattr(mt_mod._MediaFileDialog, "exec", lambda self: 1)
    monkeypatch.setattr(
        mt_mod._MediaFileDialog, "selectedFiles", lambda self: [str(img)]
    )
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("DUP", True))
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", True)
    )
    tab._add()
    assert warned.get("w") is True
    assert len(tab._media) == 1


def test_media_tab_add_cancelled(qtbot, monkeypatch):
    tab = MediaTab()
    qtbot.addWidget(tab)
    monkeypatch.setattr(mt_mod._MediaFileDialog, "exec", lambda self: 0)
    tab._add()
    assert tab._media == []


def test_media_tab_remove(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="A", data=_PNG)])
    tab._list.setCurrentRow(0)
    tab._remove()
    assert tab._media == []


def test_media_tab_move(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load(
        [
            RecipeMedia(code="A", data=_PNG),
            RecipeMedia(code="B", data=_PNG),
        ]
    )
    tab._list.setCurrentRow(0)
    tab._move_down()
    assert [m.code for m in tab._media] == ["B", "A"]
    tab._list.setCurrentRow(1)
    tab._move_up()
    assert [m.code for m in tab._media] == ["A", "B"]


def test_media_tab_export(qtbot, tmp_path, monkeypatch):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab.load([RecipeMedia(code="A", mime_type="image/png", data=_PNG)])
    tab._list.setCurrentRow(0)
    out = tmp_path / "exported"
    monkeypatch.setattr(
        mt_mod.QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), "")
    )
    tab._export()
    assert (tmp_path / "exported.png").read_bytes() == _PNG


def test_media_tab_export_no_selection(qtbot):
    tab = MediaTab()
    qtbot.addWidget(tab)
    tab._export()  # rien sélectionné → no-op


# ===========================================================================
# RecipeEditor
# ===========================================================================


def _seed(db):
    cat = db.save_category(Category(name="Dessert"))
    src = db.save_source(Source(name="Livre"))
    ing = db.save_ingredient(Ingredient(name="Farine"))
    db.save_unit(Unit(name="g"))
    return cat, src, ing


def test_recipe_editor_load_and_save(qtbot, db):
    cat, src, ing = _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    recipe = Recipe(
        code="GATEAU",
        name="Gâteau",
        difficulty=2,
        prep_time=30,
        categories=[cat.id],
        source_id=src.id,
        ingredients=[RecipeIngredient(quantity="100", ingredient_id=ing.id)],
    )
    editor.load(recipe, db, RecipeConfig())
    assert editor.has_unsaved_changes() is False
    assert editor._name_edit.text() == "Gâteau"

    saved = []
    editor.saved.connect(saved.append)
    editor._name_edit.setText("Gâteau modifié")
    assert editor.has_unsaved_changes() is True
    editor._save()
    assert saved
    assert saved[0].name == "Gâteau modifié"
    assert editor.has_unsaved_changes() is False


def test_recipe_editor_save_without_category(qtbot, db, monkeypatch):
    _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    recipe = Recipe(code="R", name="R")
    editor.load(recipe, db, None)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", True)
    )
    editor._save()
    assert warned.get("w") is True


def test_recipe_editor_auto_code_from_name(qtbot, db):
    _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    editor.load(Recipe(code="", name=""), db, None)
    editor._name_edit.setText("Tarte aux Pommes")
    assert editor._code_edit.text() == "TARTE_AUX_POMMES"


def test_recipe_editor_clear(qtbot, db):
    cat, _, _ = _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    editor.load(Recipe(code="R", name="R", categories=[cat.id]), db, None)
    editor.clear()
    assert editor._name_edit.text() == ""
    assert editor._category_list.count() == 0


def test_recipe_editor_check_spelling(qtbot, db, monkeypatch):
    _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    editor.load(Recipe(code="R", name="R"), db, None)
    captured = {}
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.run_spellcheck",
        lambda items, parent: captured.setdefault("items", items),
    )
    editor._check_spelling()
    assert captured["items"][0][0] == "Réalisation"


def test_recipe_editor_reload_references(qtbot, db):
    cat, _, _ = _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    editor.load(Recipe(code="R", name="R", categories=[cat.id]), db, None)
    db.save_category(Category(name="Entrée"))
    editor.reload_references()
    assert editor._category_list.count() == 2


def test_recipe_editor_save_action_property(qtbot):
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    assert editor.save_action is editor._act_save


def test_recipe_editor_save_with_times(qtbot, db):
    cat, _, _ = _seed(db)
    editor = RecipeEditor()
    qtbot.addWidget(editor)
    recipe = Recipe(code="R", name="R", categories=[cat.id])
    editor.load(recipe, db, None)
    editor._category_list.item(0).setCheckState(Qt.CheckState.Checked)
    editor._prep_spin.setValue(15)
    editor._cook_spin.setValue(20)
    editor._save()
    assert recipe.prep_time == 15
    assert recipe.cook_time == 20
    assert recipe.wait_time is None
