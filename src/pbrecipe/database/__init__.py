# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exposes the Database class and create_database factory for recipe database access."""

from pbrecipe.database.database import Database
from pbrecipe.database.factory import create_database

__all__ = ["Database", "create_database"]
