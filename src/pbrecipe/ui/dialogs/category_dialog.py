from pbrecipe.models import Category
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


class CategoryDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Catégories", db, parent)

    def _load_items(self):
        return self._db.list_categories()

    def _make_item(self, name: str):
        return Category(name=name)

    def _save_item(self, item):
        self._db.save_category(item)

    def _delete_item(self, item_id):
        self._db.delete_category(item_id)
