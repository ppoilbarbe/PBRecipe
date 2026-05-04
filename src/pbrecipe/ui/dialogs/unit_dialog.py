from pbrecipe.models import Unit
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


class UnitDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Unités", db, parent)

    def _load_items(self):
        return self._db.list_units()

    def _make_item(self, name: str):
        return Unit(name=name)

    def _save_item(self, item):
        self._db.save_unit(item)

    def _delete_item(self, item_id):
        self._db.delete_unit(item_id)
