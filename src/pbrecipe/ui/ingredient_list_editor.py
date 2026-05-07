from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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


class IngredientRow(QWidget):
    move_up = Signal()
    move_down = Signal()
    add_after = Signal()
    remove_self = Signal()

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

        self._btn_up = QPushButton("↑")
        self._btn_up.setFixedWidth(28)
        self._btn_up.clicked.connect(self.move_up)
        layout.addWidget(self._btn_up)

        self._btn_down = QPushButton("↓")
        self._btn_down.setFixedWidth(28)
        self._btn_down.clicked.connect(self.move_down)
        layout.addWidget(self._btn_down)

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
        btn_add.clicked.connect(self.add_after)
        layout.addWidget(btn_add)

        btn_del = QPushButton("−")
        btn_del.setFixedWidth(28)
        btn_del.setStyleSheet(_action_btn_style)
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
        )

    def connect_changed(self, slot) -> None:
        self._prefix.textChanged.connect(slot)
        self._qty.textChanged.connect(slot)
        self._unit.currentIndexChanged.connect(slot)
        self._sep.textChanged.connect(slot)
        self._ingredient.currentIndexChanged.connect(slot)
        self._suffix.textChanged.connect(slot)

    def focus_prefix(self) -> None:
        self._prefix.setFocus()

    def set_move_buttons(self, up_enabled: bool, down_enabled: bool) -> None:
        self._btn_up.setEnabled(up_enabled)
        self._btn_down.setEnabled(down_enabled)

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
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        # Header labels aligned with row columns
        header = QHBoxLayout()
        for label, width in [
            ("", 28),  # ↑
            ("", 28),  # ↓
            ("Préfixe", 70),
            ("Qté", 60),
            ("Unité", 90),
            ("Sépar.", 90),
            ("Ingrédient", 150),
            ("Suffixe", 90),
        ]:
            lbl = QLabel(label)
            lbl.setFixedWidth(width)
            header.addWidget(lbl)
        header.addStretch()
        root.addLayout(header)

        # Scrollable rows area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)

        # Empty-state button (index 0, hidden when rows exist)
        self._empty_btn = QPushButton("+")
        self._empty_btn.setFixedWidth(40)
        self._empty_btn.clicked.connect(lambda: self._insert_at(0))
        self._rows_layout.addWidget(self._empty_btn)

        self._rows_layout.addStretch()
        scroll.setWidget(self._rows_widget)
        root.addWidget(scroll)

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
        self._update_move_buttons()
        self._update_empty_state()

    def clear(self) -> None:
        self._loading = True
        for row in self._rows:
            row.setParent(None)
        self._rows.clear()
        self._loading = False
        self._update_move_buttons()
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
        row.move_up.connect(lambda r=row: self._move_row(r, -1))
        row.move_down.connect(lambda r=row: self._move_row(r, 1))
        row.add_after.connect(lambda r=row: self._insert_at(self._rows.index(r) + 1))
        row.remove_self.connect(lambda r=row: self._remove_row(r))
        if not self._loading:
            self._update_move_buttons()
            self._update_empty_state()
            self.changed.emit()
            row.focus_prefix()

    def _remove_row(self, row: IngredientRow) -> None:
        self._rows.remove(row)
        row.setParent(None)
        self._update_move_buttons()
        self._update_empty_state()
        self.changed.emit()

    def _move_row(self, row: IngredientRow, delta: int) -> None:
        idx = self._rows.index(row)
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self._rows):
            return
        self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
        self._rows_layout.insertWidget(new_idx + 1, row)
        self._update_move_buttons()
        self.changed.emit()

    def _update_move_buttons(self) -> None:
        n = len(self._rows)
        for i, row in enumerate(self._rows):
            row.set_move_buttons(i > 0, i < n - 1)

    def _update_empty_state(self) -> None:
        self._empty_btn.setVisible(len(self._rows) == 0)

    def get_ingredients(self, recipe_code: str) -> list[RecipeIngredient]:
        return [r.get_data(recipe_code, i) for i, r in enumerate(self._rows)]
