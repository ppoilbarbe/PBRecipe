from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote_plus

from pbrecipe.config import RecipeConfig
from pbrecipe.database.database import Database

_log = logging.getLogger(__name__)


def create_database(config: RecipeConfig) -> Database:
    db = config.db
    if db.type == "sqlite":
        path = Path(db.path).expanduser().resolve()
        url = f"sqlite:///{path}"
        _log.debug("Base SQLite : %s", path)
    elif db.type == "mariadb":
        url = (
            f"mysql+pymysql://{quote_plus(db.user)}:{quote_plus(db.password)}"
            f"@{db.host}:{db.port}/{db.database}?charset=utf8mb4"
        )
        _log.debug("Base MariaDB : %s@%s:%s/%s", db.user, db.host, db.port, db.database)
    elif db.type == "postgresql":
        url = (
            f"postgresql+psycopg2://{quote_plus(db.user)}:{quote_plus(db.password)}"
            f"@{db.host}:{db.port}/{db.database}"
        )
        _log.debug(
            "Base PostgreSQL : %s@%s:%s/%s", db.user, db.host, db.port, db.database
        )
    else:
        raise ValueError(f"Unsupported database type: {db.type!r}")
    _log.info("Base de données : type=%s", db.type)
    return Database(url)
