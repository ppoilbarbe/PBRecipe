from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.constants import MAX_DIFFICULTY_LABEL
from pbrecipe.database import Database
from pbrecipe.models import DifficultyLevel

_log = logging.getLogger(__name__)

_THUMB_SIZE = 48
_IMG_FILTER = "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp)"


def _mime_from_path(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "image/jpeg"


def _pixmap_from_bytes(data: bytes) -> QPixmap:
    px = QPixmap()
    px.loadFromData(data)
    return px


class DifficultyDialog(QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._levels: list[DifficultyLevel] = []
        self._current_row: int = -1
        self._loading: bool = False  # bloque les signaux pendant le chargement
        self.setWindowTitle("Niveaux de difficulté")
        self.setMinimumSize(600, 340)
        self._setup_ui()
        self._reload_levels()
        if self._list.count():
            self._list.setCurrentRow(0)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── Liste (gauche) ────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setIconSize(QSize(_THUMB_SIZE, _THUMB_SIZE))
        self._list.setFixedWidth(200)
        self._list.currentRowChanged.connect(self._on_row_changed)
        splitter.addWidget(self._list)

        # ── Panneau d'édition (droite) ────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 4, 4, 4)

        self._level_label = QLabel()
        self._level_label.setStyleSheet("font-weight: bold;")
        rl.addWidget(self._level_label)

        form = QFormLayout()
        self._label_edit = QLineEdit()
        self._label_edit.setMaxLength(MAX_DIFFICULTY_LABEL)
        self._label_edit.setPlaceholderText("(vide pour niveau non défini)")
        self._label_edit.editingFinished.connect(self._save_current)
        form.addRow("Libellé :", self._label_edit)
        rl.addLayout(form)

        # Aperçu de l'icône
        self._preview = QLabel("Aucune icône")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._preview.setStyleSheet(
            "background:#f4f4f4; border:1px solid #ccc; border-radius:3px;"
        )
        self._preview.setMinimumHeight(120)
        rl.addWidget(self._preview)

        img_bar = QHBoxLayout()
        self._btn_load = QPushButton("Charger une image…")
        self._btn_load.clicked.connect(self._load_image)
        self._btn_clear = QPushButton("Supprimer l'icône")
        self._btn_clear.clicked.connect(self._clear_image)
        img_bar.addWidget(self._btn_load)
        img_bar.addWidget(self._btn_clear)
        img_bar.addStretch()
        rl.addLayout(img_bar)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # ── Bouton Fermer ─────────────────────────────────────────────
        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self._on_close)
        root.addWidget(close_box)

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def _reload_levels(self) -> None:
        self._levels = self._db.list_difficulty_levels()
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        current_row = self._list.currentRow()
        self._list.clear()
        for dl in self._levels:
            label = dl.label or "(aucun)" if dl.level == 0 else dl.label
            text = f"{dl.level} — {label}" if label else f"{dl.level}"
            item = QListWidgetItem(text)
            if dl.data:
                px = _pixmap_from_bytes(dl.data)
                if not px.isNull():
                    from PySide6.QtGui import QIcon

                    item.setIcon(
                        QIcon(
                            px.scaled(
                                _THUMB_SIZE,
                                _THUMB_SIZE,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                    )
            self._list.addItem(item)
        if 0 <= current_row < self._list.count():
            self._list.setCurrentRow(current_row)

    def _load_panel(self, dl: DifficultyLevel) -> None:
        self._loading = True
        self._level_label.setText(f"Niveau {dl.level}")
        self._label_edit.setText(dl.label)
        self._refresh_preview(dl)
        self._btn_clear.setEnabled(dl.data is not None)
        self._loading = False

    def _refresh_preview(self, dl: DifficultyLevel) -> None:
        if dl.data:
            px = _pixmap_from_bytes(dl.data)
            if not px.isNull():
                w = max(self._preview.width() - 8, 40)
                h = max(self._preview.height() - 8, 40)
                self._preview.setPixmap(
                    px.scaled(
                        w,
                        h,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self._preview.setText("")
                return
        self._preview.setPixmap(QPixmap())
        self._preview.setText("Aucune icône")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if 0 <= self._current_row < len(self._levels):
            self._refresh_preview(self._levels[self._current_row])

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        if self._loading:
            return
        self._save_current()
        self._current_row = row
        if 0 <= row < len(self._levels):
            self._load_panel(self._levels[row])

    def _save_current(self) -> None:
        if (
            self._loading
            or self._current_row < 0
            or self._current_row >= len(self._levels)
        ):
            return
        dl = self._levels[self._current_row]
        new_label = self._label_edit.text()
        if dl.label != new_label:
            dl.label = new_label
            self._db.save_difficulty_level(dl)
            _log.info("Niveau %d — libellé mis à jour : «%s»", dl.level, dl.label)
            self._rebuild_list()

    def _load_image(self) -> None:
        if self._current_row < 0 or self._current_row >= len(self._levels):
            return
        dlg = QFileDialog(self, "Sélectionner une icône")
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setNameFilter(_IMG_FILTER)
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        if not dlg.exec():
            return
        files = dlg.selectedFiles()
        if not files:
            return
        path = files[0]
        data = Path(path).read_bytes()
        dl = self._levels[self._current_row]
        dl.mime_type = _mime_from_path(path)
        dl.data = data
        self._db.save_difficulty_level(dl)
        _log.info("Niveau %d — icône chargée depuis %s", dl.level, path)
        self._refresh_preview(dl)
        self._btn_clear.setEnabled(True)
        self._rebuild_list()

    def _clear_image(self) -> None:
        if self._current_row < 0 or self._current_row >= len(self._levels):
            return
        dl = self._levels[self._current_row]
        dl.data = None
        self._db.save_difficulty_level(dl)
        _log.info("Niveau %d — icône supprimée", dl.level)
        self._refresh_preview(dl)
        self._btn_clear.setEnabled(False)
        self._rebuild_list()

    def _on_close(self) -> None:
        self._save_current()
        self.reject()
