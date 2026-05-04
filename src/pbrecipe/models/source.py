from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Source:
    id: int | None = None
    name: str = ""  # max 100 chars, non-empty
