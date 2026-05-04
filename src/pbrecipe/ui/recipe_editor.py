from __future__ import annotations

import logging
import re
import unicodedata

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.config import RecipeConfig
from pbrecipe.database import Database
from pbrecipe.models import Recipe
from pbrecipe.ui.html_editor import HtmlEditor
from pbrecipe.ui.ingredient_list_editor import IngredientListEditor
from pbrecipe.ui.media_tab import MediaTab

_log = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Derive a recipe code from its name."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().upper()
    return re.sub(r"[\s-]+", "_", text)[:50]


class RecipeEditor(QWidget):
    saved = Signal(Recipe)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipe: Recipe | None = None
        self._db: Database | None = None
        self._config: RecipeConfig | None = None
        self._dirty = False
        self._loading = False
        self._setup_ui()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        # Header: name + code
        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nom de la recette")
        self._name_edit.textChanged.connect(self._on_name_changed)
        self._name_edit.textChanged.connect(self._mark_dirty)
        form.addRow("Nom :", self._name_edit)

        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("CODE_UNIQUE")
        self._code_edit.textChanged.connect(self._mark_dirty)
        form.addRow("Code :", self._code_edit)
        root.addLayout(form)

        tabs = QTabWidget()
        root.addWidget(tabs)

        # Tab 1 — metadata
        meta_tab = QWidget()
        meta_layout = QVBoxLayout(meta_tab)
        meta_layout.addLayout(self._build_meta_form())
        meta_layout.addStretch()
        tabs.addTab(meta_tab, "Informations")

        # Tab 2 — ingredients
        self._ingredient_editor = IngredientListEditor()
        self._ingredient_editor.changed.connect(self._mark_dirty)
        tabs.addTab(self._ingredient_editor, "Ingrédients")

        # Tab 3 — description
        self._desc_editor = HtmlEditor()
        self._desc_editor.changed.connect(self._mark_dirty)
        tabs.addTab(self._desc_editor, "Réalisation")

        # Tab 4 — comments
        self._comment_editor = HtmlEditor()
        self._comment_editor.changed.connect(self._mark_dirty)
        tabs.addTab(self._comment_editor, "Commentaires")

        # Tab 5 — media
        self._media_tab = MediaTab()
        self._media_tab.changed.connect(self._mark_dirty)
        self._media_tab.changed.connect(self._refresh_editor_images)
        tabs.addTab(self._media_tab, "Médias")

        # Save button
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        self._save_btn = QPushButton("Enregistrer")
        self._save_btn.clicked.connect(self._save)
        self._save_btn.setEnabled(False)
        btn_bar.addWidget(self._save_btn)
        root.addLayout(btn_bar)

    def _build_meta_form(self) -> QFormLayout:
        form = QFormLayout()

        # Serving
        self._serving_edit = QLineEdit()
        self._serving_edit.setPlaceholderText("ex. 6 parts, 3 personnes")
        self._serving_edit.setMaxLength(30)
        self._serving_edit.textChanged.connect(self._mark_dirty)
        form.addRow("Quantité :", self._serving_edit)

        # Difficulty
        self._difficulty_spin = QSpinBox()
        self._difficulty_spin.setRange(0, 3)
        self._difficulty_spin.setSpecialValueText("Inconnue")
        self._difficulty_spin.valueChanged.connect(self._mark_dirty)
        form.addRow("Difficulté :", self._difficulty_spin)

        # Temps (préparation + attente + cuisson sur une ligne)
        def _make_time_spin() -> QSpinBox:
            s = QSpinBox()
            s.setRange(0, 9999)
            s.setSuffix(" min")
            s.setSpecialValueText("—")
            s.valueChanged.connect(self._mark_dirty)
            return s

        self._prep_spin = _make_time_spin()
        self._wait_spin = _make_time_spin()
        self._cook_spin = _make_time_spin()

        times_row = QHBoxLayout()
        times_row.setSpacing(6)
        for label_text, spin in (
            ("Prép. :", self._prep_spin),
            ("Attente :", self._wait_spin),
            ("Cuisson :", self._cook_spin),
        ):
            lbl = QLabel(label_text)
            lbl.setBuddy(spin)
            times_row.addWidget(lbl)
            times_row.addWidget(spin)
        times_row.addStretch()
        form.addRow("Temps :", times_row)

        # Categories
        cat_group = QGroupBox("Catégories")
        cat_layout = QVBoxLayout(cat_group)
        self._category_list = QListWidget()
        self._category_list.itemChanged.connect(self._mark_dirty)
        cat_layout.addWidget(self._category_list)
        form.addRow(cat_group)

        # Source
        self._source_combo = QComboBox()
        self._source_combo.currentIndexChanged.connect(self._mark_dirty)
        form.addRow("Source :", self._source_combo)

        return form

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        recipe: Recipe,
        db: Database,
        config: RecipeConfig | None,
    ) -> None:
        self._loading = True
        self._recipe = recipe
        self._db = db
        self._config = config

        self._name_edit.setText(recipe.name)
        self._code_edit.setText(recipe.code)
        self._serving_edit.setText(recipe.serving)
        self._difficulty_spin.setValue(recipe.difficulty)
        self._prep_spin.setValue(recipe.prep_time or 0)
        self._wait_spin.setValue(recipe.wait_time or 0)
        self._cook_spin.setValue(recipe.cook_time or 0)
        self._desc_editor.set_html(recipe.description)
        self._comment_editor.set_html(recipe.comments)

        self._reload_categories(recipe)
        self._reload_sources(recipe)
        self._ingredient_editor.load(recipe.ingredients, db)
        self._media_tab.load(recipe.media)
        self._reload_editor_references(recipe, db)

        self._loading = False
        self._mark_clean()
        _log.debug(
            "Recette chargée dans l'éditeur : %s — «%s»",
            recipe.code or "(nouveau)",
            recipe.name or "(sans nom)",
        )

    def has_unsaved_changes(self) -> bool:
        return self._dirty

    def clear(self) -> None:
        self._loading = True
        self._recipe = None
        self._db = None
        self._config = None
        self._name_edit.clear()
        self._code_edit.clear()
        self._serving_edit.clear()
        self._difficulty_spin.setValue(0)
        self._prep_spin.setValue(0)
        self._wait_spin.setValue(0)
        self._cook_spin.setValue(0)
        self._desc_editor.set_html("")
        self._comment_editor.set_html("")
        self._category_list.clear()
        self._source_combo.clear()
        self._ingredient_editor.clear()
        self._media_tab.load([])
        self._loading = False
        self._mark_clean()

    def reload_references(self) -> None:
        """Mettre à jour les listes déroulantes après modification d'un référentiel."""
        if self._recipe is None or self._db is None:
            return
        self._loading = True
        self._reload_categories(self._recipe)
        self._reload_sources(self._recipe)
        self._ingredient_editor.reload(self._db)
        self._reload_editor_references(self._recipe, self._db)
        self._loading = False

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _mark_dirty(self) -> None:
        if self._loading:
            return
        self._dirty = True
        self._save_btn.setEnabled(True)

    def _mark_clean(self) -> None:
        self._dirty = False
        self._save_btn.setEnabled(False)

    def _on_name_changed(self, text: str) -> None:
        if self._recipe and not self._recipe.code:
            slug = _slugify(text)
            self._code_edit.setText(slug)
            _log.debug("Code auto-généré depuis le nom : %s", slug)

    def _save(self) -> None:
        if self._recipe is None:
            return
        self._recipe.name = self._name_edit.text().strip()
        self._recipe.code = self._code_edit.text().strip()
        self._recipe.serving = self._serving_edit.text().strip()
        self._recipe.difficulty = self._difficulty_spin.value()
        prep = self._prep_spin.value()
        wait = self._wait_spin.value()
        cook = self._cook_spin.value()
        self._recipe.prep_time = prep if prep > 0 else None
        self._recipe.wait_time = wait if wait > 0 else None
        self._recipe.cook_time = cook if cook > 0 else None
        self._recipe.description = self._desc_editor.get_html()
        self._recipe.comments = self._comment_editor.get_html()
        categories = [
            self._category_list.item(i).data(0x0100)
            for i in range(self._category_list.count())
            if self._category_list.item(i).checkState().value  # checked
        ]
        if not categories:
            _log.warning("Enregistrement annulé : aucune catégorie sélectionnée")
            QMessageBox.warning(
                self,
                "Catégorie manquante",
                "Veuillez sélectionner au moins une catégorie avant d'enregistrer.",
            )
            return
        self._recipe.categories = categories
        src_idx = self._source_combo.currentIndex()
        self._recipe.source_id = self._source_combo.itemData(src_idx)
        self._recipe.ingredients = self._ingredient_editor.get_ingredients(
            self._recipe.code
        )
        self._recipe.media = self._media_tab.get_media(self._recipe.code)
        self._mark_clean()
        _log.info(
            "Recette enregistrée : %s — «%s» (%d ingrédients, %d médias)",
            self._recipe.code,
            self._recipe.name,
            len(self._recipe.ingredients),
            len(self._recipe.media),
        )
        self.saved.emit(self._recipe)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _reload_editor_references(self, recipe: Recipe, db: Database) -> None:
        recipes = [(r.code, r.name) for r in db.list_recipes()]
        images = [(m.code, m.data) for m in recipe.media]
        techniques = [(t.code, t.title) for t in db.list_techniques()]
        for editor in (self._desc_editor, self._comment_editor):
            editor.set_references(recipes, images, techniques)

    def _refresh_editor_images(self) -> None:
        images = [(m.code, m.data) for m in self._media_tab.get_media("")]
        for editor in (self._desc_editor, self._comment_editor):
            editor.set_images(images)

    def _reload_categories(self, recipe: Recipe) -> None:
        self._category_list.clear()
        if self._db is None:
            return
        for cat in self._db.list_categories():
            item = QListWidgetItem(cat.name)
            item.setData(0x0100, cat.id)
            from PySide6.QtCore import Qt

            item.setCheckState(
                Qt.CheckState.Checked
                if cat.id in recipe.categories
                else Qt.CheckState.Unchecked
            )
            self._category_list.addItem(item)

    def _reload_sources(self, recipe: Recipe) -> None:
        self._source_combo.clear()
        self._source_combo.addItem("— aucune —", None)
        if self._db is None:
            return
        for src in self._db.list_sources():
            label = re.sub(r"<[^>]+>", "", src.name)
            self._source_combo.addItem(label, src.id)
            if src.id == recipe.source_id:
                self._source_combo.setCurrentIndex(self._source_combo.count() - 1)
