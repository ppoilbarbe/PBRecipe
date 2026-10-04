# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe ingredient list editor with drag-and-drop reordering."""

from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QWidget

from pbrecipe.constants import (
    MAX_INGREDIENT_AFFIX,
    MAX_INGREDIENT_NAME,
    MAX_INGREDIENT_QUANTITY,
    MAX_UNIT_NAME,
)
from pbrecipe.database import Database
from pbrecipe.models import RecipeIngredient
from pbrecipe.ui._row_list_editor import (
    BaseRow,
    BaseRowListEditor,
    fill_ref_combo,
    make_plural_checkbox,
    make_ref_combo,
)

_NO_INGREDIENT = "— aucun —"


class IngredientRow(BaseRow):
    _ADD_TOOLTIP = "Ajouter un ingrédient après celui-ci"
    _DEL_TOOLTIP = "Supprimer cet ingrédient"

    def __init__(
        self,
        row: RecipeIngredient,
        units: list,
        ingredients: list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._row = row
        layout = self._layout

        self._prefix = QLineEdit(row.prefix)
        self._prefix.setMaxLength(MAX_INGREDIENT_AFFIX)
        self._prefix.setPlaceholderText("Préfixe")
        layout.addWidget(self._prefix, MAX_INGREDIENT_AFFIX)

        self._qty = QLineEdit(row.quantity)
        self._qty.setMaxLength(MAX_INGREDIENT_QUANTITY)
        self._qty.setPlaceholderText("Qté")
        layout.addWidget(self._qty, MAX_INGREDIENT_QUANTITY)

        self._unit = make_ref_combo(8)
        fill_ref_combo(self._unit, units, row.unit_id, "")
        layout.addWidget(self._unit, MAX_UNIT_NAME)

        self._unit_plural = make_plural_checkbox(
            row.unit_plural, "Pluriel (coché = utiliser la forme plurielle de l'unité)"
        )
        layout.addWidget(self._unit_plural)

        self._sep = QLineEdit(row.separator)
        self._sep.setMaxLength(MAX_INGREDIENT_AFFIX)
        self._sep.setPlaceholderText("Sépar.")
        layout.addWidget(self._sep, MAX_INGREDIENT_AFFIX)

        self._ingredient = make_ref_combo(12)
        fill_ref_combo(self._ingredient, ingredients, row.ingredient_id, _NO_INGREDIENT)
        layout.addWidget(self._ingredient, MAX_INGREDIENT_NAME)

        self._ingredient_plural = make_plural_checkbox(
            row.ingredient_plural,
            "Pluriel (coché = utiliser la forme plurielle de l'ingrédient)",
        )
        layout.addWidget(self._ingredient_plural)

        self._suffix = QLineEdit(row.suffix)
        self._suffix.setMaxLength(MAX_INGREDIENT_AFFIX)
        self._suffix.setPlaceholderText("Suffixe")
        layout.addWidget(self._suffix, MAX_INGREDIENT_AFFIX)

        self._add_action_buttons()

    def get_data(self, recipe_code: str, position: int) -> RecipeIngredient:
        return RecipeIngredient(
            id=self._row.id,
            recipe_code=recipe_code,
            position=position,
            prefix=self._prefix.text(),
            quantity=self._qty.text(),
            unit_id=self._unit.currentData(),
            separator=self._sep.text(),
            ingredient_id=self._ingredient.currentData(),
            suffix=self._suffix.text(),
            unit_plural=self._unit_plural.isChecked(),
            ingredient_plural=self._ingredient_plural.isChecked(),
        )

    def connect_changed(self, slot) -> None:
        self._prefix.textChanged.connect(slot)
        self._qty.textChanged.connect(slot)
        self._unit.currentIndexChanged.connect(slot)
        self._unit_plural.stateChanged.connect(slot)
        self._sep.textChanged.connect(slot)
        self._ingredient.currentIndexChanged.connect(slot)
        self._ingredient_plural.stateChanged.connect(slot)
        self._suffix.textChanged.connect(slot)

    def reload(self, units: list, ingredients: list) -> None:
        fill_ref_combo(self._unit, units, self._unit.currentData(), "")
        fill_ref_combo(
            self._ingredient,
            ingredients,
            self._ingredient.currentData(),
            _NO_INGREDIENT,
        )


class IngredientListEditor(BaseRowListEditor):
    _HEADER = [
        ("", 20, None),
        ("Préfixe", None, MAX_INGREDIENT_AFFIX),
        ("Qté", None, MAX_INGREDIENT_QUANTITY),
        ("Unité", None, MAX_UNIT_NAME),
        ("Pl.", 24, None),
        ("Sépar.", None, MAX_INGREDIENT_AFFIX),
        ("Ingrédient", None, MAX_INGREDIENT_NAME),
        ("Pl.", 24, None),
        ("Suffixe", None, MAX_INGREDIENT_AFFIX),
    ]
    _EMPTY_TOOLTIP = "Ajouter un premier ingrédient"

    def _load_refs(self, db: Database) -> tuple[list, list]:
        return db.list_units(), db.list_ingredients()

    def _make_row(self, data, parent: QWidget) -> IngredientRow:
        units, ingredients = self._refs
        return IngredientRow(data or RecipeIngredient(), units, ingredients, parent)

    def get_ingredients(self, recipe_code: str) -> list[RecipeIngredient]:
        return self.get_items(recipe_code)
