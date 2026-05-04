from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecipeIngredient:
    id: int | None = None
    recipe_code: str = ""
    position: int = 0
    prefix: str = ""  # max 10 chars
    quantity: str = "1"  # max 10 chars
    unit_id: int | None = None
    separator: str = ""  # max 20 chars
    ingredient_id: int | None = None
    suffix: str = ""  # max 20 chars


@dataclass
class RecipeMedia:
    id: int | None = None
    recipe_code: str = ""
    position: int = 0
    code: str = ""  # référence [IMG:CODE] dans description/commentaires
    mime_type: str = "image/jpeg"
    data: bytes = b""


@dataclass
class Recipe:
    code: str = ""  # unique primary key derived from name
    name: str = ""
    difficulty: int = 0  # 0=unknown, 1-3
    serving: str = ""  # max 30 chars, e.g. "6 parts", "3 personnes"
    prep_time: int | None = None  # minutes
    wait_time: int | None = None  # minutes
    cook_time: int | None = None  # minutes
    description: str = ""  # HTML with special markers
    comments: str = ""  # HTML with special markers
    source_id: int | None = None

    categories: list[int] = field(default_factory=list)  # category IDs
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    media: list[RecipeMedia] = field(default_factory=list)

    @property
    def total_time(self) -> int | None:
        if self.prep_time is None and self.wait_time is None and self.cook_time is None:
            return None
        return (self.prep_time or 0) + (self.wait_time or 0) + (self.cook_time or 0)
