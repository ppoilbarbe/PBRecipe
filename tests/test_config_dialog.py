"""Tests du dialogue de configuration de la base (ConfigDialog)."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMessageBox

from pbrecipe.config.dialog_dirs import DialogDirs
from pbrecipe.config.recipe_config import DbConfig, RecipeConfig
from pbrecipe.ui import config_dialog as cd
from pbrecipe.ui.config_dialog import ConfigDialog


def test_config_dialog_load_sqlite(qtbot):
    cfg = RecipeConfig(name="Base", db=DbConfig(type="sqlite", path="/x.db"))
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    assert dlg._name_edit.text() == "Base"
    assert dlg._sqlite_path.text() == "/x.db"
    assert dlg._db_stack.currentIndex() == 0


def test_config_dialog_load_network(qtbot):
    cfg = RecipeConfig(
        db=DbConfig(type="mariadb", host="h", database="d", user="u", password="p")
    )
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    assert dlg._db_stack.currentIndex() == 1
    assert dlg._db_host.text() == "h"


def test_config_dialog_accept_sqlite(qtbot):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._name_edit.setText("Nouveau")
    dlg._sqlite_path.setText("/data/r.db")
    dlg._php_export_edit.setText("/php")
    dlg._yaml_export_edit.setText("/y.yaml")
    dlg._site_type_edit.setText("cocktails")
    dlg._accept()
    assert cfg.name == "Nouveau"
    assert cfg.db.path == "/data/r.db"
    assert cfg.php_export_dir == "/php"
    assert cfg.yaml_export_file == "/y.yaml"
    assert cfg.site_type == "cocktails"


def test_config_dialog_accept_defaults_when_empty(qtbot):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._name_edit.setText("")
    dlg._site_type_edit.setText("")
    dlg._sqlite_path.setText("")
    dlg._accept()
    assert cfg.name == "Mes Recettes"
    assert cfg.site_type == "recettes"
    assert cfg.db.path == "~/recipes.db"


def test_config_dialog_accept_network(qtbot):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    for i in range(dlg._db_type.count()):
        if dlg._db_type.itemData(i) == "postgresql":
            dlg._db_type.setCurrentIndex(i)
            break
    assert dlg._db_port.value() == 5432
    dlg._db_host.setText("")
    dlg._db_name.setText("mabase")
    dlg._php_db_host.setText("phost")
    dlg._php_db_port.setValue(1234)
    dlg._accept()
    assert cfg.db.type == "postgresql"
    assert cfg.db.host == "localhost"
    assert cfg.db.database == "mabase"
    assert cfg.db.php_host == "phost"
    assert cfg.db.php_port == 1234


def test_config_dialog_db_type_mariadb_port(qtbot):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    for i in range(dlg._db_type.count()):
        if dlg._db_type.itemData(i) == "mariadb":
            dlg._db_type.setCurrentIndex(i)
            break
    assert dlg._db_port.value() == 3306


def test_config_dialog_test_connection_sqlite_noop(qtbot):
    cfg = RecipeConfig(db=DbConfig(type="sqlite"))
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    dlg._test_connection()  # sqlite → return immédiat, pas d'exception


def test_config_dialog_test_connection_failure(qtbot, monkeypatch):
    cfg = RecipeConfig(db=DbConfig(type="mariadb"))
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    for i in range(dlg._db_type.count()):
        if dlg._db_type.itemData(i) == "mariadb":
            dlg._db_type.setCurrentIndex(i)
            break
    dlg._db_host.setText("nonexistent.invalid")
    dlg._db_name.setText("x")
    captured = {}
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *a, **k: captured.setdefault("c", True)
    )
    monkeypatch.setattr(
        QMessageBox, "information", lambda *a, **k: captured.setdefault("i", True)
    )
    dlg._test_connection()
    assert captured.get("c") is True


def test_config_dialog_browse_sqlite(qtbot, tmp_path, monkeypatch):
    cfg = RecipeConfig()
    dd_obj = DialogDirs()
    dlg = ConfigDialog(cfg, dialog_dirs=dd_obj)
    qtbot.addWidget(dlg)
    target = str(tmp_path / "mybase")
    monkeypatch.setattr(cd.QFileDialog, "exec", lambda self: 1)
    monkeypatch.setattr(cd.QFileDialog, "selectedFiles", lambda self: [target])
    dlg._browse_sqlite_path()
    assert dlg._sqlite_path.text() == target + ".db"


def test_config_dialog_browse_sqlite_cancel(qtbot, monkeypatch):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(cd.QFileDialog, "exec", lambda self: 0)
    dlg._browse_sqlite_path()


def test_config_dialog_browse_php_dir(qtbot, tmp_path, monkeypatch):
    cfg = RecipeConfig()
    dd_obj = DialogDirs()
    dlg = ConfigDialog(cfg, dialog_dirs=dd_obj)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path)
    )
    dlg._browse_php_export_dir()
    assert dlg._php_export_edit.text() == str(tmp_path)


def test_config_dialog_browse_php_dir_cancel(qtbot, monkeypatch):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: "")
    dlg._browse_php_export_dir()
    assert dlg._php_export_edit.text() == ""


def test_config_dialog_browse_yaml(qtbot, tmp_path, monkeypatch):
    cfg = RecipeConfig()
    dd_obj = DialogDirs()
    dlg = ConfigDialog(cfg, dialog_dirs=dd_obj)
    qtbot.addWidget(dlg)
    target = str(tmp_path / "dump")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (target, ""))
    dlg._browse_yaml_export_file()
    assert dlg._yaml_export_edit.text() == target + ".yaml"


def test_config_dialog_browse_yaml_cancel(qtbot, monkeypatch):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    dlg._browse_yaml_export_file()


def test_config_dialog_config_property(qtbot):
    cfg = RecipeConfig()
    dlg = ConfigDialog(cfg)
    qtbot.addWidget(dlg)
    assert dlg.config is cfg
