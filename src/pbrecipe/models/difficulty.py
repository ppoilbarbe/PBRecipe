from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DifficultyLevel:
    level: int
    label: str = ""
    mime_type: str = "image/jpeg"
    data: bytes | None = field(default=None, repr=False)
