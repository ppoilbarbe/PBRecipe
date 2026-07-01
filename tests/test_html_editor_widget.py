"""Tests du widget HtmlEditor et de ses dialogues internes."""

from __future__ import annotations

from pbrecipe.ui import html_editor as he
from pbrecipe.ui.html_editor import (
    HtmlEditor,
    _HtmlSourceDialog,
    _ImgPickerDialog,
    _LinkDialog,
    _pretty_html,
    _RefPickerDialog,
)

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd49a73"
    "000000097048597300000f6100000f6101a83fa7690000001649444154089963fc"
    "cfc0c0c0c0c0c4c0c0c0c0c000000d1d01030cc7e7890000000049454e44ae426082"
)


# --- _pretty_html ---


def test_pretty_html_indents():
    out = _pretty_html("<p>Bonjour</p>")
    assert "Bonjour" in out


def test_pretty_html_invalid_fallback():
    raw = "<p>non fermé"
    assert _pretty_html(raw) == raw


# --- _HtmlSourceDialog ---


def test_html_source_dialog(qtbot):
    dlg = _HtmlSourceDialog("<p>x</p>")
    qtbot.addWidget(dlg)
    dlg._editor.setPlainText("<p>modifié</p>")
    dlg._accept()
    assert dlg.html == "<p>modifié</p>"


# --- _LinkDialog ---


def test_link_dialog_accept(qtbot):
    dlg = _LinkDialog("texte")
    qtbot.addWidget(dlg)
    dlg._url_edit.setText("https://example.com")
    dlg._accept()
    assert dlg.url == "https://example.com"
    assert dlg.text == "texte"


def test_link_dialog_empty_url_blocks(qtbot):
    dlg = _LinkDialog()
    qtbot.addWidget(dlg)
    dlg._accept()  # URL vide → ne ferme pas
    assert dlg.url == ""


def test_link_dialog_text_defaults_to_url(qtbot):
    dlg = _LinkDialog("")
    qtbot.addWidget(dlg)
    dlg._url_edit.setText("https://x.test")
    dlg._accept()
    assert dlg.text == "https://x.test"


# --- _RefPickerDialog ---


def test_ref_picker_filter_and_select(qtbot):
    dlg = _RefPickerDialog("T", [("R1", "Recette 1"), ("R2", "Autre")])
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 2
    dlg._apply_filter("autre")
    assert dlg._list.count() == 1
    dlg._populate(dlg._all_items)
    dlg._list.setCurrentRow(0)
    dlg._accept_selection()
    assert dlg.selected_code == "R1"


def test_ref_picker_double_click(qtbot):
    dlg = _RefPickerDialog("T", [("R1", "Recette 1")])
    qtbot.addWidget(dlg)
    dlg._accept_item(dlg._list.item(0))
    assert dlg.selected_code == "R1"


# --- _ImgPickerDialog ---


def test_img_picker_select(qtbot):
    items = [("REC", "IMG1"), ("AUTRE", "IMG2")]
    dlg = _ImgPickerDialog(items, current_recipe="REC", show_filter=False)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 2
    dlg._list.setCurrentRow(0)
    dlg._accept_selection()
    assert dlg.selected_recipe_code == "REC"
    assert dlg.selected_img_code == "IMG1"


def test_img_picker_current_recipe_filter(qtbot):
    items = [("REC", "IMG1"), ("AUTRE", "IMG2")]
    dlg = _ImgPickerDialog(items, current_recipe="REC", show_filter=True)
    qtbot.addWidget(dlg)
    assert dlg._list.count() == 1  # filtré sur recette courante
    dlg._filter_cb.setChecked(False)
    assert dlg._list.count() == 2
    dlg._filter.setText("autre")
    assert dlg._list.count() == 1


def test_img_picker_double_click(qtbot):
    items = [("REC", "IMG1")]
    dlg = _ImgPickerDialog(items)
    qtbot.addWidget(dlg)
    dlg._accept_item(dlg._list.item(0))
    assert dlg.selected_img_code == "IMG1"


def test_img_picker_fetch_data(qtbot):
    items = [("REC", "IMG1")]
    fetched: list[tuple[str, str]] = []

    def _fetch(rc: str, code: str) -> bytes:
        fetched.append((rc, code))
        return _PNG

    dlg = _ImgPickerDialog(items, fetch_data=_fetch)
    qtbot.addWidget(dlg)
    dlg._list.setCurrentRow(0)
    assert fetched == [("REC", "IMG1")]


# --- HtmlEditor ---


def test_html_editor_set_get(qtbot):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_html("<p>Bonjour <b>monde</b></p>")
    assert "monde" in ed.get_html()
    assert ed.get_plain_text().strip() == "Bonjour monde"


def test_html_editor_empty(qtbot):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_html("")
    assert ed.get_html() == ""


def test_html_editor_clear(qtbot):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_html("<p>x</p>")
    ed.clear()
    assert ed.get_html() == ""


def test_html_editor_references_setters(qtbot):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_current_recipe("REC")
    ed.set_references([("R", "Recette")], [("R", "I")], [("T", "Tech")])
    ed.set_images([("R2", "I2")])
    assert ed._current_recipe_code == "REC"
    assert ed._images == [("R2", "I2")]


def test_html_editor_formatting(qtbot):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_html("<p>texte</p>")
    cursor = ed._edit.textCursor()
    cursor.select(cursor.SelectionType.Document)
    ed._edit.setTextCursor(cursor)
    ed._bold()
    ed._italic()
    ed._underline()
    ed._heading(2)
    ed._heading(2)  # bascule en niveau 0
    ed._bullet_list()
    ed._numbered_list()


def test_html_editor_insert_markers(qtbot, monkeypatch):
    ed = HtmlEditor(current_recipe_mode=True)
    qtbot.addWidget(ed)
    ed.set_references([("REC", "Recette")], [("REC", "IMG1")], [("TECH", "Technique")])
    ed.set_current_recipe("REC")

    monkeypatch.setattr(he._RefPickerDialog, "exec", lambda self: 1)
    monkeypatch.setattr(
        he._RefPickerDialog, "selected_code", property(lambda self: "REC")
    )
    ed._insert_recipe_marker()
    ed._insert_tech_marker()
    assert "[RECIPE:REC]" in ed.get_plain_text()
    assert "[TECH:REC]" in ed.get_plain_text()


def test_html_editor_insert_img_marker(qtbot, monkeypatch):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_references([], [("REC", "IMG1")], [])
    monkeypatch.setattr(he._ImgPickerDialog, "exec", lambda self: 1)
    monkeypatch.setattr(
        he._ImgPickerDialog,
        "selected_recipe_code",
        property(lambda self: "REC"),
    )
    monkeypatch.setattr(
        he._ImgPickerDialog,
        "selected_img_code",
        property(lambda self: "IMG1"),
    )
    ed._insert_img_marker()
    assert "[IMG:REC:IMG1]" in ed.get_plain_text()


def test_html_editor_insert_link(qtbot, monkeypatch):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    monkeypatch.setattr(he._LinkDialog, "exec", lambda self: 1)
    monkeypatch.setattr(he._LinkDialog, "url", property(lambda self: "https://x.test"))
    monkeypatch.setattr(he._LinkDialog, "text", property(lambda self: "lien"))
    ed._insert_link()
    assert "x.test" in ed.get_html()


def test_html_editor_edit_html_source(qtbot, monkeypatch):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_html("<p>avant</p>")
    monkeypatch.setattr(he._HtmlSourceDialog, "exec", lambda self: 1)
    monkeypatch.setattr(
        he._HtmlSourceDialog, "html", property(lambda self: "<p>après</p>")
    )
    ed._edit_html_source()
    assert "après" in ed.get_html()


def test_html_editor_pick_ref_cancelled(qtbot, monkeypatch):
    ed = HtmlEditor()
    qtbot.addWidget(ed)
    ed.set_references([("R", "Recette")], [], [])
    monkeypatch.setattr(he._RefPickerDialog, "exec", lambda self: 0)
    ed._insert_recipe_marker()  # annulé → rien inséré
    assert ed.get_plain_text().strip() == ""
