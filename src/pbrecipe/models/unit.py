from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Unit:
    id: int | None = None
    name: str = ""  # max 15 chars, may be empty
    name_plural: str = ""  # max 15 chars, optional plural form
