from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.config.recipe_config import _DEFAULT_STRINGS
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
    "all_categories": "Option « toutes catégories » dans le filtre",
    "all_difficulties": "Option « toutes difficultés » dans le filtre",
    "search_by_ingredient": "Option de recherche par ingrédient",
    "show_techniques": "Option d'affichage d'une technique",
    "no_results": "Message si aucune recette trouvée",
}


class GlobalsDialog(QDialog):
    """Édition de la présentation et des libellés propres à la base."""

    def __init__(self, db: Database, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Présentation et libellés de la base")
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

        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load(self) -> None:
        data = self._db.get_globals()

        self._presentation_editor.set_html(data.get("presentation", ""))
        recipes = [(r.code, r.name) for r in self._db.list_recipes()]
        images = self._db.list_all_media()
        techniques = [(t.code, t.title) for t in self._db.list_techniques()]
        self._presentation_editor.set_references(recipes, images, techniques)

        for key, edit in self._string_edits.items():
            edit.setText(data.get(key, ""))

    def _accept(self) -> None:
        data: dict[str, str] = {}
        presentation = self._presentation_editor.get_html()
        if presentation:
            data["presentation"] = presentation
        for key, edit in self._string_edits.items():
            val = edit.text().strip()
            if val:
                data[key] = val
        self._db.set_globals(data)
        self.accept()
