# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resizable dialog showing a single image scaled to fit the window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QSizePolicy, QVBoxLayout, QWidget

from pbrecipe.ui.dialogs._geometry_mixin import GeometryMixin


class ImagePreviewDialog(GeometryMixin, QDialog):
    """Show a single image at full size, scaled to fit the (resizable) window."""

    def __init__(
        self, pixmap: QPixmap, title: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._pixmap = pixmap
        self.setWindowTitle(title or "Aperçu de l'image")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background:#000;")
        self._label.setMinimumSize(1, 1)
        self._label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        layout.addWidget(self._label)

        self.resize(min(pixmap.width(), 1000) or 400, min(pixmap.height(), 800) or 300)
        self._init_geometry("ImagePreviewDialog")
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap.isNull():
            return
        w = max(self._label.width(), 1)
        h = max(self._label.height(), 1)
        self._label.setPixmap(
            self._pixmap.scaled(
                w,
                h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()
