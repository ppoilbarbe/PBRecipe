"""Tests de la fenêtre principale (MainWindow) avec base SQLite."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox

from pbrecipe.config import AppConfig, RecipeConfig
from pbrecipe.config.recipe_config import DbConfig
from pbrecipe.models import Category, Recipe
from pbrecipe.ui import main_window as mw_mod
from pbrecipe.ui.main_window import MainWindow


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))


@pytest.fixture(autouse=True)
def mock_progress_dialog(monkeypatch):
    """Neutralise _make_yaml_progress pour éviter QProgressDialog et processEvents().

    processEvents() avec coverage instrumente chaque event Qt → lenteur ×8.
    On remplace la méthode entière par un no-op qui renvoie un faux dialog et
    un callback vide, comme le fait PBRenamer pour QMenu.exec().
    """
    mock_dlg = MagicMock()
    monkeypatch.setattr(
        mw_mod.MainWindow,
        "_make_yaml_progress",
        lambda self, title: (mock_dlg, lambda *a: None),
    )


@pytest.fixture
def config_file(tmp_path):
    db_path = tmp_path / "recipes.db"
    cfg = RecipeConfig(
        name="Ma Base",
        db=DbConfig(type="sqlite", path=str(db_path)),
        php_export_dir=str(tmp_path / "php"),
    )
    yaml_path = tmp_path / "conf.yaml"
    cfg.save(yaml_path)
    return yaml_path


@pytest.fixture
def window(qtbot, config_file):
    app_config = AppConfig()
    win = MainWindow(initial_path=str(config_file), app_config=app_config)
    qtbot.addWidget(win)
    return win


def _add_recipe(win, code="GATEAU", name="Gâteau"):
    cat = win._db.save_category(Category(name="Dessert"))
    win._db.save_recipe(Recipe(code=code, name=name, categories=[cat.id]))
    win._refresh_recipe_list()
    return cat


def test_window_loads_config(window):
    assert window._config is not None
    assert window._db is not None
    assert "Ma Base" in window.windowTitle()
    assert "sqlite:recipes.db" == window._db_label.text()


def test_window_no_initial_path(qtbot):
    win = MainWindow(app_config=AppConfig())
    qtbot.addWidget(win)
    assert win._config is None
    assert win.windowTitle() == "PBRecipe"


def test_auto_load_missing_file(qtbot):
    win = MainWindow(initial_path="/nonexistent/x.yaml", app_config=AppConfig())
    qtbot.addWidget(win)
    assert win._config is None


def test_auto_load_corrupt(qtbot, tmp_path, monkeypatch):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: [unterminated\n", encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    win = MainWindow(initial_path=str(bad), app_config=AppConfig())
    qtbot.addWidget(win)
    assert win._config is None


def test_refresh_and_select_recipe(window):
    _add_recipe(window)
    assert window._recipe_list.count() == 1
    window._recipe_list.setCurrentRow(0)
    assert window._stack.currentWidget() is window._recipe_editor


def test_filter_recipes(window):
    _add_recipe(window, "A", "Tarte")
    window._db.save_recipe(Recipe(code="B", name="Mousse"))
    window._refresh_recipe_list()
    window._filter_edit.setText("tarte")
    visible = [
        window._recipe_list.item(i).text()
        for i in range(window._recipe_list.count())
        if not window._recipe_list.item(i).isHidden()
    ]
    assert visible == ["Tarte"]


def test_new_recipe(window):
    window._new_recipe()
    assert window._stack.currentWidget() is window._recipe_editor


def test_new_recipe_no_db(qtbot, monkeypatch):
    win = MainWindow(app_config=AppConfig())
    qtbot.addWidget(win)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", 1)
    )
    win._new_recipe()
    assert warned.get("w") == 1


def test_copy_recipe(window):
    _add_recipe(window)
    window._recipe_list.setCurrentRow(0)
    window._copy_recipe()
    assert window._stack.currentWidget() is window._recipe_editor
    assert "Copie de" in window._recipe_editor._name_edit.text()


def test_delete_recipe(window, monkeypatch):
    _add_recipe(window)
    window._recipe_list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    window._delete_recipe()
    assert window._recipe_list.count() == 0


def test_recipe_saved_signal(window):
    cat = _add_recipe(window)
    window._recipe_list.setCurrentRow(0)
    recipe = window._db.get_recipe("GATEAU")
    recipe.name = "Gâteau v2"
    recipe.categories = [cat.id]
    window._on_recipe_saved(recipe)
    assert window._db.get_recipe("GATEAU").name == "Gâteau v2"


def test_recent_menu_and_clear(window):
    window._register_recent("/tmp/foo.yaml")
    assert window._app_config.recent_files
    window._clear_recent()
    assert window._app_config.recent_files == []


def test_open_recent_missing(window, monkeypatch):
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", 1)
    )
    window._open_recent("/no/such/file.yaml")
    assert warned.get("w") == 1


def test_edit_config_dialogs(window, monkeypatch):
    monkeypatch.setattr(mw_mod.ConfigDialog, "exec", lambda self: 0)
    window._edit_config()  # annulé → no-op


def test_new_config_cancel(window, monkeypatch):
    monkeypatch.setattr(mw_mod.ConfigDialog, "exec", lambda self: 0)
    window._new_config()


def test_reference_editors_open(window, monkeypatch):
    for mod, cls in [
        ("category_dialog", "CategoryDialog"),
        ("ingredient_dialog", "IngredientDialog"),
        ("unit_dialog", "UnitDialog"),
        ("technique_dialog", "TechniqueDialog"),
        ("source_dialog", "SourceDialog"),
        ("difficulty_dialog", "DifficultyDialog"),
    ]:
        monkeypatch.setattr(f"pbrecipe.ui.dialogs.{mod}.{cls}.exec", lambda self: 0)
    window._edit_categories()
    window._edit_ingredients()
    window._edit_units()
    window._edit_techniques()
    window._edit_sources()
    window._edit_difficulty_levels()


def test_edit_globals_and_preferences(window, monkeypatch):
    monkeypatch.setattr("pbrecipe.ui.globals_dialog.GlobalsDialog.exec", lambda self: 0)
    monkeypatch.setattr(
        "pbrecipe.ui.preferences_dialog.PreferencesDialog.exec", lambda self: 0
    )
    # grammalecte_info() exécute le moteur Grammalecte complet ; sous coverage,
    # le trace callback s'applique à chacune de ses lignes internes → ~35 s.
    # On le neutralise : ce test couvre main_window, pas Grammalecte.
    monkeypatch.setattr(
        "pbrecipe.ui.spellcheck_dialog.grammalecte_info", lambda: (False, "")
    )
    window._edit_globals()
    window._edit_preferences()


def test_show_about(window, monkeypatch):
    monkeypatch.setattr(mw_mod.AboutDialog, "exec", lambda self: 0)
    window._show_about()


def test_check_consistency_clean(window, monkeypatch):
    info = {}
    monkeypatch.setattr(
        QMessageBox, "information", lambda *a, **k: info.setdefault("i", 1)
    )
    window._check_consistency()
    assert info.get("i") == 1


def test_check_consistency_with_issues(window):
    window._db.save_recipe(Recipe(code="R", name="R", description="[RECIPE:GHOST]"))
    window._check_consistency()
    assert window._consistency_dialog is not None


def test_export_yaml_configured(window, tmp_path, monkeypatch):
    _add_recipe(window)
    out = tmp_path / "dump.yaml"
    window._config.yaml_export_file = str(out)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    window._export_yaml()
    assert out.exists()


def test_export_yaml_no_db(qtbot, monkeypatch):
    win = MainWindow(app_config=AppConfig())
    qtbot.addWidget(win)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", 1)
    )
    win._export_yaml()
    assert warned.get("w") == 1


def test_export_yaml_as(window, tmp_path, monkeypatch):
    _add_recipe(window)
    out = tmp_path / "as.yaml"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(out), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    window._export_yaml_as()
    assert out.exists()


def test_import_yaml(window, tmp_path, monkeypatch):
    _add_recipe(window)
    src = tmp_path / "exp.yaml"
    from pbrecipe.export.yaml_io import YamlExport

    YamlExport(window._db).run(str(src))

    window._db.delete_recipe("GATEAU")
    window._refresh_recipe_list()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(src), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    # Le mode est choisi via un QMessageBox dont on simule le bouton « Fusionner ».
    real_exec = mw_mod.QMessageBox.exec
    clicked_holder = {}

    def fake_exec(self):
        # Retient le bouton « Fusionner » (rôle AcceptRole, non-défaut).
        for btn in self.buttons():
            if btn.text() == "Fusionner":
                clicked_holder["btn"] = btn
        return 0

    monkeypatch.setattr(mw_mod.QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(
        mw_mod.QMessageBox,
        "clickedButton",
        lambda self: clicked_holder.get("btn"),
    )
    window._import_yaml()
    assert window._db.get_recipe("GATEAU") is not None
    monkeypatch.setattr(mw_mod.QMessageBox, "exec", real_exec)


def test_import_yaml_replace(window, tmp_path, monkeypatch):
    _add_recipe(window)
    src = tmp_path / "exp2.yaml"
    from pbrecipe.export.yaml_io import YamlExport

    YamlExport(window._db).run(str(src))
    window._db.save_recipe(Recipe(code="EXTRA", name="Extra"))
    window._refresh_recipe_list()

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(src), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)

    clicked_holder = {}

    def fake_exec(self):
        for btn in self.buttons():
            if btn.text() == "Remplacer":
                clicked_holder["btn"] = btn
        return 0

    monkeypatch.setattr(mw_mod.QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(
        mw_mod.QMessageBox,
        "clickedButton",
        lambda self: clicked_holder.get("btn"),
    )
    window._import_yaml()
    assert window._db.get_recipe("EXTRA") is None


def test_export_php_configured(window, tmp_path, monkeypatch):
    _add_recipe(window)
    target = tmp_path / "phpout"
    window._config.php_export_dir = str(target)
    target.mkdir()
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    window._export_php()
    assert (target / "index.php").exists()


def test_export_php_with_consistency_issues(window, tmp_path, monkeypatch):
    window._db.save_recipe(Recipe(code="R", name="R", description="[RECIPE:GHOST]"))
    target = tmp_path / "phpout2"
    target.mkdir()
    window._config.php_export_dir = str(target)
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    window._export_php()
    # export annulé → pas de fichier index.php
    assert not (target / "index.php").exists()


def test_export_php_as(window, tmp_path, monkeypatch):
    _add_recipe(window)
    target = tmp_path / "phpas"
    target.mkdir()
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **k: str(target)
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    window._export_php_as()
    assert (target / "index.php").exists()


def test_export_php_no_db(qtbot, monkeypatch):
    win = MainWindow(app_config=AppConfig())
    qtbot.addWidget(win)
    warned = {}
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: warned.setdefault("w", 1)
    )
    win._export_php()
    assert warned.get("w") == 1


def test_confirm_discard_no_changes(window):
    assert window._confirm_discard() is True


def test_close_event_saves_geometry(window):
    window.close()
    assert "width" in window._app_config.window_geometry


def test_normalize_filter():
    assert MainWindow._normalize_filter("Crème Brûlée") == "creme brulee"


def test_update_db_label_network(qtbot):
    cfg = RecipeConfig(db=DbConfig(type="mariadb", database="mabase"))
    win = MainWindow(app_config=AppConfig())
    qtbot.addWidget(win)
    win._config = cfg
    win._update_db_label()
    assert win._db_label.text() == "mariadb:mabase"
