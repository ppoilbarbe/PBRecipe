# SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Content and appearance dialog: HTML presentation, labels and image limits."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.config.recipe_config import _DEFAULT_STRINGS
from pbrecipe.constants import (
    DEFAULT_DIFF_IMG_MAX_H,
    DEFAULT_DIFF_IMG_MAX_W,
    DEFAULT_MEDIA_JPEG_QUALITY,
    DEFAULT_MEDIA_MAX_H,
    DEFAULT_MEDIA_MAX_W,
)
from pbrecipe.database import Database
from pbrecipe.ui.html_editor import HtmlEditor

_STRING_LABELS: dict[str, str] = {
    # Application
    "window_title": "Titre de la fenêtre de l'application",
    "recipe_singular": "Nom singulier (ex. : Recette)",
    "recipe_plural": "Nom pluriel (ex. : Recettes)",
    # Champs de la recette
    "serving_label": "Libellé de la quantité servie",
    "category_label": "Libellé de la catégorie (singulier)",
    "categories_label": "Libellé des catégories (pluriel)",
    "difficulty_label": "Libellé de la difficulté",
    "duration_label": "Libellé de la durée totale",
    "prep_label": "Libellé de la préparation",
    "wait_label": "Libellé du temps d'attente",
    "cook_label": "Libellé de la cuisson",
    "ingredients_label": "Libellé des ingrédients",
    "description_label": "Libellé de la réalisation",
    "comments_label": "Libellé des commentaires",
    "source_label": "Libellé de la source",
    "techniques_label": "Libellé des techniques",
    # Site web
    "site_title": "Titre du site web",
    "site_description": "Description du site web",
    "search_placeholder": "Texte indicatif du champ de recherche",
    "all_categories": "Placeholder du filtre catégories",
    "all_sources": "Placeholder du filtre sources",
    "search_by_ingredient": "Option de recherche par ingrédient",
    "show_techniques": "Option d'affichage d'une technique",
    "no_results": "Message si aucune recette trouvée",
    "no_group_label": "Libellé de la case « Ne pas grouper »",
}

_DIALOG_TITLE = "Contenu et apparence"


class GlobalsDialog(QDialog):
    """Édition des paramètres généraux de la base."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle(_DIALOG_TITLE)
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        tabs = QTabWidget()

        # ── Onglet Présentation ───────────────────────────────────────────
        pres_widget = QWidget()
        pres_layout = QVBoxLayout(pres_widget)
        pres_layout.setContentsMargins(4, 4, 4, 4)
        self._presentation_editor = HtmlEditor()
        pres_layout.addWidget(self._presentation_editor)
        tabs.addTab(pres_widget, "Présentation")

        # ── Onglet Libellés ───────────────────────────────────────────────
        strings_widget = QWidget()
        strings_layout = QVBoxLayout(strings_widget)
        strings_layout.setContentsMargins(4, 4, 4, 4)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        strings_form = QFormLayout(inner)
        self._string_edits: dict[str, QLineEdit] = {}
        for key, default in _DEFAULT_STRINGS.items():
            edit = QLineEdit()
            edit.setPlaceholderText(default)
            self._string_edits[key] = edit
            label = _STRING_LABELS.get(key, key)
            strings_form.addRow(f"{label} :", edit)
        scroll.setWidget(inner)
        strings_layout.addWidget(scroll)
        tabs.addTab(strings_widget, "Libellés")

        # ── Onglet Médias ─────────────────────────────────────────────────
        media_widget = QWidget()
        media_layout = QVBoxLayout(media_widget)
        media_layout.setContentsMargins(8, 8, 8, 8)
        media_layout.setSpacing(12)

        diff_group = QGroupBox("Icônes de difficulté")
        diff_form = QFormLayout(diff_group)
        self._diff_max_w_spin = self._make_size_spin(64, 4096, DEFAULT_DIFF_IMG_MAX_W)
        self._diff_max_h_spin = self._make_size_spin(64, 4096, DEFAULT_DIFF_IMG_MAX_H)
        diff_form.addRow("Largeur maximale :", self._diff_max_w_spin)
        diff_form.addRow("Hauteur maximale :", self._diff_max_h_spin)
        media_layout.addWidget(diff_group)

        recipe_group = QGroupBox("Médias des recettes")
        recipe_form = QFormLayout(recipe_group)
        self._media_max_w_spin = self._make_size_spin(256, 8192, DEFAULT_MEDIA_MAX_W)
        self._media_max_h_spin = self._make_size_spin(256, 8192, DEFAULT_MEDIA_MAX_H)
        recipe_form.addRow("Largeur maximale :", self._media_max_w_spin)
        recipe_form.addRow("Hauteur maximale :", self._media_max_h_spin)
        self._jpeg_quality_spin = QSpinBox()
        self._jpeg_quality_spin.setRange(1, 100)
        self._jpeg_quality_spin.setValue(DEFAULT_MEDIA_JPEG_QUALITY)
        self._jpeg_quality_spin.setSuffix(" %")
        self._jpeg_quality_spin.setSingleStep(5)
        recipe_form.addRow("Qualité JPEG :", self._jpeg_quality_spin)
        media_layout.addWidget(recipe_group)

        media_layout.addStretch()
        tabs.addTab(media_widget, "Médias")

        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _make_size_spin(min_val: int, max_val: int, default: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSuffix(" px")
        spin.setSingleStep(64)
        return spin

    def _load(self) -> None:
        data = self._db.get_globals()

        self._presentation_editor.set_html(data.get("presentation", ""))
        recipes = [(r.code, r.name) for r in self._db.list_recipes()]
        image_keys = self._db.list_all_media_keys()
        techniques = [(t.code, t.title) for t in self._db.list_techniques()]
        self._presentation_editor.set_references(recipes, image_keys, techniques)
        self._presentation_editor.set_image_fetcher(self._db.get_media_data)

        for key, edit in self._string_edits.items():
            edit.setText(data.get(key, ""))

        self._diff_max_w_spin.setValue(
            _parse_int(data.get("diff_img_max_w"), DEFAULT_DIFF_IMG_MAX_W)
        )
        self._diff_max_h_spin.setValue(
            _parse_int(data.get("diff_img_max_h"), DEFAULT_DIFF_IMG_MAX_H)
        )
        self._media_max_w_spin.setValue(
            _parse_int(data.get("media_max_w"), DEFAULT_MEDIA_MAX_W)
        )
        self._media_max_h_spin.setValue(
            _parse_int(data.get("media_max_h"), DEFAULT_MEDIA_MAX_H)
        )
        self._jpeg_quality_spin.setValue(
            _parse_int(data.get("media_jpeg_quality"), DEFAULT_MEDIA_JPEG_QUALITY)
        )

    def _accept(self) -> None:
        data: dict[str, str] = {}
        presentation = self._presentation_editor.get_html()
        if presentation:
            data["presentation"] = presentation
        for key, edit in self._string_edits.items():
            val = edit.text().strip()
            if val:
                data[key] = val
        data["diff_img_max_w"] = str(self._diff_max_w_spin.value())
        data["diff_img_max_h"] = str(self._diff_max_h_spin.value())
        data["media_max_w"] = str(self._media_max_w_spin.value())
        data["media_max_h"] = str(self._media_max_h_spin.value())
        data["media_jpeg_quality"] = str(self._jpeg_quality_spin.value())
        self._db.set_globals(data)
        self.accept()


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default
