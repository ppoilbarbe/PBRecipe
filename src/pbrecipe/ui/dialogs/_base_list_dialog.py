"""Generic dialog for managing a flat list of named items (categories, units, …)."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.database import Database

_log = logging.getLogger(__name__)


class BaseListDialog(QDialog):
    def __init__(
        self,
        title: str,
        db: Database,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._edit)
        root.addWidget(self._list)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Ajouter…")
        self._btn_add.clicked.connect(self._add)
        self._btn_edit = QPushButton("Modifier…")
        self._btn_edit.clicked.connect(self._edit)
        self._btn_del = QPushButton("Supprimer")
        self._btn_del.clicked.connect(self._delete)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_del)
        btn_bar.addStretch()
        root.addLayout(btn_bar)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.reject)
        root.addWidget(close_btn)

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _load_items(self) -> list:
        raise NotImplementedError

    def _item_name(self, item) -> str:
        return item.name

    def _item_id(self, item) -> int | str:
        return item.id

    def _save_item(self, item) -> None:
        raise NotImplementedError

    def _delete_item(self, item_id) -> None:
        raise NotImplementedError

    def _make_item(self, name: str):
        raise NotImplementedError

    def _update_item_name(self, item, name: str):
        item.name = name

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._list.clear()
        items = self._load_items()
        _log.debug("%s : %d éléments", self.windowTitle(), len(items))
        for item in items:
            lw_item = QListWidgetItem(self._item_name(item))
            lw_item.setData(0x0100, item)
            self._list.addItem(lw_item)

    def _add(self) -> None:
        name, ok = QInputDialog.getText(self, "Ajouter", "Nom :")
        if ok and name.strip():
            item = self._make_item(name.strip())
            self._save_item(item)
            _log.info("%s — créé : «%s»", self.windowTitle(), name.strip())
            self._refresh()

    def _edit(self) -> None:
        lw_item = self._list.currentItem()
        if lw_item is None:
            return
        item = lw_item.data(0x0100)
        old_name = self._item_name(item)
        name, ok = QInputDialog.getText(self, "Modifier", "Nom :", text=old_name)
        if ok and name.strip():
            self._update_item_name(item, name.strip())
            self._save_item(item)
            _log.info(
                "%s — modifié : «%s» → «%s»", self.windowTitle(), old_name, name.strip()
            )
            self._refresh()

    def _delete(self) -> None:
        lw_item = self._list.currentItem()
        if lw_item is None:
            return
        item = lw_item.data(0x0100)
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer « {self._item_name(item)} » ?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            _log.info("%s — supprimé : «%s»", self.windowTitle(), self._item_name(item))
            self._delete_item(self._item_id(item))
            self._refresh()
