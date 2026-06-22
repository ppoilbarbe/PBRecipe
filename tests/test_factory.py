"""Tests de create_database (construction d'URL selon le type de base)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pbrecipe.config import RecipeConfig
from pbrecipe.config.recipe_config import DbConfig
from pbrecipe.database import create_database


def test_sqlite_url(tmp_path: Path):
    cfg = RecipeConfig(db=DbConfig(type="sqlite", path=str(tmp_path / "r.db")))
    db = create_database(cfg)
    assert db._url.startswith("sqlite:///")
    assert str(tmp_path / "r.db") in db._url


def test_mariadb_url():
    cfg = RecipeConfig(
        db=DbConfig(
            type="mariadb",
            host="h",
            port=3306,
            database="d",
            user="u",
            password="p@ss",
        )
    )
    db = create_database(cfg)
    assert db._url.startswith("mysql+pymysql://")
    assert "p%40ss" in db._url
    assert "charset=utf8mb4" in db._url


def test_postgresql_url():
    cfg = RecipeConfig(
        db=DbConfig(
            type="postgresql",
            host="h",
            port=5432,
            database="d",
            user="u",
            password="pwd",
        )
    )
    db = create_database(cfg)
    assert db._url.startswith("postgresql+psycopg2://")


def test_unsupported_type():
    cfg = RecipeConfig(db=DbConfig(type="oracle"))
    with pytest.raises(ValueError):
        create_database(cfg)
