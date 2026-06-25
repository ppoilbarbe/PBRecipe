"""Tests du dialogue de vérification orthographique (mocks des moteurs)."""

from __future__ import annotations

import sys
import types

import pytest
from PySide6.QtWidgets import QMessageBox

from pbrecipe.ui import spellcheck_dialog as sc
from pbrecipe.ui.spellcheck_dialog import (
    SpellCheckDialog,
    _build_context,
    _format_match,
    _no_checker_warning,
    language_tool_info,
)

# --- helpers purs ---


def test_build_context_truncation():
    text = "a" * 100 + "ERREUR" + "b" * 100
    ctx = _build_context(text, 100, len("ERREUR"))
    assert ctx.startswith("…")
    assert ctx.endswith("…")
    assert "<u><b>ERREUR</b></u>" in ctx


def test_build_context_no_truncation():
    ctx = _build_context("court ERR fin", 6, 3)
    assert not ctx.startswith("…")
    assert "<u><b>ERR</b></u>" in ctx


def test_format_match():
    html = _format_match("Faute", "ctx", "<i>sug</i>")
    assert "Faute" in html
    assert "Suggestion" in html


def test_language_tool_info():
    ok, info = language_tool_info()
    assert isinstance(ok, bool)
    assert isinstance(info, str)


# --- _no_checker_warning ---


def test_no_checker_warning_grammalecte(qtbot, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: captured.setdefault("msg", a[2])
    )
    _no_checker_warning(None, grammalecte_preferred=True)
    assert "Grammalecte" in captured["msg"]


def test_no_checker_warning_languagetool(qtbot, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: captured.setdefault("msg", a[2])
    )
    # LT enabled in config but module not installed → mentions language-tool-python
    _no_checker_warning(None, grammalecte_preferred=False, languagetool_enabled=True)
    assert "language-tool-python" in captured["msg"]


def test_no_checker_warning_none_enabled(qtbot, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: captured.setdefault("msg", a[2])
    )
    # Neither checker enabled → generic "activate one" message
    _no_checker_warning(None, grammalecte_preferred=False, languagetool_enabled=False)
    assert "Préférences" in captured["msg"]


# --- SpellCheckDialog avec moteur LanguageTool mocké ---


class _FakeMatch:
    def __init__(self, offset, error_length, message, replacements):
        self.offset = offset
        self.error_length = error_length
        self.message = message
        self.replacements = replacements


class _FakeTool:
    def __init__(self, *a, **k):
        pass

    def check(self, text):
        if "faute" in text:
            return [_FakeMatch(0, 5, "Erreur détectée", ["correct"])]
        return []


@pytest.fixture
def fake_lt(monkeypatch):
    fake_mod = types.ModuleType("language_tool_python")
    fake_mod.LanguageTool = _FakeTool
    monkeypatch.setitem(sys.modules, "language_tool_python", fake_mod)
    monkeypatch.setattr(sc, "_lt_tool", None)
    monkeypatch.setattr(sc, "_lt_tool_url", None)
    return fake_mod


def test_spellcheck_dialog_languagetool_with_errors(qtbot, fake_lt):
    dlg = SpellCheckDialog([("Réalisation", "<p>faute ici</p>")], "languagetool")
    qtbot.addWidget(dlg)
    html = dlg._browser.toHtml()
    assert "Erreur détectée" in html


def test_spellcheck_dialog_languagetool_no_errors(qtbot, fake_lt):
    dlg = SpellCheckDialog([("Section", "<p>texte propre</p>")], "languagetool")
    qtbot.addWidget(dlg)
    assert "Aucun problème" in dlg._browser.toHtml()


def test_spellcheck_dialog_no_text(qtbot, fake_lt):
    dlg = SpellCheckDialog([("Vide", "")], "languagetool")
    qtbot.addWidget(dlg)
    assert "Aucun texte" in dlg._browser.toHtml()


def test_spellcheck_dialog_update_check(qtbot, fake_lt):
    dlg = SpellCheckDialog([("S", "<p>propre</p>")], "languagetool")
    qtbot.addWidget(dlg)
    dlg.update_check([("S2", "<p>faute</p>")], "languagetool")
    assert "Erreur détectée" in dlg._browser.toHtml()


def test_spellcheck_dialog_title_grammalecte(qtbot, fake_lt):
    dlg = SpellCheckDialog([("S", "")], "grammalecte")
    qtbot.addWidget(dlg)
    assert "Grammalecte" in dlg.windowTitle()


# --- run_spellcheck ---


def test_run_spellcheck_no_checker(qtbot, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(sc, "grammalecte_info", lambda: (False, ""))
    monkeypatch.setattr(sc, "language_tool_info", lambda: (False, ""))
    monkeypatch.setattr(sc, "_spellcheck_dialog", None)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", True)
    )
    sc.run_spellcheck([("S", "texte")])
    assert warned.get("w") is True


def test_run_spellcheck_opens_dialog(qtbot, monkeypatch, tmp_path, fake_lt):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # Write a config that enables LanguageTool so the dialog opens
    cfg_path = tmp_path / "pbrecipe" / "app.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        "%YAML 1.2\n---\nlanguagetool_enabled: true\n", encoding="utf-8"
    )
    monkeypatch.setattr(sc, "grammalecte_info", lambda: (False, ""))
    monkeypatch.setattr(sc, "language_tool_info", lambda: (True, "1.0"))
    monkeypatch.setattr(sc, "_spellcheck_dialog", None)
    shown = {}
    monkeypatch.setattr(
        SpellCheckDialog, "show", lambda self: shown.setdefault("s", True)
    )
    sc.run_spellcheck([("S", "<p>propre</p>")])
    assert shown.get("s") is True
    if sc._spellcheck_dialog is not None:
        qtbot.addWidget(sc._spellcheck_dialog)
    sc._spellcheck_dialog = None
