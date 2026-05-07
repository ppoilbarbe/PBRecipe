from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pbrecipe.models import Unit
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


def _plural_dialog(
    parent: QWidget,
    title: str,
    name: str = "",
    name_plural: str = "",
) -> tuple[str, str, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    form = QFormLayout(dlg)
    edit_name = QLineEdit(name)
    edit_name.setMaxLength(15)
    edit_plural = QLineEdit(name_plural)
    edit_plural.setMaxLength(15)
    edit_plural.setPlaceholderText("(identique au singulier si vide)")
    form.addRow("Singulier :", edit_name)
    form.addRow("Pluriel :", edit_plural)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    form.addRow(buttons)
    edit_name.setFocus()
    ok = dlg.exec() == QDialog.DialogCode.Accepted
    return edit_name.text().strip(), edit_plural.text().strip(), ok


class UnitDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Unités", db, parent)

    def _load_items(self):
        return self._db.list_units()

    def _item_name(self, item) -> str:
        if item.name_plural:
            return f"{item.name} / {item.name_plural}"
        return item.name

    def _make_item(self, name: str):
        return Unit(name=name)

    def _save_item(self, item):
        self._db.save_unit(item)

    def _delete_item(self, item_id):
        self._db.delete_unit(item_id)

    def _add(self) -> None:
        name, plural, ok = _plural_dialog(self, "Ajouter une unité")
        if ok and name:
            item = Unit(name=name, name_plural=plural)
            self._save_item(item)
            self._refresh()

    def _edit(self) -> None:
        lw_item = self._list.currentItem()
        if lw_item is None:
            return
        item: Unit = lw_item.data(0x0100)
        name, plural, ok = _plural_dialog(
            self, "Modifier l'unité", item.name, item.name_plural
        )
        if ok and name:
            item.name = name
            item.name_plural = plural
            self._save_item(item)
            self._refresh()
