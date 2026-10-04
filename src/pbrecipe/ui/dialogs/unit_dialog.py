# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for managing measurement units with singular and plural forms."""

from pbrecipe.constants import MAX_UNIT_NAME
from pbrecipe.models import Unit
from pbrecipe.ui.dialogs._plural_list_dialog import PluralListDialog


class UnitDialog(PluralListDialog):
    _max_length = MAX_UNIT_NAME
    _add_title = "Ajouter une unité"
    _edit_title = "Modifier l'unité"

    def __init__(self, db, parent=None):
        super().__init__("Unités", db, parent=parent)

    def _load_items(self):
        return self._db.list_units()

    def _make_item(self, name: str, name_plural: str = ""):
        return Unit(name=name, name_plural=name_plural)

    def _save_item(self, item):
        self._db.save_unit(item)

    def _delete_item(self, item_id):
        self._db.delete_unit(item_id)
