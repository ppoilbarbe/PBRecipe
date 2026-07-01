# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Data model for a difficulty level with optional label and icon image."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DifficultyLevel:
    level: int
    label: str = ""
    hide_label: bool = False
    mime_type: str = "image/jpeg"
    data: bytes | None = field(default=None, repr=False)
