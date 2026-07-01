# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for a recipe category."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Category:
    id: int | None = None
    name: str = ""  # max 20 chars, non-empty
