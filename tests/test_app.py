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
