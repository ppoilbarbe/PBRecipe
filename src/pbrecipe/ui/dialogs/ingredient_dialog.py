# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for managing ingredients with singular and plural forms."""

from pbrecipe.constants import MAX_INGREDIENT_NAME
from pbrecipe.models import Ingredient
from pbrecipe.ui.dialogs._plural_list_dialog import PluralListDialog


class IngredientDialog(PluralListDialog):
    _max_length = MAX_INGREDIENT_NAME
    _add_title = "Ajouter un ingrédient"
    _edit_title = "Modifier l'ingrédient"

    def __init__(self, db, parent=None):
        super().__init__("Ingrédients", db, parent=parent)

    def _load_items(self):
        return self._db.list_ingredients()

    def _make_item(self, name: str, name_plural: str = ""):
        return Ingredient(name=name, name_plural=name_plural)

    def _save_item(self, item):
        self._db.save_ingredient(item)

    def _delete_item(self, item_id):
        self._db.delete_ingredient(item_id)
