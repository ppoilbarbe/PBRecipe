"""Regression tests for spellcheck_dialog utilities."""

from __future__ import annotations

import pytest

from pbrecipe.ui.spellcheck_dialog import _html_to_plain, _patch_pygrammalecte

# ---------------------------------------------------------------------------
# _html_to_plain — conversion HTML → texte brut
# ---------------------------------------------------------------------------


def test_nbsp_raw_char_preserved():
    """Un \xa0 brut dans le HTML doit survivre à la conversion."""
    html = "<p>Note\xa0: texte</p>"
    result = _html_to_plain(html)
    assert "\xa0" in result, "L'espace insécable brut doit être préservé"


def test_nbsp_entity_converted():
    """&nbsp; dans le HTML Qt doit devenir \\xa0, pas un espace ordinaire."""
    html = "<p>Note&nbsp;: texte</p>"
    result = _html_to_plain(html)
    assert "\xa0" in result, "&nbsp; doit être converti en \\xa0"
    assert "Note\xa0: texte" in result


def test_nbsp_decimal_entity_converted():
    """&#160; doit également être converti en \\xa0."""
    html = "<p>Note&#160;: texte</p>"
    result = _html_to_plain(html)
    assert "\xa0" in result


def test_regular_space_unchanged():
    html = "<p>bonjour monde</p>"
    result = _html_to_plain(html)
    assert " " in result
    assert "\xa0" not in result


def test_html_tags_stripped():
    html = "<p>Bonjour <b>le</b> monde.</p>"
    assert _html_to_plain(html) == "Bonjour le monde."


def test_block_tags_become_newlines():
    html = "<p>Premier</p><p>Second</p>"
    result = _html_to_plain(html)
    assert "Premier" in result
    assert "Second" in result
    assert "\n" in result


def test_br_becomes_newline():
    html = "<p>Ligne A<br>Ligne B</p>"
    result = _html_to_plain(html)
    assert "Ligne A" in result
    assert "Ligne B" in result
    assert "\n" in result


def test_style_block_stripped():
    html = "<style>p { color: red; }</style><p>Texte</p>"
    result = _html_to_plain(html)
    assert "color" not in result
    assert "Texte" in result


def test_html_entities_decoded():
    html = "<p>caf&eacute; &amp; th&eacute;</p>"
    result = _html_to_plain(html)
    assert "café" in result
    assert "&" in result


def test_empty_input():
    assert _html_to_plain("") == ""


def test_plain_text_passthrough():
    """Texte sans balises : inchangé (modulo strip)."""
    text = "Pas de HTML ici."
    assert _html_to_plain(text) == text


# ---------------------------------------------------------------------------
# _patch_pygrammalecte — robustesse du JSON avec paragraphes vides
# ---------------------------------------------------------------------------

_ITEM = '{"iParagraph":1,"lGrammarErrors":[],"lSpellingErrors":[]}'


def _make_raw(warnings_list: list[str]) -> str:
    """Reconstruit le JSON tel que _run_grammalecte le produit."""
    return '{"data": [\n' + ",\n".join(warnings_list) + "\n]}"


@pytest.fixture(autouse=True)
def apply_patch():
    """Applique le patch une fois par test (idempotent)."""
    _patch_pygrammalecte()


def _convert(json_str: str) -> list:
    import pygrammalecte.pygrammalecte as pg

    return list(pg._convert_to_messages(json_str))


def test_no_empty_paragraphs():
    """Cas nominal sans paragraphe vide."""
    assert _convert(_make_raw([_ITEM])) == []


def test_one_empty_before():
    """1 paragraphe vide avant l'item → JSON invalide sans le patch."""
    assert _convert(_make_raw(["", _ITEM])) == []


def test_one_empty_after():
    """1 paragraphe vide après l'item."""
    assert _convert(_make_raw([_ITEM, ""])) == []


def test_two_empties_before():
    assert _convert(_make_raw(["", "", _ITEM])) == []


def test_three_empties_before():
    """3 paragraphes vides : nécessite 2 passes de regex."""
    assert _convert(_make_raw(["", "", "", _ITEM])) == []


def test_four_empties_before():
    """4 paragraphes vides : nécessite 3 passes de regex."""
    assert _convert(_make_raw(["", "", "", "", _ITEM])) == []


def test_empties_both_sides():
    assert _convert(_make_raw(["", "", _ITEM, "", ""])) == []


def test_all_empty_paragraphs():
    """Aucun item : tableau vide valide."""
    assert _convert(_make_raw(["", ""])) == []
    assert _convert(_make_raw(["", "", ""])) == []


def test_multiple_items_with_empties():
    """Deux items séparés par des paragraphes vides."""
    item2 = '{"iParagraph":2,"lGrammarErrors":[],"lSpellingErrors":[]}'
    assert _convert(_make_raw(["", _ITEM, "", "", item2, ""])) == []


# ---------------------------------------------------------------------------
# Suggestions orthographiques dans GrammalecteSpellingMessage
# ---------------------------------------------------------------------------

_ITEM_WITH_SUGG = (
    '{"iParagraph":1,"lGrammarErrors":[],"lSpellingErrors":['
    '{"i":0,"sType":"WORD","sValue":"canelle","nStart":0,"nEnd":7,'
    '"aSuggestions":["cannelle","camelle"]}'
    "]}"
)


def test_spelling_suggestions_attached():
    """Les suggestions aSuggestions doivent être accessibles via .suggestions."""
    from pygrammalecte import GrammalecteSpellingMessage

    messages = _convert(_make_raw([_ITEM_WITH_SUGG]))
    assert len(messages) == 1
    msg = messages[0]
    assert isinstance(msg, GrammalecteSpellingMessage)
    assert hasattr(msg, "suggestions")
    assert "cannelle" in msg.suggestions


def test_spelling_suggestions_order():
    """La première suggestion doit être la meilleure (cannelle avant camelle)."""
    messages = _convert(_make_raw([_ITEM_WITH_SUGG]))
    assert messages[0].suggestions[0] == "cannelle"


def test_spelling_no_suggestions_when_absent():
    """Si aSuggestions est absent du dict, suggestions est une liste vide."""
    _item_no_sugg = (
        '{"iParagraph":1,"lGrammarErrors":[],"lSpellingErrors":['
        '{"i":0,"sType":"WORD","sValue":"xyz","nStart":0,"nEnd":3}'
        "]}"
    )
    messages = _convert(_make_raw([_item_no_sugg]))
    assert messages[0].suggestions == []
