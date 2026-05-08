from pathlib import Path

from pbrecipe.config import RecipeConfig
from pbrecipe.config.recipe_config import DbConfig


def test_defaults():
    cfg = RecipeConfig()
    assert cfg.name == "Mes Recettes"
    assert cfg.db.type == "sqlite"


def test_roundtrip(tmp_path: Path):
    cfg = RecipeConfig(
        name="Cocktails",
        db=DbConfig(type="mariadb", host="db.example.com", database="cocktails"),
    )
    path = tmp_path / "test.yaml"
    cfg.save(path)

    loaded = RecipeConfig.from_file(path)
    assert loaded.name == "Cocktails"
    assert loaded.db.type == "mariadb"
    assert loaded.db.host == "db.example.com"
