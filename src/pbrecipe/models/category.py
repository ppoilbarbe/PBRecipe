from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Category:
    id: int | None = None
    name: str = ""  # max 20 chars, non-empty
