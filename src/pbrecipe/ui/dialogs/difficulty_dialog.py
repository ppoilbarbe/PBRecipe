# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for managing difficulty levels: labels, icons and level count."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
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
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.constants import (
    DEFAULT_DIFF_IMG_MAX_H,
    DEFAULT_DIFF_IMG_MAX_W,
    MAX_DIFFICULTY_COUNT,
    MAX_DIFFICULTY_LABEL,
    MIN_DIFFICULTY_COUNT,
)
from pbrecipe.database import Database
from pbrecipe.image_utils import scale_to_fit
from pbrecipe.models import DifficultyLevel
from pbrecipe.ui.dialogs._geometry_mixin import GeometryMixin

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


class DifficultyDialog(GeometryMixin, QDialog):
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
        self._init_geometry("DifficultyDialog")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Nombre de niveaux :"))
        self._count_spin = QSpinBox()
        self._count_spin.setRange(MIN_DIFFICULTY_COUNT, MAX_DIFFICULTY_COUNT)
        self._count_spin.valueChanged.connect(self._on_count_changed)
        count_row.addWidget(self._count_spin)
        count_row.addStretch()
        root.addLayout(count_row)

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
        self._hide_label_cb = QCheckBox(
            "Masquer le libellé (infobulle au survol de l'icône)"
        )
        self._hide_label_cb.stateChanged.connect(self._save_current)
        form.addRow("", self._hide_label_cb)
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

        self._resolution_label = QLabel()
        self._resolution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resolution_label.setStyleSheet("color: #888;")
        rl.addWidget(self._resolution_label)

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
        count = max(
            (dl.level for dl in self._levels if dl.level > 0),
            default=MIN_DIFFICULTY_COUNT,
        )
        self._count_spin.blockSignals(True)
        self._count_spin.setValue(count)
        self._count_spin.blockSignals(False)
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
        self._hide_label_cb.setChecked(dl.hide_label)
        self._refresh_preview(dl)
        self._btn_clear.setEnabled(dl.data is not None)
        self._loading = False

    def _refresh_preview(self, dl: DifficultyLevel) -> None:
        if dl.data:
            px = _pixmap_from_bytes(dl.data)
            if not px.isNull():
                self._resolution_label.setText(f"{px.width()} × {px.height()} px")
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
        self._resolution_label.setText("")
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
        new_hide = self._hide_label_cb.isChecked()
        if dl.label != new_label or dl.hide_label != new_hide:
            dl.label = new_label
            dl.hide_label = new_hide
            self._db.save_difficulty_level(dl)
            _log.info(
                "Niveau %d — libellé mis à jour : «%s» (masqué=%s)",
                dl.level,
                dl.label,
                dl.hide_label,
            )
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
        mime = _mime_from_path(path)
        data = Path(path).read_bytes()
        globals_data = self._db.get_globals()
        try:
            max_w = int(globals_data.get("diff_img_max_w", DEFAULT_DIFF_IMG_MAX_W))
            max_h = int(globals_data.get("diff_img_max_h", DEFAULT_DIFF_IMG_MAX_H))
        except (ValueError, TypeError):
            max_w, max_h = DEFAULT_DIFF_IMG_MAX_W, DEFAULT_DIFF_IMG_MAX_H
        data = scale_to_fit(data, max_w, max_h, mime)
        dl = self._levels[self._current_row]
        dl.mime_type = mime
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

    def _on_count_changed(self, new_count: int) -> None:
        current_count = max(
            (dl.level for dl in self._levels if dl.level > 0), default=0
        )
        if new_count > current_count:
            for lvl in range(current_count + 1, new_count + 1):
                self._db.save_difficulty_level(DifficultyLevel(level=lvl, label=""))
                _log.info("Niveau %d ajouté", lvl)
        elif new_count < current_count:
            for lvl in range(current_count, new_count, -1):
                self._db.delete_difficulty_level(lvl)
                _log.info("Niveau %d supprimé", lvl)
        self._reload_levels()
        if self._list.count():
            self._list.setCurrentRow(min(self._current_row, self._list.count() - 1))

    def _on_close(self) -> None:
        self._save_current()
        self.reject()
