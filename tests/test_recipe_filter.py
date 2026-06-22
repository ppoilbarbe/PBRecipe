"""Regression tests for the recipe list filter (diacritics-insensitive)."""

from __future__ import annotations

from pbrecipe.ui.main_window import MainWindow

norm = MainWindow._normalize_filter


# ---------------------------------------------------------------------------
# Normalisation de base
# ---------------------------------------------------------------------------


def test_lowercase():
    assert norm("ABC") == "abc"


def test_accented_e_variants():
    """é, è, ê, ë et E/É doivent tous produire 'e'."""
    for c in "éèêëÉÈÊË":
        assert norm(c) == "e", f"'{c}' devrait se normaliser en 'e'"


def test_accented_a_variants():
    for c in "àâäÀÂÄ":
        assert norm(c) == "a", f"'{c}' devrait se normaliser en 'a'"


def test_accented_u_variants():
    for c in "ùûüÙÛÜ":
        assert norm(c) == "u", f"'{c}' devrait se normaliser en 'u'"


def test_accented_i_variants():
    for c in "îïÎÏ":
        assert norm(c) == "i", f"'{c}' devrait se normaliser en 'i'"


def test_accented_o_variants():
    for c in "ôöÔÖ":
        assert norm(c) == "o", f"'{c}' devrait se normaliser en 'o'"


def test_cedilla():
    assert norm("ç") == "c"
    assert norm("Ç") == "c"


def test_plain_ascii_unchanged():
    assert norm("bonjour") == "bonjour"
    assert norm("recette") == "recette"


# ---------------------------------------------------------------------------
# Cas représentatifs du filtre de la liste
# ---------------------------------------------------------------------------


def test_filter_match_accent_vs_plain():
    """Chercher 'gateau' doit correspondre à 'Gâteau'."""
    assert norm("gateau") in norm("Gâteau au chocolat")


def test_filter_match_accent_vs_accent():
    """Chercher 'gâteau' doit correspondre à 'Gateau'."""
    assert norm("gâteau") in norm("Gateau au chocolat")


def test_filter_match_case_insensitive():
    assert norm("CHOCOLAT") in norm("gâteau au chocolat")


def test_filter_no_match():
    assert norm("tarte") not in norm("Gâteau au chocolat")


def test_filter_empty_needle_matches_all():
    """Filtre vide → needle vide, doit correspondre à tout."""
    needle = norm("")
    assert not needle  # chaîne vide = falsy → toutes les recettes visibles


def test_filter_real_recipe_names():
    """Noms de recettes typiques."""
    cases = [
        ("confiture", "Confiture de fraises"),
        ("creme", "Crème brûlée"),
        ("brûlée", "Crème brulée"),
        ("mousse", "Mousse au chocolat"),
        ("clafoutis", "Clafoutis aux cerises"),
    ]
    for needle, name in cases:
        assert norm(needle) in norm(name), f"'{needle}' devrait trouver '{name}'"
