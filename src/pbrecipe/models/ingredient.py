from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Ingredient:
    id: int | None = None
    name: str = ""  # max 50 chars, non-empty
