# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for a culinary technique with code, title and HTML description."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Technique:
    code: str = ""  # max 10 chars, primary key, non-empty
    title: str = ""  # max 40 chars, non-empty
    description: str = ""  # HTML with special markers
