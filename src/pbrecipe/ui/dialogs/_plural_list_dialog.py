# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generic dialog for reference lists whose items have singular and plural names."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pbrecipe.ui.dialogs._base_list_dialog import BaseListDialog


def plural_name_dialog(
    parent: QWidget,
    title: str,
    max_length: int,
    name: str = "",
    name_plural: str = "",
) -> tuple[str, str, bool]:
    """Ask for a singular and an optional plural name; return (name, plural, ok)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    form = QFormLayout(dlg)
    edit_name = QLineEdit(name)
    edit_name.setMaxLength(max_length)
    edit_plural = QLineEdit(name_plural)
    edit_plural.setMaxLength(max_length)
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


class PluralListDialog(BaseListDialog):
    """Reference list dialog for items with ``name`` and ``name_plural``.

    Subclasses set the class attributes below and implement ``_load_items``,
    ``_make_item``, ``_save_item`` and ``_delete_item``.
    """

    _max_length: int
    _add_title: str
    _edit_title: str

    def _item_name(self, item) -> str:
        if item.name_plural:
            return f"{item.name} / {item.name_plural}"
        return item.name

    def _make_item(self, name: str, name_plural: str = ""):
        raise NotImplementedError

    def _add(self) -> None:
        name, plural, ok = plural_name_dialog(self, self._add_title, self._max_length)
        if ok and name:
            self._save_item(self._make_item(name, plural))
            self._refresh()

    def _edit(self) -> None:
        lw_item = self._list.currentItem()
        if lw_item is None:
            return
        item = lw_item.data(0x0100)
        name, plural, ok = plural_name_dialog(
            self, self._edit_title, self._max_length, item.name, item.name_plural
        )
        if ok and name:
            item.name = name
            item.name_plural = plural
            self._save_item(item)
            self._refresh()
