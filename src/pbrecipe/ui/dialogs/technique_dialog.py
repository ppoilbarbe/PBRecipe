from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.constants import MAX_TECHNIQUE_CODE, MAX_TECHNIQUE_TITLE
from pbrecipe.database import Database
from pbrecipe.models import Technique
from pbrecipe.ui.html_editor import HtmlEditor

_log = logging.getLogger(__name__)


class TechniqueEditDialog(QDialog):
    def __init__(
        self,
        technique: Technique,
        db: Database | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._technique = technique
        self._db = db
        self.setWindowTitle("Éditer la technique")
        self.setMinimumSize(600, 400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._code_edit = QLineEdit(self._technique.code)
        self._code_edit.setMaxLength(MAX_TECHNIQUE_CODE)
        form.addRow("Code :", self._code_edit)
        self._title_edit = QLineEdit(self._technique.title)
        self._title_edit.setMaxLength(MAX_TECHNIQUE_TITLE)
        form.addRow("Titre :", self._title_edit)
        root.addLayout(form)
        self._desc_editor = HtmlEditor()
        self._desc_editor.set_html(self._technique.description)
        if self._db is not None:
            recipes = [(r.code, r.name) for r in self._db.list_recipes()]
            images = self._db.list_all_media()
            techniques = [(t.code, t.title) for t in self._db.list_techniques()]
            self._desc_editor.set_references(recipes, images, techniques)
        root.addWidget(self._desc_editor)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        self._technique.code = self._code_edit.text().strip().upper()
        self._technique.title = self._title_edit.text().strip()
        self._technique.description = self._desc_editor.get_html()
        self.accept()

    @property
    def technique(self) -> Technique:
        return self._technique


class TechniqueDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Techniques")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._edit)
        root.addWidget(self._list)

        btn_bar = QHBoxLayout()
        for label, slot in [
            ("Ajouter…", self._add),
            ("Modifier…", self._edit),
            ("Supprimer", self._delete),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_bar.addWidget(btn)
        btn_bar.addStretch()
        root.addLayout(btn_bar)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        root.addWidget(close)

    def _refresh(self) -> None:
        self._list.clear()
        techniques = self._db.list_techniques()
        _log.debug("Techniques : %d chargées", len(techniques))
        for t in techniques:
            item = QListWidgetItem(f"{t.code} — {t.title}")
            item.setData(0x0100, t)
            self._list.addItem(item)

    def _add(self) -> None:
        dlg = TechniqueEditDialog(Technique(), self._db, self)
        if dlg.exec():
            if self._db.get_technique(dlg.technique.code) is not None:
                QMessageBox.warning(
                    self,
                    "Code déjà utilisé",
                    f"Le code « {dlg.technique.code} » est déjà utilisé"
                    " par une autre technique.",
                )
                return
            self._db.save_technique(dlg.technique)
            _log.info(
                "Technique créée : %s — %s", dlg.technique.code, dlg.technique.title
            )
            self._refresh()

    def _edit(self) -> None:
        lw = self._list.currentItem()
        if lw is None:
            return
        t_before: Technique = lw.data(0x0100)
        dlg = TechniqueEditDialog(t_before, self._db, self)
        if dlg.exec():
            if (
                dlg.technique.code != t_before.code
                and self._db.get_technique(dlg.technique.code) is not None
            ):
                QMessageBox.warning(
                    self,
                    "Code déjà utilisé",
                    f"Le code « {dlg.technique.code} » est déjà utilisé"
                    " par une autre technique.",
                )
                return
            self._db.save_technique(dlg.technique)
            _log.info(
                "Technique modifiée : %s — %s", dlg.technique.code, dlg.technique.title
            )
            self._refresh()

    def _delete(self) -> None:
        lw = self._list.currentItem()
        if lw is None:
            return
        t: Technique = lw.data(0x0100)
        reply = QMessageBox.question(
            self, "Confirmer", f"Supprimer la technique « {t.code} » ?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            _log.info("Technique supprimée : %s — %s", t.code, t.title)
            self._db.delete_technique(t.code)
            self._refresh()
