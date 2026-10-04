# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recipe equipment list editor with drag-and-drop reordering."""

from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QWidget

from pbrecipe.constants import MAX_EQUIPMENT_AFFIX, MAX_EQUIPMENT_NAME
from pbrecipe.database import Database
from pbrecipe.models import RecipeEquipment
from pbrecipe.ui._row_list_editor import (
    BaseRow,
    BaseRowListEditor,
    fill_ref_combo,
    make_plural_checkbox,
    make_ref_combo,
)

_NO_EQUIPMENT = "— aucun —"


class EquipmentRow(BaseRow):
    _ADD_TOOLTIP = "Ajouter un matériel après celui-ci"
    _DEL_TOOLTIP = "Supprimer ce matériel"

    def __init__(
        self,
        row: RecipeEquipment,
        equipment: list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._row = row
        layout = self._layout

        self._prefix = QLineEdit(row.prefix)
        self._prefix.setMaxLength(MAX_EQUIPMENT_AFFIX)
        self._prefix.setPlaceholderText("Préfixe")
        layout.addWidget(self._prefix, MAX_EQUIPMENT_AFFIX)

        self._equipment = make_ref_combo(12)
        fill_ref_combo(self._equipment, equipment, row.equipment_id, _NO_EQUIPMENT)
        layout.addWidget(self._equipment, MAX_EQUIPMENT_NAME)

        self._equipment_plural = make_plural_checkbox(
            row.equipment_plural,
            "Pluriel (coché = utiliser la forme plurielle du matériel)",
        )
        layout.addWidget(self._equipment_plural)

        self._suffix = QLineEdit(row.suffix)
        self._suffix.setMaxLength(MAX_EQUIPMENT_AFFIX)
        self._suffix.setPlaceholderText("Suffixe")
        layout.addWidget(self._suffix, MAX_EQUIPMENT_AFFIX)

        self._add_action_buttons()

    def get_data(self, recipe_code: str, position: int) -> RecipeEquipment:
        return RecipeEquipment(
            id=self._row.id,
            recipe_code=recipe_code,
            position=position,
            prefix=self._prefix.text(),
            equipment_id=self._equipment.currentData(),
            suffix=self._suffix.text(),
            equipment_plural=self._equipment_plural.isChecked(),
        )

    def connect_changed(self, slot) -> None:
        self._prefix.textChanged.connect(slot)
        self._equipment.currentIndexChanged.connect(slot)
        self._equipment_plural.stateChanged.connect(slot)
        self._suffix.textChanged.connect(slot)

    def reload(self, equipment: list) -> None:
        fill_ref_combo(
            self._equipment, equipment, self._equipment.currentData(), _NO_EQUIPMENT
        )


class EquipmentListEditor(BaseRowListEditor):
    _HEADER = [
        ("", 20, None),
        ("Préfixe", None, MAX_EQUIPMENT_AFFIX),
        ("Matériel", None, MAX_EQUIPMENT_NAME),
        ("Pl.", 24, None),
        ("Suffixe", None, MAX_EQUIPMENT_AFFIX),
    ]
    _EMPTY_TOOLTIP = "Ajouter un premier matériel"

    def _load_refs(self, db: Database) -> tuple[list]:
        return (db.list_equipment(),)

    def _make_row(self, data, parent: QWidget) -> EquipmentRow:
        (equipment,) = self._refs
        return EquipmentRow(data or RecipeEquipment(), equipment, parent)

    def get_equipment(self, recipe_code: str) -> list[RecipeEquipment]:
        return self.get_items(recipe_code)
