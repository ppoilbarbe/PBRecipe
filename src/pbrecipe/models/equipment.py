# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for a piece of kitchen equipment needed to make a recipe."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Equipment:
    id: int | None = None
    name: str = ""  # max 50 chars, non-empty
    name_plural: str = ""  # max 50 chars, optional plural form
