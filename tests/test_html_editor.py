from __future__ import annotations

import pytest

from pbrecipe.ui.html_editor import HtmlEditor, _clean_html, _pretty_html

# ---------------------------------------------------------------------------
# Tests de _clean_html (fonction pure, pas de Qt)
# ---------------------------------------------------------------------------


def test_clean_html_empty_input():
    assert _clean_html("") == ""


def test_clean_html_extracts_body():
    raw = "<html><head><style>…</style></head><body><p>Bonjour</p></body></html>"
    assert _clean_html(raw) == "<p>Bonjour</p>"


def test_clean_html_strips_style_attributes():
    raw = '<p style="margin:0; font-size:12pt;">Texte</p>'
    assert _clean_html(raw) == "<p>Texte</p>"


def test_clean_html_strips_qt_paragraph_type_empty():
    # Le marqueur interne Qt doit disparaître du HTML stocké.
    raw = '<p style="-qt-paragraph-type:empty; margin-top:0px;"><br /></p>'
    assert _clean_html(raw) == "<p><br /></p>"


def test_clean_html_preserves_br_in_empty_paragraph():
    # Un paragraphe vide doit être stocké avec <br /> pour être rechargé.
    raw = "<p><br /></p>"
    assert _clean_html(raw) == "<p><br /></p>"


def test_clean_html_removes_inter_block_whitespace():
    raw = "<p>A</p>\n<p>B</p>"
    assert _clean_html(raw) == "<p>A</p><p>B</p>"


def test_clean_html_multiple_empty_paragraphs():
    raw = "<p>A</p>\n<p><br /></p>\n<p><br /></p>\n<p>B</p>"
    assert _clean_html(raw) == "<p>A</p><p><br /></p><p><br /></p><p>B</p>"


def test_clean_html_span_bold_to_b():
    raw = '<p><span style="font-weight:bold;">Gras</span></p>'
    assert _clean_html(raw) == "<p><b>Gras</b></p>"


def test_clean_html_span_italic_to_i():
    raw = '<p><span style="font-style:italic;">Italique</span></p>'
    assert _clean_html(raw) == "<p><i>Italique</i></p>"


def test_clean_html_span_underline_to_u():
    raw = '<p><span style="text-decoration:underline;">Souligné</span></p>'
    assert _clean_html(raw) == "<p><u>Souligné</u></p>"


def test_clean_html_bare_span_unwrapped():
    raw = "<p><span>Texte</span></p>"
    assert _clean_html(raw) == "<p>Texte</p>"


def test_clean_html_heading_removes_inner_bold():
    raw = "<h2><b>Titre</b></h2>"
    assert _clean_html(raw) == "<h2>Titre</h2>"


# ---------------------------------------------------------------------------
# Tests de _pretty_html (fonction pure, pas de Qt)
# ---------------------------------------------------------------------------


def test_pretty_html_empty_returns_empty():
    assert _pretty_html("") == ""


def test_pretty_html_block_elements_on_separate_lines():
    html = "<h2>Titre</h2><p>Texte.</p>"
    result = _pretty_html(html)
    lines = result.splitlines()
    assert lines[0] == "<h2>Titre</h2>"
    assert lines[1] == "<p>Texte.</p>"


def test_pretty_html_list_items_indented():
    html = "<ul><li>A</li><li>B</li></ul>"
    result = _pretty_html(html)
    assert "<ul>" in result
    assert "  <li>A</li>" in result
    assert "  <li>B</li>" in result
    assert "</ul>" in result


def test_pretty_html_inline_elements_preserved():
    """Les balises inline (<b>, <i>) dans un bloc ne doivent pas disparaître."""
    html = "<p>Texte <b>gras</b> et <i>italique</i>.</p>"
    result = _pretty_html(html)
    assert "<b>gras</b>" in result
    assert "<i>italique</i>" in result


def test_pretty_html_no_xml_declaration():
    """La déclaration <?xml …?> ne doit pas apparaître dans le résultat."""
    result = _pretty_html("<p>Test</p>")
    assert "<?xml" not in result


def test_pretty_html_no_root_wrapper():
    """La balise <root> d'enrobage ne doit pas apparaître dans le résultat."""
    result = _pretty_html("<p>Test</p>")
    assert "<root>" not in result
    assert "</root>" not in result


def test_pretty_html_invalid_html_returns_raw():
    """HTML invalide pour minidom : retourne le HTML brut sans lever d'exception."""
    invalid = "<p>Non fermé & entité brute"
    result = _pretty_html(invalid)
    assert result == invalid


def test_pretty_html_roundtrip_block_only(editor):
    """Le HTML mis en forme par _pretty_html peut être rechargé sans perte
    pour du contenu sans éléments inline mixés à du texte brut."""
    original = "<h2>Titre</h2><p>Texte simple.</p><ul><li>A</li><li>B</li></ul>"
    editor.set_html(original)
    clean = editor.get_html()

    pretty = _pretty_html(clean)
    editor.set_html(pretty)
    after = editor.get_html()

    assert after == clean


def test_pretty_html_inline_elements_alter_whitespace(editor):
    """Limitation connue de minidom : les espaces autour des balises inline
    peuvent être modifiés après pretty-print + rechargement.
    Le contenu textuel doit rester présent même si la mise en forme change."""
    original = "<p>Texte <b>gras</b> et <i>italique</i>.</p>"
    editor.set_html(original)
    clean = editor.get_html()

    pretty = _pretty_html(clean)
    editor.set_html(pretty)
    after = editor.get_html()

    # Le texte brut est conservé, même si la ponctuation est réencadrée d'espaces.
    import re as _re

    text = _re.sub(r"<[^>]+>", "", after)
    assert "gras" in text
    assert "italique" in text


# ---------------------------------------------------------------------------
# Tests de HtmlEditor (intégration Qt)
# ---------------------------------------------------------------------------


@pytest.fixture
def editor(qtbot):
    e = HtmlEditor()
    qtbot.addWidget(e)
    return e


def test_set_html_empty_paragraph_single_block(editor):
    """Régression : <p><br /></p> doit créer un bloc vide, pas un bloc U+2028.

    Sans le fix, setHtml("<p><br /></p>") crée un bloc avec text=' '
    (LINE SEPARATOR) qui se rend visuellement comme deux lignes vides.
    """
    editor.set_html("<p>Ligne 1</p><p><br /></p><p>Ligne 2</p>")
    doc = editor._edit.document()

    assert doc.blockCount() == 3
    empty_block = doc.findBlockByNumber(1)
    assert empty_block.text() == "", (
        f"Le bloc vide contient {repr(empty_block.text())} au lieu de '' — "
        "probable régression du doublement des sauts de paragraphe"
    )
    assert empty_block.length() == 1


def test_set_html_multiple_empty_paragraphs_single_blocks(editor):
    """Deux paragraphes vides consécutifs → deux blocs vides (pas quatre)."""
    editor.set_html("<p>A</p><p><br /></p><p><br /></p><p>B</p>")
    doc = editor._edit.document()

    assert doc.blockCount() == 4
    for i in (1, 2):
        block = doc.findBlockByNumber(i)
        assert block.text() == "", (
            f"Bloc {i} contient {repr(block.text())} — doublement non corrigé"
        )


def test_empty_paragraph_matches_typed_block_structure(editor, qtbot):
    """Un paragraphe vide rechargé doit avoir la même structure interne
    qu'un paragraphe créé par frappe clavier (insertBlock).
    """
    editor.set_html("<p>Ligne 1</p><p><br /></p><p>Ligne 2</p>")

    editor_typed = HtmlEditor()
    qtbot.addWidget(editor_typed)
    cursor = editor_typed._edit.textCursor()
    cursor.insertText("Ligne 1")
    cursor.insertBlock()
    cursor.insertBlock()
    cursor.insertText("Ligne 2")
    editor_typed._edit.setTextCursor(cursor)

    doc_loaded = editor._edit.document()
    doc_typed = editor_typed._edit.document()

    assert doc_loaded.blockCount() == doc_typed.blockCount()
    for i in range(doc_loaded.blockCount()):
        bl = doc_loaded.findBlockByNumber(i)
        bt = doc_typed.findBlockByNumber(i)
        assert bl.text() == bt.text(), (
            f"Bloc {i} : rechargé={repr(bl.text())} vs tapé={repr(bt.text())}"
        )


def test_get_html_idempotent_empty_paragraph(editor):
    """set_html → get_html doit être idempotent : le HTML stocké ne doit pas
    changer d'un cycle à l'autre (régression du doublement physique).
    """
    html = "<p>Ligne 1</p><p><br /></p><p>Ligne 2</p>"
    editor.set_html(html)
    first = editor.get_html()

    editor.set_html(first)
    second = editor.get_html()

    assert first == html, f"Round 1 modifie le HTML : {repr(first)}"
    assert second == html, f"Round 2 modifie le HTML : {repr(second)}"


def test_get_html_idempotent_multiple_empty_paragraphs(editor):
    """Plusieurs paragraphes vides : le HTML doit rester stable."""
    html = "<p>A</p><p><br /></p><p><br /></p><p>B</p>"
    editor.set_html(html)
    first = editor.get_html()

    editor.set_html(first)
    second = editor.get_html()

    assert first == html
    assert second == html


def test_get_html_idempotent_rich_content(editor):
    """Contenu riche (titres, gras, listes) : idempotence du roundtrip."""
    html = (
        "<h2>Titre</h2><p>Texte <b>gras</b> et <i>italique</i>.</p>"
        "<p><br /></p><p>Fin.</p>"
    )
    editor.set_html(html)
    first = editor.get_html()

    editor.set_html(first)
    second = editor.get_html()

    assert first == second


def test_get_html_empty_editor_returns_empty_string(editor):
    editor.set_html("")
    assert editor.get_html() == ""


def test_get_html_whitespace_only_returns_empty_string(editor):
    editor.set_html("<p><br /></p>")
    assert editor.get_html() == ""
