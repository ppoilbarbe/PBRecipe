# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared machinery for the recipe row editors (ingredients, equipment).

A row editor is a scrollable list of rows, each with a drag handle on the left,
item-specific fields, and +/− buttons on the right. Rows are reordered by
dragging the handle.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.database import Database

_ACTION_BTN_STYLE = (
    "QPushButton { font-weight: bold; }"
    "QPushButton:focus {"
    "  background-color: palette(highlight);"
    "  color: palette(highlighted-text);"
    "  border: 2px solid palette(highlight);"
    "  outline: none;"
    "}"
)


class _DragHandle(QLabel):
    _THRESHOLD = 5

    drag_started = Signal()
    drag_moved = Signal(QPoint)
    drag_ended = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("⠿", parent)
        self.setFixedWidth(20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Glisser pour réordonner")
        self._pressing = False
        self._dragging = False
        self._press_pos = QPoint()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressing = True
            self._dragging = False
            self._press_pos = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pressing:
            pos = event.globalPosition().toPoint()
            if not self._dragging:
                if (pos - self._press_pos).manhattanLength() >= self._THRESHOLD:
                    self._dragging = True
                    self.drag_started.emit()
            if self._dragging:
                self.drag_moved.emit(pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._pressing:
            self._pressing = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self._dragging:
                self._dragging = False
                self.drag_ended.emit(event.globalPosition().toPoint())
        super().mouseReleaseEvent(event)


# ----------------------------------------------------------------------
# Field helpers
# ----------------------------------------------------------------------


def make_ref_combo(min_contents: int) -> QComboBox:
    """Combo for a reference item (unit, ingredient, equipment)."""
    combo = QComboBox()
    # Évite AdjustToContentsOnFirstShow (défaut) : sur une base à des
    # centaines/milliers d'éléments, mesurer chaque item au premier affichage
    # de chaque ligne rendait le changement de recette perceptiblement lent.
    # La largeur réelle est de toute façon pilotée par le stretch du layout.
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    combo.setMinimumContentsLength(min_contents)
    return combo


def fill_ref_combo(
    combo: QComboBox, items: list, current_id: int | None, none_label: str
) -> None:
    """(Re)fill *combo* with *items* (``id``/``name``), selecting *current_id*.

    Signals are blocked so that refilling does not mark the recipe as modified.
    """
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(none_label, None)
    for item in items:
        combo.addItem(item.name, item.id)
        if item.id == current_id:
            combo.setCurrentIndex(combo.count() - 1)
    combo.blockSignals(False)


def make_plural_checkbox(checked: bool, tooltip: str) -> QCheckBox:
    box = QCheckBox()
    box.setChecked(checked)
    box.setFixedWidth(24)
    box.setToolTip(tooltip)
    return box


# ----------------------------------------------------------------------
# Row and list base classes
# ----------------------------------------------------------------------


class BaseRow(QWidget):
    """One editable row: drag handle, fields added by the subclass, +/− buttons.

    Subclass ``__init__`` calls ``super().__init__()``, adds its fields to
    ``self._layout`` (``self._prefix`` being the first focusable one), then
    calls ``self._add_action_buttons()``. Subclasses also implement
    ``get_data``, ``connect_changed`` and ``reload``.
    """

    add_after = Signal()
    remove_self = Signal()
    drag_started = Signal()
    drag_moved = Signal(QPoint)
    drag_ended = Signal(QPoint)

    _ADD_TOOLTIP = ""
    _DEL_TOOLTIP = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 2, 0, 2)

        handle = _DragHandle()
        handle.drag_started.connect(self.drag_started)
        handle.drag_moved.connect(self.drag_moved)
        handle.drag_ended.connect(self.drag_ended)
        self._layout.addWidget(handle)

    def _add_action_buttons(self) -> None:
        btn_add = QPushButton("+")
        btn_add.setFixedWidth(28)
        btn_add.setStyleSheet(_ACTION_BTN_STYLE)
        btn_add.setToolTip(self._ADD_TOOLTIP)
        btn_add.clicked.connect(self.add_after)
        self._layout.addWidget(btn_add)

        btn_del = QPushButton("−")
        btn_del.setFixedWidth(28)
        btn_del.setStyleSheet(_ACTION_BTN_STYLE)
        btn_del.setToolTip(self._DEL_TOOLTIP)
        btn_del.clicked.connect(self.remove_self)
        self._layout.addWidget(btn_del)

    def get_data(self, recipe_code: str, position: int):
        raise NotImplementedError

    def connect_changed(self, slot) -> None:
        raise NotImplementedError

    def reload(self, *refs: list) -> None:
        raise NotImplementedError

    def focus_prefix(self) -> None:
        self._prefix.setFocus()


class BaseRowListEditor(QWidget):
    """Scrollable list of ``BaseRow`` with insertion, removal and drag-and-drop.

    Subclasses set ``_HEADER`` (``(label, fixed_width, stretch)`` tuples, the
    drag-handle column included) and ``_EMPTY_TOOLTIP``, and implement
    ``_load_refs`` and ``_make_row``.
    """

    changed = Signal()

    _HEADER: list[tuple[str, int | None, int | None]] = []
    _EMPTY_TOOLTIP = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[BaseRow] = []
        self._refs: tuple[list, ...] = ()
        self._loading = False
        self._drag_row: BaseRow | None = None
        self._drag_target_idx: int = 0
        self._setup_ui()

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    def _load_refs(self, db: Database) -> tuple[list, ...]:
        """Return the reference lists passed to each row (e.g. units, ingredients)."""
        raise NotImplementedError

    def _make_row(self, data, parent: QWidget) -> BaseRow:
        """Build a row for *data*, or for a new empty item if *data* is None."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        for label, fixed_w, stretch in self._HEADER:
            lbl = QLabel(label)
            if fixed_w is not None:
                lbl.setFixedWidth(fixed_w)
            header.addWidget(lbl, stretch or 0)
        header.addSpacing(28 + 28)  # réserve l'espace des boutons +/−
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        self._empty_btn = QPushButton("+")
        self._empty_btn.setFixedWidth(40)
        self._empty_btn.setToolTip(self._EMPTY_TOOLTIP)
        self._empty_btn.clicked.connect(lambda: self._insert_at(0))
        self._rows_layout.addWidget(self._empty_btn)

        self._rows_layout.addStretch()
        scroll.setWidget(self._rows_widget)
        root.addWidget(scroll)

        # Overlay indicator shown during drag (not in layout, positioned manually)
        self._drop_indicator = QFrame(self._rows_widget)
        self._drop_indicator.setFixedHeight(2)
        self._drop_indicator.setStyleSheet("background: palette(highlight);")
        self._drop_indicator.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._drop_indicator.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, items: list, db: Database) -> None:
        self._loading = True
        self._refs = self._load_refs(db)
        for row in self._rows:
            self._discard_row(row)
        self._rows.clear()
        for item in items:
            self._insert_at(len(self._rows), item)
        self._loading = False
        self._update_empty_state()

    def clear(self) -> None:
        self._loading = True
        for row in self._rows:
            self._discard_row(row)
        self._rows.clear()
        self._loading = False
        self._update_empty_state()

    def reload(self, db: Database) -> None:
        """Refresh reference lists in every row without losing entered values."""
        self._refs = self._load_refs(db)
        for row in self._rows:
            row.reload(*self._refs)

    def get_items(self, recipe_code: str) -> list:
        return [r.get_data(recipe_code, i) for i, r in enumerate(self._rows)]

    # ------------------------------------------------------------------
    # Rows
    # ------------------------------------------------------------------

    def _discard_row(self, row: BaseRow) -> None:
        self._rows_layout.removeWidget(row)
        row.hide()
        row.deleteLater()

    def _insert_at(self, idx: int, data=None) -> None:
        row = self._make_row(data, self._rows_widget)
        # Layout: [_empty_btn(0), row0(1), row1(2), ..., stretch(last)]
        self._rows_layout.insertWidget(idx + 1, row)
        self._rows.insert(idx, row)
        row.connect_changed(self.changed)
        row.add_after.connect(lambda r=row: self._insert_at(self._rows.index(r) + 1))
        row.remove_self.connect(lambda r=row: self._remove_row(r))
        row.drag_started.connect(lambda r=row: self._on_drag_start(r))
        row.drag_moved.connect(lambda pos, r=row: self._on_drag_move(r, pos))
        row.drag_ended.connect(lambda pos, r=row: self._on_drag_end(r, pos))
        if not self._loading:
            self._update_empty_state()
            self.changed.emit()
            row.focus_prefix()

    def _remove_row(self, row: BaseRow) -> None:
        self._rows.remove(row)
        self._discard_row(row)
        self._update_empty_state()
        self.changed.emit()

    def _move_row_to(self, row: BaseRow, target_idx: int) -> None:
        """Déplace row à target_idx (index dans la liste sans row)."""
        src = self._rows.index(row)
        if src == target_idx:
            return
        self._rows.pop(src)
        self._rows.insert(target_idx, row)
        self._rows_layout.insertWidget(target_idx + 1, row)
        self.changed.emit()

    def _update_empty_state(self) -> None:
        self._empty_btn.setVisible(len(self._rows) == 0)

    # ------------------------------------------------------------------
    # Drag handling
    # ------------------------------------------------------------------

    def _on_drag_start(self, row: BaseRow) -> None:
        self._drag_row = row
        self._drag_target_idx = self._rows.index(row)
        row.setStyleSheet("background-color: palette(midlight);")

    def _on_drag_move(self, row: BaseRow, global_pos: QPoint) -> None:
        target = self._drop_target_for_global_y(row, global_pos.y())
        self._drag_target_idx = target
        self._position_indicator(row, target)

    def _on_drag_end(self, row: BaseRow, _global_pos: QPoint) -> None:
        row.setStyleSheet("")
        self._drop_indicator.hide()
        self._move_row_to(row, self._drag_target_idx)
        self._drag_row = None

    def _drop_target_for_global_y(self, dragging: BaseRow, global_y: int) -> int:
        """Retourne l'index cible dans la liste sans la ligne en cours de drag."""
        other = [r for r in self._rows if r is not dragging]
        for i, r in enumerate(other):
            mid = r.mapToGlobal(QPoint(0, r.height() // 2)).y()
            if global_y < mid:
                return i
        return len(other)

    def _position_indicator(self, dragging: BaseRow, target_idx: int) -> None:
        other = [r for r in self._rows if r is not dragging]
        if not other:
            self._drop_indicator.hide()
            return

        if target_idx == 0:
            ref = other[0]
            local = self._rows_widget.mapFromGlobal(ref.mapToGlobal(QPoint(0, 0)))
        else:
            ref = other[target_idx - 1]
            local = self._rows_widget.mapFromGlobal(
                ref.mapToGlobal(QPoint(0, ref.height()))
            )

        self._drop_indicator.setGeometry(0, local.y() - 1, self._rows_widget.width(), 2)
        self._drop_indicator.show()
        self._drop_indicator.raise_()
