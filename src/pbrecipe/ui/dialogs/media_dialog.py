# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Dialog for viewing and batch-managing all recipe media stored in the database."""

from __future__ import annotations

import logging

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.constants import (
    DEFAULT_MEDIA_JPEG_QUALITY,
    DEFAULT_MEDIA_MAX_H,
    DEFAULT_MEDIA_MAX_W,
)
from pbrecipe.database import Database
from pbrecipe.image_utils import scale_to_fit
from pbrecipe.models import RecipeMedia
from pbrecipe.ui.dialogs._geometry_mixin import GeometryMixin

_log = logging.getLogger(__name__)

_THUMB = 64
_COL_THUMB, _COL_CODE, _COL_TYPE, _COL_DIM, _COL_SIZE, _COL_RESIZE, _COL_JPEG = range(7)

_MIME_LABELS: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/gif": "GIF",
    "image/webp": "WebP",
    "image/bmp": "BMP",
    "image/tiff": "TIFF",
    "video/mp4": "MP4",
    "video/quicktime": "MOV",
    "video/webm": "WebM",
}


def _type_label(mime_type: str) -> str:
    if not mime_type:
        return "—"
    return _MIME_LABELS.get(mime_type, mime_type.split("/")[-1].upper())


def _human_size(n: int) -> str:
    for thresh, unit in ((1024**3, "Go"), (1024**2, "Mo"), (1024, "Ko")):
        if n >= thresh:
            return f"{n / thresh:.1f} {unit}"
    return f"{n} o"


def _image_dims(data: bytes) -> tuple[int, int]:
    px = QPixmap()
    px.loadFromData(data)
    return (px.width(), px.height()) if not px.isNull() else (0, 0)


def _to_jpeg(data: bytes, quality: int = -1) -> bytes:
    img = QImage()
    img.loadFromData(QByteArray(data))
    if img.isNull():
        return data
    if img.hasAlphaChannel():
        img = img.convertToFormat(QImage.Format.Format_RGB32)
    buf = QBuffer()
    buf.open(QIODevice.OpenMode.WriteOnly)
    img.save(buf, "JPEG", quality)
    buf.close()
    result = bytes(buf.data())
    return result if result else data


class MediaDialog(GeometryMixin, QDialog):
    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._media: list[RecipeMedia] = []
        g = db.get_globals()
        try:
            self._max_w = int(g.get("media_max_w", DEFAULT_MEDIA_MAX_W))
            self._max_h = int(g.get("media_max_h", DEFAULT_MEDIA_MAX_H))
            self._jpeg_quality = int(
                g.get("media_jpeg_quality", DEFAULT_MEDIA_JPEG_QUALITY)
            )
        except (ValueError, TypeError):
            self._max_w, self._max_h = DEFAULT_MEDIA_MAX_W, DEFAULT_MEDIA_MAX_H
            self._jpeg_quality = DEFAULT_MEDIA_JPEG_QUALITY
        self.setWindowTitle("Gestion des médias")
        self.setMinimumSize(820, 450)
        self._setup_ui()
        self._load()
        self._init_geometry("MediaDialog")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["", "Code", "Type", "Dimensions", "Poids", "Recadrer", "→ JPEG"]
        )
        h = self._table.horizontalHeader()
        h.setSectionResizeMode(_COL_THUMB, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(_COL_CODE, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(_COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(_COL_DIM, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(_COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(_COL_RESIZE, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(_COL_JPEG, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_THUMB, _THUMB + 16)
        self._table.setColumnWidth(_COL_RESIZE, 100)
        self._table.setColumnWidth(_COL_JPEG, 100)
        self._table.setIconSize(QSize(_THUMB, _THUMB))
        self._table.verticalHeader().setDefaultSectionSize(_THUMB + 8)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        root.addWidget(self._table)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        root.addWidget(close_box)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._media = self._db.list_all_media()
        self._table.setRowCount(len(self._media))
        for row, m in enumerate(self._media):
            self._fill_row(row, m)

    def _fill_row(self, row: int, m: RecipeMedia) -> None:
        is_image = m.mime_type.startswith("image/") if m.mime_type else False

        # Thumbnail
        thumb_item = QTableWidgetItem()
        if m.data:
            px = QPixmap()
            px.loadFromData(m.data)
            if not px.isNull():
                thumb_item.setIcon(
                    QIcon(
                        px.scaled(
                            _THUMB,
                            _THUMB,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                )
        self._table.setItem(row, _COL_THUMB, thumb_item)

        # Code
        self._table.setItem(
            row, _COL_CODE, QTableWidgetItem(f"{m.recipe_code}:{m.code}")
        )

        # Type
        type_item = QTableWidgetItem(_type_label(m.mime_type))
        type_item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.setItem(row, _COL_TYPE, type_item)

        # Dimensions
        w, h = _image_dims(m.data) if (m.data and is_image) else (0, 0)
        dim_item = QTableWidgetItem(f"{w} × {h}" if w else "—")
        dim_item.setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.setItem(row, _COL_DIM, dim_item)

        # File size
        size_item = QTableWidgetItem(_human_size(len(m.data)) if m.data else "—")
        size_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.setItem(row, _COL_SIZE, size_item)

        # Resize button
        over_limit = bool(is_image and w and h and (w > self._max_w or h > self._max_h))
        btn_resize = QPushButton("Recadrer")
        btn_resize.setEnabled(over_limit)
        if not is_image:
            btn_resize.setToolTip("Non applicable aux fichiers non-image")
        elif over_limit:
            btn_resize.setToolTip(f"Réduire à {self._max_w} × {self._max_h} px maximum")
        else:
            btn_resize.setToolTip("Déjà dans les limites")
        btn_resize.clicked.connect(lambda _=False, r=row: self._do_resize(r))
        self._table.setCellWidget(row, _COL_RESIZE, btn_resize)

        # JPEG conversion button
        can_jpeg = is_image and m.mime_type != "image/jpeg"
        btn_jpeg = QPushButton("→ JPEG")
        btn_jpeg.setEnabled(can_jpeg)
        if not is_image:
            btn_jpeg.setToolTip("Non applicable aux fichiers non-image")
        elif can_jpeg:
            btn_jpeg.setToolTip("Convertir en JPEG")
        else:
            btn_jpeg.setToolTip("Déjà en JPEG")
        btn_jpeg.clicked.connect(lambda _=False, r=row: self._do_to_jpeg(r))
        self._table.setCellWidget(row, _COL_JPEG, btn_jpeg)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_resize(self, row: int) -> None:
        m = self._media[row]
        new_data = scale_to_fit(
            m.data, self._max_w, self._max_h, m.mime_type, self._jpeg_quality
        )
        if new_data is m.data:
            return
        m.data = new_data
        self._db.save_recipe_media(m)
        _log.info("Média %s:%s recadré", m.recipe_code, m.code)
        self._fill_row(row, m)

    def _do_to_jpeg(self, row: int) -> None:
        m = self._media[row]
        new_data = _to_jpeg(m.data, self._jpeg_quality)
        if not new_data or new_data is m.data:
            return
        m.data = new_data
        m.mime_type = "image/jpeg"
        self._db.save_recipe_media(m)
        _log.info("Média %s:%s converti en JPEG", m.recipe_code, m.code)
        self._fill_row(row, m)
