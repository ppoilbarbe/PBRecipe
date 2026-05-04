from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Technique:
    code: str = ""  # max 10 chars, primary key, non-empty
    title: str = ""  # max 40 chars, non-empty
    description: str = ""  # HTML with special markers
