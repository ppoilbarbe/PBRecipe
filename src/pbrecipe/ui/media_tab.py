from __future__ import annotations

import mimetypes
import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.models import RecipeMedia

_THUMB_SIZE = 80
_PREVIEW_W = 240
_IMG_FILTER = "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp)"

_MIME_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}


def _code_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^\w]", "_", stem).upper().strip("_")
    if not stem:
        return "IMG"
    tokens = [t for t in stem.split("_") if t]
    result: list[str] = []
    total = 0
    for token in reversed(tokens):
        cost = len(token) + (1 if result else 0)
        if total + cost > 20:
            break
        result.insert(0, token)
        total += cost
    return "_".join(result) or stem[-20:]


def _mime_from_path(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "image/jpeg"


def _pixmap_from_bytes(data: bytes) -> QPixmap:
    px = QPixmap()
    px.loadFromData(data)
    return px


# ---------------------------------------------------------------------------


class _MediaFileDialog(QFileDialog):
    """QFileDialog with an embedded image preview panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, "Sélectionner une image")
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setNameFilter(_IMG_FILTER)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)

        self._preview = QLabel("Aperçu")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumSize(_PREVIEW_W, _PREVIEW_W)
        self._preview.setMaximumWidth(_PREVIEW_W + 20)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self._preview.setStyleSheet(
            "background:#f4f4f4; border:1px solid #ccc; border-radius:3px;"
        )

        grid = self.layout()
        grid.addWidget(self._preview, 0, grid.columnCount(), grid.rowCount(), 1)

        self.currentChanged.connect(self._on_current_changed)

    def _on_current_changed(self, path: str) -> None:
        if not path or not Path(path).is_file():
            self._preview.clear()
            self._preview.setText("Aperçu")
            return
        px = QPixmap(path)
        if px.isNull():
            self._preview.setText("Non prévisualisable")
            return
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

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        files = self.selectedFiles()
        if files:
            self._on_current_changed(files[0])


# ---------------------------------------------------------------------------


class MediaTab(QWidget):
    """Recipe editor tab: list of stored images with thumbnail + full preview."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._media: list[RecipeMedia] = []
        self._current_pixmap: QPixmap | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # ── Left : list + buttons ──────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.setIconSize(QSize(_THUMB_SIZE, _THUMB_SIZE))
        self._list.setSpacing(2)
        self._list.currentRowChanged.connect(self._on_row_changed)
        ll.addWidget(self._list)

        btn_bar = QHBoxLayout()
        self._add_btn = QPushButton("Ajouter…")
        self._del_btn = QPushButton("Supprimer")
        self._export_btn = QPushButton("Exporter…")
        self._up_btn = QPushButton("↑")
        self._down_btn = QPushButton("↓")
        self._up_btn.setFixedWidth(32)
        self._down_btn.setFixedWidth(32)
        self._add_btn.clicked.connect(self._add)
        self._del_btn.clicked.connect(self._remove)
        self._export_btn.clicked.connect(self._export)
        self._up_btn.clicked.connect(self._move_up)
        self._down_btn.clicked.connect(self._move_down)
        for b in (
            self._add_btn,
            self._del_btn,
            self._export_btn,
            self._up_btn,
            self._down_btn,
        ):
            btn_bar.addWidget(b)
        btn_bar.addStretch()
        ll.addLayout(btn_bar)
        splitter.addWidget(left)

        # ── Right : full preview ───────────────────────────────────────
        self._preview = QLabel("Sélectionnez une image")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._preview.setStyleSheet("background:#f0f0f0;")
        splitter.addWidget(self._preview)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, media_list: list[RecipeMedia]) -> None:
        self._media = list(media_list)
        self._rebuild_list()

    def get_media(self, recipe_code: str) -> list[RecipeMedia]:
        for i, m in enumerate(self._media):
            m.recipe_code = recipe_code
            m.position = i
        return list(self._media)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _rebuild_list(self, select_row: int = -1) -> None:
        self._list.clear()
        for m in self._media:
            self._list.addItem(self._make_item(m))
        if select_row >= 0:
            self._list.setCurrentRow(min(select_row, self._list.count() - 1))

    def _make_item(self, media: RecipeMedia) -> QListWidgetItem:
        item = QListWidgetItem(media.code)
        if media.data:
            px = _pixmap_from_bytes(media.data)
            if not px.isNull():
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
        return item

    def _existing_codes(self) -> set[str]:
        return {m.code.upper() for m in self._media}

    def _unique_code(self, base: str) -> str:
        existing = self._existing_codes()
        if base not in existing:
            return base
        root = base[:17]
        i = 2
        while i < 1000:
            candidate = f"{root}_{i}"[:20]
            if candidate not in existing:
                return candidate
            i += 1
        return base

    def _on_row_changed(self, row: int) -> None:
        self._current_pixmap = None
        if 0 <= row < len(self._media) and self._media[row].data:
            px = _pixmap_from_bytes(self._media[row].data)
            if not px.isNull():
                self._current_pixmap = px
                self._refresh_preview()
                return
        self._preview.setPixmap(QPixmap())
        self._preview.setText(
            "Pas d'aperçu disponible" if row >= 0 else "Sélectionnez une image"
        )

    def _refresh_preview(self) -> None:
        if self._current_pixmap is None:
            return
        w = max(self._preview.width() - 8, 1)
        h = max(self._preview.height() - 8, 1)
        self._preview.setPixmap(
            self._current_pixmap.scaled(
                w,
                h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_preview()

    def _add(self) -> None:
        dlg = _MediaFileDialog(self)
        if not dlg.exec():
            return
        files = dlg.selectedFiles()
        if not files:
            return
        path = files[0]

        default_code = self._unique_code(_code_from_filename(path))
        code, ok = QInputDialog.getText(
            self,
            "Code de l'image",
            "Code unique pour référencer cette image dans\n"
            "la description (ex. [IMG:CODE]) :",
            text=default_code,
        )
        if not ok or not code.strip():
            return

        code_upper = code.strip().upper()
        if code_upper in self._existing_codes():
            QMessageBox.warning(
                self,
                "Code déjà utilisé",
                f"Le code « {code_upper} » est déjà utilisé"
                " par une autre image de cette recette.",
            )
            return

        self._media.append(
            RecipeMedia(
                code=code_upper,
                mime_type=_mime_from_path(path),
                data=Path(path).read_bytes(),
            )
        )
        self._rebuild_list(len(self._media) - 1)
        self.changed.emit()

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        self._media.pop(row)
        self._current_pixmap = None
        self._preview.setPixmap(QPixmap())
        self._preview.setText("Sélectionnez une image")
        self._rebuild_list(max(row - 1, 0))
        self.changed.emit()

    def _export(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        media = self._media[row]
        if not media.data:
            return

        ext = _MIME_EXT.get(media.mime_type, "")
        code = media.code or "image"

        name_filter = (
            f"Fichier {media.mime_type} (*{ext})" if ext else "Tous les fichiers (*)"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'image",
            code + ext,
            name_filter,
        )
        if not path:
            return

        p = Path(path)
        if ext and not p.suffix:
            p = Path(path + ext)

        try:
            p.write_bytes(media.data)
        except OSError as e:
            QMessageBox.warning(self, "Erreur d'export", str(e))

    def _move_up(self) -> None:
        row = self._list.currentRow()
        if row <= 0:
            return
        self._media[row - 1], self._media[row] = self._media[row], self._media[row - 1]
        self._rebuild_list(row - 1)
        self.changed.emit()

    def _move_down(self) -> None:
        row = self._list.currentRow()
        if row < 0 or row >= len(self._media) - 1:
            return
        self._media[row], self._media[row + 1] = self._media[row + 1], self._media[row]
        self._rebuild_list(row + 1)
        self.changed.emit()
