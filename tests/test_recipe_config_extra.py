"""Tests complémentaires de RecipeConfig / DbConfig."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.config import RecipeConfig
from pbrecipe.config.recipe_config import DbConfig


def test_php_credentials_fallback():
    db = DbConfig(host="h", port=3306, user="u", password="p")
    assert db.php_credentials() == ("h", 3306, "u", "p")


def test_php_credentials_override():
    db = DbConfig(
        host="h",
        port=3306,
        user="u",
        password="p",
        php_host="ph",
        php_port=5432,
        php_user="pu",
        php_password="pp",
    )
    assert db.php_credentials() == ("ph", 5432, "pu", "pp")


def test_db_to_dict_includes_php_fields():
    db = DbConfig(php_host="ph", php_port=1, php_user="pu", php_password="pp")
    d = db.to_dict()
    assert d["php_host"] == "ph"
    assert d["php_port"] == 1
    assert d["php_user"] == "pu"
    assert d["php_password"] == "pp"


def test_db_from_dict_ignores_unknown():
    db = DbConfig.from_dict({"type": "mariadb", "unknown_key": 1})
    assert db.type == "mariadb"


def test_save_without_path_raises():
    cfg = RecipeConfig()
    with pytest.raises(ValueError):
        cfg.save()


def test_save_adds_yaml_suffix(tmp_path: Path):
    cfg = RecipeConfig(name="X")
    target = tmp_path / "conf.txt"
    cfg.save(target)
    assert (tmp_path / "conf.yaml").exists()
    assert cfg.path == tmp_path / "conf.yaml"


def test_to_dict_optional_fields():
    cfg = RecipeConfig(
        php_export_dir="/php", yaml_export_file="/y.yaml", site_type="cocktails"
    )
    d = cfg.to_dict()
    assert d["php_export_dir"] == "/php"
    assert d["yaml_export_file"] == "/y.yaml"
    assert d["site_type"] == "cocktails"


def test_save_uses_stored_path(tmp_path: Path):
    target = tmp_path / "c.yaml"
    cfg = RecipeConfig(name="A")
    cfg.save(target)
    cfg.name = "B"
    cfg.save()
    assert RecipeConfig.from_file(target).name == "B"
