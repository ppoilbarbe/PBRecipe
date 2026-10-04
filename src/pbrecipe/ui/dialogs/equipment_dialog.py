# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for managing the known kitchen equipment with singular and plural forms."""

from pbrecipe.constants import MAX_EQUIPMENT_NAME
from pbrecipe.models import Equipment
from pbrecipe.ui.dialogs._plural_list_dialog import PluralListDialog


class EquipmentDialog(PluralListDialog):
    _max_length = MAX_EQUIPMENT_NAME
    _add_title = "Ajouter un matériel"
    _edit_title = "Modifier le matériel"

    def __init__(self, db, parent=None):
        super().__init__("Matériel", db, parent=parent)

    def _load_items(self):
        return self._db.list_equipment()

    def _make_item(self, name: str, name_plural: str = ""):
        return Equipment(name=name, name_plural=name_plural)

    def _save_item(self, item):
        self._db.save_equipment(item)

    def _delete_item(self, item_id):
        self._db.delete_equipment(item_id)
