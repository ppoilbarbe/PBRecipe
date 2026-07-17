# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for managing recipe sources (books, websites, people, …)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pbrecipe.constants import MAX_SOURCE_SHORTCUT
from pbrecipe.models import Source
from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


def _source_dialog(
    parent: QWidget,
    title: str,
    name: str = "",
    shortcut: str = "",
) -> tuple[str, str, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    form = QFormLayout(dlg)
    edit_name = QLineEdit(name)
    edit_shortcut = QLineEdit(shortcut)
    edit_shortcut.setMaxLength(MAX_SOURCE_SHORTCUT)
    edit_shortcut.setPlaceholderText("Optionnel — affiché à la place du texte complet")
    form.addRow("Texte :", edit_name)
    form.addRow("Raccourci :", edit_shortcut)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    form.addRow(buttons)
    edit_name.setFocus()
    ok = dlg.exec() == QDialog.DialogCode.Accepted
    return edit_name.text().strip(), edit_shortcut.text().strip(), ok


class SourceDialog(BaseListDialog):
    def __init__(self, db, parent=None):
        super().__init__("Sources", db, parent=parent)

    def _load_items(self):
        return self._db.list_sources()

    def _make_item(self, name: str):
        return Source(name=name)

    def _save_item(self, item):
        self._db.save_source(item)

    def _delete_item(self, item_id):
        self._db.delete_source(item_id)

    def _add(self) -> None:
        name, shortcut, ok = _source_dialog(self, "Ajouter une source")
        if ok and name:
            item = Source(name=name, shortcut=shortcut)
            self._save_item(item)
            self._refresh()

    def _edit(self) -> None:
        lw_item = self._list.currentItem()
        if lw_item is None:
            return
        item: Source = lw_item.data(0x0100)
        name, shortcut, ok = _source_dialog(
            self, "Modifier la source", item.name, item.shortcut
        )
        if ok and name:
            item.name = name
            item.shortcut = shortcut
            self._save_item(item)
            self._refresh()
