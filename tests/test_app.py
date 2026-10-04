"""Tests des modes headless de app.py et de argparse_qt."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pytest

from pbrecipe import app
from pbrecipe.argparse_qt import add_qt_arguments
from pbrecipe.config import RecipeConfig
from pbrecipe.config.recipe_config import DbConfig
from pbrecipe.database.database import Database

# --------------------------------------------------------------------------
# argparse_qt
# --------------------------------------------------------------------------


def _parser_with_qt():
    p = argparse.ArgumentParser()
    add_qt_arguments(p)
    return p


def test_qt_args_with_value():
    args = _parser_with_qt().parse_args(["--style", "fusion"])
    assert args.qt_args == ["-style", "fusion"]


def test_qt_args_flag_no_value():
    args = _parser_with_qt().parse_args(["--reverse"])
    assert args.qt_args == ["-reverse"]


def test_qt_args_multiple():
    args = _parser_with_qt().parse_args(["--style", "fusion", "--reverse"])
    assert args.qt_args == ["-style", "fusion", "-reverse"]


def test_qt_args_default_empty():
    assert _parser_with_qt().parse_args([]).qt_args == []


def test_qt_help_hides_options_from_usage():
    p = _parser_with_qt()
    usage = p.format_usage()
    assert "--style" not in usage
    full_help = p.format_help()
    assert "Qt options" in full_help


# --------------------------------------------------------------------------
# apply_log_level
# --------------------------------------------------------------------------


def test_apply_log_level_debug():
    app.apply_log_level(logging.DEBUG)
    assert logging.getLogger().level == logging.DEBUG


def test_apply_log_level_info_no_handlers(monkeypatch):
    root = logging.getLogger()
    saved = root.handlers[:]
    root.handlers = []
    try:
        app.apply_log_level(logging.WARNING)
        assert root.level == logging.WARNING
    finally:
        root.handlers = saved


# --------------------------------------------------------------------------
# Fixtures pour les modes headless
# --------------------------------------------------------------------------


@pytest.fixture
def config_file(tmp_path: Path):
    db_path = tmp_path / "recipes.db"
    db = Database(f"sqlite:///{db_path}")
    db.connect()
    db.create_schema()
    db.disconnect()
    cfg = RecipeConfig(
        name="Test",
        db=DbConfig(type="sqlite", path=str(db_path)),
        php_export_dir=str(tmp_path / "php"),
    )
    yaml_path = tmp_path / "conf.yaml"
    cfg.save(yaml_path)
    return yaml_path


def _run_main(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["pbrecipe", *argv])
    app.main()


# --------------------------------------------------------------------------
# --check-connect
# --------------------------------------------------------------------------


def test_check_connect_ok(monkeypatch, config_file, capsys):
    _run_main(monkeypatch, [str(config_file), "--check-connect"])
    out = capsys.readouterr().out
    assert "[OK]" in out
    assert "Connexion opérationnelle" in out


def test_check_connect_missing_file(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(missing), "--check-connect"])
    assert "introuvable" in capsys.readouterr().out


def test_check_connect_no_recent(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--check-connect"])
    assert "[ERREUR]" in capsys.readouterr().out


def test_check_connect_bad_config(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: [unterminated\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(bad), "--check-connect"])
    assert "[ERREUR]" in capsys.readouterr().out


# --------------------------------------------------------------------------
# --export-php
# --------------------------------------------------------------------------


def test_export_php_explicit_dir(monkeypatch, config_file, tmp_path, capsys):
    target = tmp_path / "out_php"
    _run_main(monkeypatch, [str(config_file), "--export-php", str(target)])
    assert (target / "index.php").exists()


def test_export_php_config_dir(monkeypatch, config_file):
    cfg = RecipeConfig.from_file(config_file)
    _run_main(monkeypatch, [str(config_file), "--export-php"])
    assert (Path(cfg.php_export_dir) / "index.php").exists()


def test_export_php_no_dir_configured(monkeypatch, tmp_path):
    db_path = tmp_path / "r.db"
    Database(f"sqlite:///{db_path}").connect()
    cfg = RecipeConfig(db=DbConfig(type="sqlite", path=str(db_path)))
    yaml_path = tmp_path / "c.yaml"
    cfg.save(yaml_path)
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(yaml_path), "--export-php"])


def test_export_php_missing_config(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        _run_main(
            monkeypatch, [str(tmp_path / "nope.yaml"), "--export-php", str(tmp_path)]
        )


def test_export_php_no_recent(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--export-php", str(tmp_path / "out")])


# --------------------------------------------------------------------------
# --export-yaml
# --------------------------------------------------------------------------


def test_export_yaml_explicit_file(monkeypatch, config_file, tmp_path):
    target = tmp_path / "dump"
    _run_main(monkeypatch, [str(config_file), "--export-yaml", str(target)])
    assert (tmp_path / "dump.yaml").exists()


def test_export_yaml_missing_config(monkeypatch, tmp_path):
    with pytest.raises(SystemExit):
        _run_main(
            monkeypatch,
            [str(tmp_path / "nope.yaml"), "--export-yaml", str(tmp_path / "o.yaml")],
        )


def test_export_yaml_no_recent(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--export-yaml", str(tmp_path / "o.yaml")])


def test_export_yaml_bad_config(monkeypatch, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("db: [unterminated\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(bad), "--export-yaml", str(tmp_path / "o.yaml")])


# --------------------------------------------------------------------------
# Mise à jour du schéma avant export headless
# --------------------------------------------------------------------------


def _drop_equipment_tables(config_file: Path) -> Database:
    db = Database(f"sqlite:///{RecipeConfig.from_file(config_file).db.path}")
    db.connect()
    with db._tx() as conn:
        conn.exec_driver_sql("DROP TABLE recipe_equipment")
        conn.exec_driver_sql("DROP TABLE equipment")
    db.disconnect()
    return db


def _table_names(db: Database) -> set[str]:
    from sqlalchemy import inspect

    db.connect()
    try:
        return set(inspect(db._engine).get_table_names())
    finally:
        db.disconnect()


def test_export_yaml_upgrades_old_schema(monkeypatch, config_file, tmp_path):
    db = _drop_equipment_tables(config_file)
    target = tmp_path / "dump.yaml"
    _run_main(monkeypatch, [str(config_file), "--export-yaml", str(target)])
    assert target.exists()
    assert {"equipment", "recipe_equipment"} <= _table_names(db)


def test_export_php_upgrades_old_schema(monkeypatch, config_file, tmp_path):
    db = _drop_equipment_tables(config_file)
    target = tmp_path / "out_php"
    _run_main(monkeypatch, [str(config_file), "--export-php", str(target)])
    assert (target / "index.php").exists()
    assert {"equipment", "recipe_equipment"} <= _table_names(db)


@pytest.mark.parametrize("option", ["--export-yaml", "--export-php"])
def test_export_refuses_empty_database(monkeypatch, tmp_path, option):
    db_path = tmp_path / "empty.db"
    cfg = RecipeConfig(db=DbConfig(type="sqlite", path=str(db_path)))
    yaml_path = tmp_path / "c.yaml"
    cfg.save(yaml_path)
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(yaml_path), option, str(tmp_path / "out")])
    db = Database(f"sqlite:///{db_path}")
    assert _table_names(db) == set()  # aucune table créée silencieusement


@pytest.mark.parametrize("option", ["--export-yaml", "--export-php"])
def test_export_refuses_foreign_database(monkeypatch, tmp_path, option):
    db_path = tmp_path / "foreign.db"
    db = Database(f"sqlite:///{db_path}")
    db.connect()
    with db._tx() as conn:
        conn.exec_driver_sql("CREATE TABLE autre (id INTEGER)")
    db.disconnect()
    cfg = RecipeConfig(db=DbConfig(type="sqlite", path=str(db_path)))
    yaml_path = tmp_path / "c.yaml"
    cfg.save(yaml_path)
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(yaml_path), option, str(tmp_path / "out")])
    assert _table_names(db) == {"autre"}


# --------------------------------------------------------------------------
# Erreurs de base de données non interceptées (interface graphique)
# --------------------------------------------------------------------------


def _db_error():
    from sqlalchemy.exc import OperationalError

    return OperationalError(
        "SELECT equipment.name_plural FROM equipment",
        {},
        Exception("no such column: equipment.name_plural"),
    )


def test_db_error_hook_shows_message_then_quits(qtbot, monkeypatch):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self) or 0)
    scheduled = []
    monkeypatch.setattr(QTimer, "singleShot", lambda ms, fn: scheduled.append(fn))
    exits = []
    monkeypatch.setattr("PySide6.QtWidgets.QApplication.exit", exits.append)
    previous = []
    hook = app._DbErrorHook(lambda *a: previous.append(a))

    exc = _db_error()
    hook(type(exc), exc, None)
    assert len(shown) == 1
    assert "no such column: equipment.name_plural" in shown[0].text()
    assert "SELECT equipment.name_plural" in shown[0].detailedText()
    assert len(scheduled) == 1
    scheduled[0]()
    assert exits == [1]

    # Erreurs suivantes : journalisées seulement, pas de second message
    hook(type(exc), exc, None)
    assert len(shown) == 1 and len(scheduled) == 1
    assert previous == []


def test_db_error_hook_forwards_other_exceptions(monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: pytest.fail("aucun message attendu")
    )
    previous = []
    hook = app._DbErrorHook(lambda *a: previous.append(a))
    exc = ValueError("x")
    hook(ValueError, exc, None)
    assert previous == [(ValueError, exc, None)]


@pytest.mark.parametrize("option", ["--export-yaml", "--export-php"])
def test_export_refuses_incompatible_schema(
    monkeypatch, first_version_db, tmp_path, option, caplog
):
    _db_path, yaml_path = first_version_db
    target = tmp_path / "out"
    with pytest.raises(SystemExit) as info:
        _run_main(monkeypatch, [str(yaml_path), option, str(target)])
    assert info.value.code == 1
    assert "equipment.name_plural" in caplog.text
    assert not target.exists() and not (tmp_path / "out.yaml").exists()


def test_check_connect_reports_incompatible_schema(
    monkeypatch, first_version_db, capsys
):
    _db_path, yaml_path = first_version_db
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, [str(yaml_path), "--check-connect"])
    out = capsys.readouterr().out
    assert "[ERREUR] Schéma incompatible" in out
    assert "equipment.name_plural" in out
