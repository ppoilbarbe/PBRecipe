"""Tests des dialogues About, Globals, Preferences et Consistency."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.config.app_config import AppConfig
from pbrecipe.database.database import Database
from pbrecipe.models import Recipe, RecipeMedia, Technique
from pbrecipe.ui.about_dialog import AboutDialog
from pbrecipe.ui.consistency_dialog import (
    ConsistencyReportDialog,
    build_report,
    run_check,
)
from pbrecipe.ui.globals_dialog import GlobalsDialog
from pbrecipe.ui.preferences_dialog import PreferencesDialog


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


# --- AboutDialog ---


def test_about_dialog(qtbot):
    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    assert "propos" in dlg.windowTitle()


# --- GlobalsDialog ---


def test_globals_dialog_load_and_accept(qtbot, db):
    db.set_globals({"site_title": "Mon Site", "presentation": "<p>Intro</p>"})
    dlg = GlobalsDialog(db)
    qtbot.addWidget(dlg)
    assert dlg._string_edits["site_title"].text() == "Mon Site"
    dlg._string_edits["site_title"].setText("Nouveau")
    dlg._string_edits["recipe_singular"].setText("")
    dlg._accept()
    data = db.get_globals()
    assert data["site_title"] == "Nouveau"
    assert data["presentation"] == "<p>Intro</p>"


def test_globals_dialog_empty(qtbot, db):
    dlg = GlobalsDialog(db)
    qtbot.addWidget(dlg)
    dlg._accept()
    assert db.get_globals() == {}


# --- PreferencesDialog ---


def test_preferences_load_and_accept(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # grammalecte_info() exécute le moteur Grammalecte complet ; sous coverage,
    # le trace callback s'applique à chacune de ses lignes internes → ~35 s.
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (False, "")
    )
    cfg = AppConfig(log_level="WARNING", php_debug=True)
    dlg = PreferencesDialog(cfg)
    qtbot.addWidget(dlg)
    assert dlg._php_debug_cb.isChecked() is True
    dlg._php_debug_cb.setChecked(False)
    for i in range(dlg._level_combo.count()):
        if dlg._level_combo.itemData(i) == "DEBUG":
            dlg._level_combo.setCurrentIndex(i)
            break
    dlg._accept()
    assert cfg.log_level == "DEBUG"
    assert cfg.php_debug is False


def test_preferences_grammalecte_status(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (True, "2.0")
    )
    cfg = AppConfig()
    dlg = PreferencesDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._refresh_grammalecte_status()
    assert "installé" in dlg._gram_status.text()


def test_preferences_grammalecte_absent(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (False, "")
    )
    cfg = AppConfig()
    dlg = PreferencesDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._refresh_grammalecte_status()
    assert "non installé" in dlg._gram_status.text()


def test_preferences_install_finished_success(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (True, "2.1")
    )
    cfg = AppConfig()
    dlg = PreferencesDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._on_install_finished(0, None)
    assert "réussie" in dlg._gram_install_log.text()


def test_preferences_install_finished_failure(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (False, "boom")
    )
    cfg = AppConfig()
    dlg = PreferencesDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._on_install_finished(1, None)
    assert "Échec" in dlg._gram_install_log.text()


# --- consistency_dialog ---


def test_run_check_no_issues(db):
    db.save_recipe(Recipe(code="R1", name="R1", description="<p>Texte simple</p>"))
    recipe_issues, tech_issues, pres_issues = run_check(db)
    assert recipe_issues == []
    assert tech_issues == []
    assert pres_issues == []


def test_run_check_broken_refs(db):
    db.save_recipe(
        Recipe(
            code="R1",
            name="Recette 1",
            description="[IMG:R1:MISSING] [RECIPE:GHOST] [TECH:NOPE]",
            comments="[IMG:OLDFORMAT]",
        )
    )
    db.save_technique(Technique(code="T1", title="Tech", description="[RECIPE:ABSENT]"))
    db.set_globals({"presentation": "[TECH:VANISHED]"})
    recipe_issues, tech_issues, pres_issues = run_check(db)
    assert recipe_issues and recipe_issues[0].code == "R1"
    kinds = {ref.kind for ref in recipe_issues[0].refs}
    assert {"IMG", "RECIPE", "TECH", "IMG_OLD"} <= kinds
    assert tech_issues
    assert pres_issues


def test_run_check_valid_refs(db):
    db.save_recipe(
        Recipe(
            code="R1",
            name="R1",
            description="[RECIPE:R2] [TECH:T1] [IMG:R1:PHOTO]",
            media=[RecipeMedia(recipe_code="R1", position=0, code="PHOTO", data=b"x")],
        )
    )
    db.save_recipe(Recipe(code="R2", name="R2"))
    db.save_technique(Technique(code="T1", title="T1"))
    recipe_issues, _, _ = run_check(db)
    assert recipe_issues == []


def test_build_report():
    db_issues, tech_issues, pres_issues = [], [], []
    html = build_report(db_issues, tech_issues, pres_issues)
    assert "0 problème" in html
    assert "<html>" in html


def test_consistency_report_dialog(qtbot, db):
    db.save_recipe(Recipe(code="R", name="R", description="[RECIPE:GHOST]"))
    issues = run_check(db)
    html = build_report(*issues)
    assert "GHOST" in html
    dlg = ConsistencyReportDialog(html)
    qtbot.addWidget(dlg)
    assert "cohérence" in dlg.windowTitle()
