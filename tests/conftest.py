import os
import sqlite3

import pytest


def pytest_configure(config):
    # Allows Qt tests to run in headless environments (CI, etc.).
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def first_version_db(tmp_path):
    """SQLite DB migrated by the first version of the equipment feature.

    Returns ``(db_path, yaml_config_path)``. ``equipment`` lacks ``name_plural``
    and ``recipe_equipment`` has the old layout (composite PK, no ``id``,
    ``prefix``, ``suffix``, ``equipment_plural``).
    """
    from pbrecipe.config import RecipeConfig
    from pbrecipe.config.recipe_config import DbConfig
    from pbrecipe.database.database import Database
    from pbrecipe.models import Category, Recipe

    db_path = tmp_path / "old.db"
    db = Database(f"sqlite:///{db_path}")
    db.connect()
    db.create_schema()
    cat = db.save_category(Category(name="Dessert"))
    db.save_recipe(Recipe(code="R", name="R", categories=[cat.id]))
    db.disconnect()
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        DROP TABLE recipe_equipment;
        DROP TABLE equipment;
        CREATE TABLE equipment (id INTEGER PRIMARY KEY, name VARCHAR(50) NOT NULL);
        CREATE TABLE recipe_equipment (
            recipe_code VARCHAR(50), equipment_id INTEGER,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (recipe_code, equipment_id));
        """
    )
    con.commit()
    con.close()
    yaml_path = tmp_path / "old.yaml"
    RecipeConfig(name="Ancienne", db=DbConfig(type="sqlite", path=str(db_path))).save(
        yaml_path
    )
    return db_path, yaml_path
