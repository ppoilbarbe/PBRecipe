from pbrecipe.models import Ingredient
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


class IngredientDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Ingrédients", db, parent)

    def _load_items(self):
        return self._db.list_ingredients()

    def _make_item(self, name: str):
        return Ingredient(name=name)

    def _save_item(self, item):
        self._db.save_ingredient(item)

    def _delete_item(self, item_id):
        self._db.delete_ingredient(item_id)
