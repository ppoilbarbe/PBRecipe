# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for a recipe source (book, website, person, …)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Source:
    id: int | None = None
    name: str = ""  # max 100 chars, non-empty
    shortcut: str = ""  # optional short display text, max MAX_SOURCE_SHORTCUT chars
