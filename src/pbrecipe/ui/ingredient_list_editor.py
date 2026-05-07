from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.database import Database
from pbrecipe.models import RecipeIngredient


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


class IngredientRow(QWidget):
    add_after = Signal()
    remove_self = Signal()
    drag_started = Signal()
    drag_moved = Signal(QPoint)
    drag_ended = Signal(QPoint)

    def __init__(
        self,
        row: RecipeIngredient,
        units: list,
        ingredients: list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._row = row
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        handle = _DragHandle()
        handle.drag_started.connect(self.drag_started)
        handle.drag_moved.connect(self.drag_moved)
        handle.drag_ended.connect(self.drag_ended)
        layout.addWidget(handle)

        self._prefix = QLineEdit(row.prefix)
        self._prefix.setMaxLength(10)
        self._prefix.setFixedWidth(70)
        self._prefix.setPlaceholderText("Préfixe")
        layout.addWidget(self._prefix)

        self._qty = QLineEdit(row.quantity)
        self._qty.setMaxLength(10)
        self._qty.setFixedWidth(60)
        self._qty.setPlaceholderText("Qté")
        layout.addWidget(self._qty)

        self._unit = QComboBox()
        self._unit.addItem("", None)
        for u in units:
            self._unit.addItem(u.name, u.id)
            if u.id == row.unit_id:
                self._unit.setCurrentIndex(self._unit.count() - 1)
        self._unit.setFixedWidth(90)
        layout.addWidget(self._unit)

        self._unit_plural = QCheckBox()
        self._unit_plural.setChecked(row.unit_plural)
        self._unit_plural.setFixedWidth(24)
        self._unit_plural.setToolTip(
            "Pluriel (coché = utiliser la forme plurielle de l'unité)"
        )
        layout.addWidget(self._unit_plural)

        self._sep = QLineEdit(row.separator)
        self._sep.setMaxLength(20)
        self._sep.setFixedWidth(90)
        self._sep.setPlaceholderText("Sépar.")
        layout.addWidget(self._sep)

        self._ingredient = QComboBox()
        self._ingredient.addItem("— aucun —", None)
        for ing in ingredients:
            self._ingredient.addItem(ing.name, ing.id)
            if ing.id == row.ingredient_id:
                self._ingredient.setCurrentIndex(self._ingredient.count() - 1)
        self._ingredient.setMinimumWidth(150)
        layout.addWidget(self._ingredient)

        self._ingredient_plural = QCheckBox()
        self._ingredient_plural.setChecked(row.ingredient_plural)
        self._ingredient_plural.setFixedWidth(24)
        self._ingredient_plural.setToolTip(
            "Pluriel (coché = utiliser la forme plurielle de l'ingrédient)"
        )
        layout.addWidget(self._ingredient_plural)

        self._suffix = QLineEdit(row.suffix)
        self._suffix.setMaxLength(20)
        self._suffix.setFixedWidth(90)
        self._suffix.setPlaceholderText("Suffixe")
        layout.addWidget(self._suffix)

        layout.addStretch()

        _action_btn_style = (
            "QPushButton { font-weight: bold; }"
            "QPushButton:focus {"
            "  background-color: palette(highlight);"
            "  color: palette(highlighted-text);"
            "  border: 2px solid palette(highlight);"
            "  outline: none;"
            "}"
        )

        btn_add = QPushButton("+")
        btn_add.setFixedWidth(28)
        btn_add.setStyleSheet(_action_btn_style)
        btn_add.setToolTip("Ajouter un ingrédient après celui-ci")
        btn_add.clicked.connect(self.add_after)
        layout.addWidget(btn_add)

        btn_del = QPushButton("−")
        btn_del.setFixedWidth(28)
        btn_del.setStyleSheet(_action_btn_style)
        btn_del.setToolTip("Supprimer cet ingrédient")
        btn_del.clicked.connect(self.remove_self)
        layout.addWidget(btn_del)

    def get_data(self, recipe_code: str, position: int) -> RecipeIngredient:
        return RecipeIngredient(
            id=self._row.id,
            recipe_code=recipe_code,
            position=position,
            prefix=self._prefix.text(),
            quantity=self._qty.text(),
            unit_id=self._unit.currentData(),
            separator=self._sep.text(),
            ingredient_id=self._ingredient.currentData(),
            suffix=self._suffix.text(),
            unit_plural=self._unit_plural.isChecked(),
            ingredient_plural=self._ingredient_plural.isChecked(),
        )

    def connect_changed(self, slot) -> None:
        self._prefix.textChanged.connect(slot)
        self._qty.textChanged.connect(slot)
        self._unit.currentIndexChanged.connect(slot)
        self._unit_plural.stateChanged.connect(slot)
        self._sep.textChanged.connect(slot)
        self._ingredient.currentIndexChanged.connect(slot)
        self._ingredient_plural.stateChanged.connect(slot)
        self._suffix.textChanged.connect(slot)

    def focus_prefix(self) -> None:
        self._prefix.setFocus()

    def reload(self, units: list, ingredients: list) -> None:
        current_unit_id = self._unit.currentData()
        current_ing_id = self._ingredient.currentData()

        self._unit.blockSignals(True)
        self._unit.clear()
        self._unit.addItem("", None)
        for u in units:
            self._unit.addItem(u.name, u.id)
            if u.id == current_unit_id:
                self._unit.setCurrentIndex(self._unit.count() - 1)
        self._unit.blockSignals(False)

        self._ingredient.blockSignals(True)
        self._ingredient.clear()
        self._ingredient.addItem("— aucun —", None)
        for ing in ingredients:
            self._ingredient.addItem(ing.name, ing.id)
            if ing.id == current_ing_id:
                self._ingredient.setCurrentIndex(self._ingredient.count() - 1)
        self._ingredient.blockSignals(False)


class IngredientListEditor(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[IngredientRow] = []
        self._units: list = []
        self._ingredients: list = []
        self._loading = False
        self._drag_row: IngredientRow | None = None
        self._drag_target_idx: int = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        for label, width in [
            ("", 20),  # drag handle
            ("Préfixe", 70),
            ("Qté", 60),
            ("Unité", 90),
            ("Pl.", 24),
            ("Sépar.", 90),
            ("Ingrédient", 150),
            ("Pl.", 24),
            ("Suffixe", 90),
        ]:
            lbl = QLabel(label)
            lbl.setFixedWidth(width)
            header.addWidget(lbl)
        header.addStretch()
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        self._empty_btn = QPushButton("+")
        self._empty_btn.setFixedWidth(40)
        self._empty_btn.setToolTip("Ajouter un premier ingrédient")
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

    def load(self, ingredients: list[RecipeIngredient], db: Database) -> None:
        self._loading = True
        self._units = db.list_units()
        self._ingredients = db.list_ingredients()
        for row in self._rows:
            row.setParent(None)
        self._rows.clear()
        for ing in ingredients:
            self._insert_at(len(self._rows), ing)
        self._loading = False
        self._update_empty_state()

    def clear(self) -> None:
        self._loading = True
        for row in self._rows:
            row.setParent(None)
        self._rows.clear()
        self._loading = False
        self._update_empty_state()

    def reload(self, db: Database) -> None:
        self._units = db.list_units()
        self._ingredients = db.list_ingredients()
        for row in self._rows:
            row.reload(self._units, self._ingredients)

    def _insert_at(self, idx: int, data: RecipeIngredient | None = None) -> None:
        row = IngredientRow(
            data or RecipeIngredient(),
            self._units,
            self._ingredients,
            self._rows_widget,
        )
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

    def _remove_row(self, row: IngredientRow) -> None:
        self._rows.remove(row)
        row.setParent(None)
        self._update_empty_state()
        self.changed.emit()

    def _move_row_to(self, row: IngredientRow, target_idx: int) -> None:
        """Déplace row à target_idx (index dans la liste sans row)."""
        src = self._rows.index(row)
        if src == target_idx:
            return
        self._rows.pop(src)
        self._rows.insert(target_idx, row)
        self._rows_layout.insertWidget(target_idx + 1, row)
        self.changed.emit()

    # ------------------------------------------------------------------
    # Drag handling
    # ------------------------------------------------------------------

    def _on_drag_start(self, row: IngredientRow) -> None:
        self._drag_row = row
        self._drag_target_idx = self._rows.index(row)
        row.setStyleSheet("background-color: palette(midlight);")

    def _on_drag_move(self, row: IngredientRow, global_pos: QPoint) -> None:
        target = self._drop_target_for_global_y(row, global_pos.y())
        self._drag_target_idx = target
        self._position_indicator(row, target)

    def _on_drag_end(self, row: IngredientRow, _global_pos: QPoint) -> None:
        row.setStyleSheet("")
        self._drop_indicator.hide()
        self._move_row_to(row, self._drag_target_idx)
        self._drag_row = None

    def _drop_target_for_global_y(self, dragging: IngredientRow, global_y: int) -> int:
        """Retourne l'index cible dans la liste sans la ligne en cours de drag."""
        other = [r for r in self._rows if r is not dragging]
        for i, r in enumerate(other):
            mid = r.mapToGlobal(QPoint(0, r.height() // 2)).y()
            if global_y < mid:
                return i
        return len(other)

    def _position_indicator(self, dragging: IngredientRow, target_idx: int) -> None:
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

    def _update_empty_state(self) -> None:
        self._empty_btn.setVisible(len(self._rows) == 0)

    def get_ingredients(self, recipe_code: str) -> list[RecipeIngredient]:
        return [r.get_data(recipe_code, i) for i, r in enumerate(self._rows)]
