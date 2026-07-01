# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for an ingredient with singular and plural forms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Ingredient:
    id: int | None = None
    name: str = ""  # max 50 chars, non-empty
    name_plural: str = ""  # max 50 chars, optional plural form
