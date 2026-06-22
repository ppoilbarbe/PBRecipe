"""Tests de PhpExport (génération des fichiers du site PHP)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.config import RecipeConfig
from pbrecipe.config.recipe_config import DbConfig
from pbrecipe.database.database import Database
from pbrecipe.export import PhpExport, YamlExport, YamlImport
from pbrecipe.export.php_export import PhpExport as DirectPhpExport


@pytest.fixture
def db(tmp_path: Path):
    d = Database(f"sqlite:///{tmp_path / 'test.db'}")
    d.connect()
    d.create_schema()
    yield d
    d.disconnect()


def test_export_module_reexports():
    assert PhpExport is DirectPhpExport
    assert YamlExport is not None
    assert YamlImport is not None


def test_php_export_copies_files(db, tmp_path):
    cfg = RecipeConfig(
        db=DbConfig(type="sqlite", path=str(tmp_path / "data.db")),
        site_type="recettes",
    )
    target = tmp_path / "site"
    PhpExport(cfg, db, target).run()
    assert (target / "index.php").exists()
    assert (target / "lib" / "db.php").exists()
    assert (target / "lib" / "config.php").exists()
    assert (target / "css" / "base.css").exists()
    assert (target / "media").is_dir()


def test_php_config_sqlite(db, tmp_path):
    cfg = RecipeConfig(
        db=DbConfig(type="sqlite", path="~/recipes.db"), site_type="cocktails"
    )
    target = tmp_path / "site"
    PhpExport(cfg, db, target).run()
    content = (target / "lib" / "config.php").read_text(encoding="utf-8")
    assert "sqlite" in content
    assert "cocktails" in content
    assert "false" in content  # SITE_DEBUG par défaut


def test_php_config_mariadb_debug(db, tmp_path):
    cfg = RecipeConfig(
        db=DbConfig(type="mariadb", host="h", database="d", user="u", password="p")
    )
    target = tmp_path / "site"
    PhpExport(cfg, db, target, php_debug=True).run()
    content = (target / "lib" / "config.php").read_text(encoding="utf-8")
    assert "mysql" in content
    assert "true" in content


def test_php_config_postgresql(db, tmp_path):
    cfg = RecipeConfig(db=DbConfig(type="postgresql", host="h", database="d"))
    target = tmp_path / "site"
    PhpExport(cfg, db, target).run()
    content = (target / "lib" / "config.php").read_text(encoding="utf-8")
    assert "pgsql" in content


def test_php_export_clears_media_cache(db, tmp_path):
    cfg = RecipeConfig(db=DbConfig(type="sqlite", path=str(tmp_path / "d.db")))
    target = tmp_path / "site"
    (target / "media").mkdir(parents=True)
    stale = target / "media" / "old.jpg"
    stale.write_bytes(b"stale")
    PhpExport(cfg, db, target).run()
    assert not stale.exists()
    assert (target / "media").is_dir()
