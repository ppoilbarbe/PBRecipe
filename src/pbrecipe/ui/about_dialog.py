# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""About dialog: displays the application version and credits."""

from __future__ import annotations

import sys
from pathlib import Path

import PySide6
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from pbrecipe import __version__

_APP_VERSION = __version__

_APP_AUTHOR = "Philippe Poilbarbe"

_PY_VERSION = sys.version.split()[0]
_QT_VERSION = PySide6.__version__

_ICON_PATH = (
    Path(__file__).parent.parent / "resources" / "icons" / "pbrecipe-128x128.png"
)


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("À propos de PBRecipe")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Icône + titre ──────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        icon_label = QLabel()
        if _ICON_PATH.exists():
            px = QPixmap(str(_ICON_PATH)).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(px)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(icon_label)

        title = QLabel(
            "<h2 style='margin:0'>PBRecipe</h2>"
            f"<p style='margin:2px 0 0 0'>Version {_APP_VERSION}</p>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        header.addWidget(title, stretch=1)

        layout.addLayout(header)

        # ── Informations ───────────────────────────────────────────────
        info = QLabel(
            "<p>Gestionnaire de recettes avec export web PHP.</p>"
            f"<p><b>Auteur :</b> {_APP_AUTHOR}<br>"
            "<b>Licences :</b><br>"
            "&nbsp;· Application Python : GNU GPL v3<br>"
            "&nbsp;· Interface web PHP : GNU AGPL v3<br>"
            "&nbsp;· Icônes : CC BY-NC-SA 4.0</p>"
            "<p><a href='https://github.com/ppoilbarbe/PBRecipe'>"
            "github.com/ppoilbarbe/PBRecipe</a></p>"
        )
        info.setOpenExternalLinks(True)
        info.setWordWrap(True)
        layout.addWidget(info)

        # ── Infos techniques ───────────────────────────────────────────
        sep = QLabel("<hr>")
        layout.addWidget(sep)

        tech = QLabel(
            f"<b>Python</b> {_PY_VERSION} &nbsp;·&nbsp; <b>PySide6</b> {_QT_VERSION}"
        )
        tech.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tech)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)
