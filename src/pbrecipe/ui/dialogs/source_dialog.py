from pbrecipe.models import Source
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


class SourceDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Sources", db, parent)

    def _load_items(self):
        return self._db.list_sources()

    def _make_item(self, name: str):
        return Source(name=name)

    def _save_item(self, item):
        self._db.save_source(item)

    def _delete_item(self, item_id):
        self._db.delete_source(item_id)
