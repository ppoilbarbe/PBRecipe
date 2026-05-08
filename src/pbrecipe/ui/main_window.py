from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from pbrecipe.config import AppConfig, RecipeConfig
from pbrecipe.database import Database, create_database
from pbrecipe.models import Recipe, RecipeIngredient, RecipeMedia
from pbrecipe.ui.about_dialog import AboutDialog
from pbrecipe.ui.config_dialog import ConfigDialog
from pbrecipe.ui.recipe_editor import RecipeEditor

_log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(
        self,
        initial_path: str | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        super().__init__()
        self._config: RecipeConfig | None = None
        self._db: Database | None = None
        self._app_config = app_config if app_config is not None else AppConfig.load()
        self._consistency_dialog = None
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._update_title()
        self._auto_load(initial_path)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(1024, 700)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self._splitter)

        self._recipe_list = QListWidget()
        self._recipe_list.currentItemChanged.connect(self._on_recipe_selected)
        self._splitter.addWidget(self._recipe_list)

        self._stack = QStackedWidget()
        self._empty_widget = QWidget()
        self._recipe_editor = RecipeEditor()
        self._recipe_editor.saved.connect(self._on_recipe_saved)
        self._stack.addWidget(self._empty_widget)
        self._stack.addWidget(self._recipe_editor)
        self._splitter.addWidget(self._stack)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 3)

        self.statusBar().showMessage("Prêt")
        self._db_label = QLabel()
        self._db_label.setContentsMargins(4, 0, 4, 0)
        self.statusBar().addPermanentWidget(self._db_label)

        geom = self._app_config.window_geometry
        if geom.get("width") and geom.get("height"):
            self.resize(int(geom["width"]), int(geom["height"]))
        if geom.get("x") is not None and geom.get("y") is not None:
            self.move(int(geom["x"]), int(geom["y"]))
        if self._app_config.splitter_sizes:
            self._splitter.setSizes(self._app_config.splitter_sizes)

    def _setup_menus(self) -> None:
        menu_bar = self.menuBar()

        # File
        file_menu = menu_bar.addMenu("&Fichier")
        act_new = QAction("&Nouvelle base…", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.setStatusTip("Créer une nouvelle base de recettes")
        act_new.triggered.connect(self._new_config)
        file_menu.addAction(act_new)

        act_open = QAction("&Ouvrir…", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.setStatusTip("Ouvrir une base de recettes existante")
        act_open.triggered.connect(self._open_config)
        file_menu.addAction(act_open)

        self._recent_menu = QMenu("Fichiers &récents", self)
        self._recent_menu.menuAction().setStatusTip("Ouvrir un fichier récent")
        file_menu.addMenu(self._recent_menu)
        self._rebuild_recent_menu()

        self._act_settings = QAction("&Paramètres de la base…", self)
        self._act_settings.setStatusTip("Modifier les paramètres de la base ouverte")
        self._act_settings.triggered.connect(self._edit_config)
        file_menu.addAction(self._act_settings)

        self._act_globals = QAction("Présentation et &libellés…", self)
        self._act_globals.setStatusTip(
            "Modifier la présentation et les libellés propres à cette base"
        )
        self._act_globals.triggered.connect(self._edit_globals)
        file_menu.addAction(self._act_globals)

        act_prefs = QAction("P&références du programme…", self)
        act_prefs.setStatusTip("Modifier les préférences du programme")
        act_prefs.triggered.connect(self._edit_preferences)
        file_menu.addAction(act_prefs)

        file_menu.addSeparator()

        self._act_export_php = QAction("&Export PHP", self)
        self._act_export_php.setStatusTip("Exporter la base vers les fichiers PHP")
        self._act_export_php.triggered.connect(self._export_php)
        file_menu.addAction(self._act_export_php)

        self._act_export_php_as = QAction("Export PHP &sous…", self)
        self._act_export_php_as.setStatusTip(
            "Exporter la base vers un répertoire PHP choisi et l'enregistrer"
        )
        self._act_export_php_as.triggered.connect(self._export_php_as)
        file_menu.addAction(self._act_export_php_as)

        file_menu.addSeparator()

        self._act_export_yaml = QAction("E&xporter YAML", self)
        self._act_export_yaml.setStatusTip("Exporter toute la base en fichier YAML")
        self._act_export_yaml.triggered.connect(self._export_yaml)
        file_menu.addAction(self._act_export_yaml)

        self._act_export_yaml_as = QAction("Exporter YAML s&ous…", self)
        self._act_export_yaml_as.setStatusTip(
            "Exporter la base en YAML vers un fichier choisi"
            " et enregistrer le répertoire"
        )
        self._act_export_yaml_as.triggered.connect(self._export_yaml_as)
        file_menu.addAction(self._act_export_yaml_as)

        self._act_import_yaml = QAction("I&mporter YAML…", self)
        self._act_import_yaml.setStatusTip("Importer des données depuis un fichier")
        self._act_import_yaml.triggered.connect(self._import_yaml)
        file_menu.addAction(self._act_import_yaml)

        file_menu.addSeparator()

        act_quit = QAction("&Quitter", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.setStatusTip("Quitter l'application")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Recipe
        recipe_menu = menu_bar.addMenu("&Recette")
        self._act_new_recipe = QAction("&Nouvelle recette", self)
        self._act_new_recipe.setShortcut(QKeySequence("Ctrl+R"))
        self._act_new_recipe.setStatusTip("Créer une nouvelle recette vide")
        self._act_new_recipe.triggered.connect(self._new_recipe)
        recipe_menu.addAction(self._act_new_recipe)

        self._act_copy_recipe = QAction("&Copier la recette…", self)
        self._act_copy_recipe.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self._act_copy_recipe.setStatusTip("Dupliquer la recette sélectionnée")
        self._act_copy_recipe.triggered.connect(self._copy_recipe)
        recipe_menu.addAction(self._act_copy_recipe)

        self._act_del_recipe = QAction("&Supprimer la recette", self)
        self._act_del_recipe.setStatusTip("Supprimer la recette sélectionnée")
        self._act_del_recipe.triggered.connect(self._delete_recipe)
        recipe_menu.addAction(self._act_del_recipe)

        recipe_menu.addSeparator()
        recipe_menu.addAction(self._recipe_editor.save_action)

        # Reference tables
        ref_menu = menu_bar.addMenu("&Référentiels")
        self._act_ref_categories = QAction("Catégories…", self)
        self._act_ref_categories.setStatusTip("Gérer les catégories de recettes")
        self._act_ref_categories.triggered.connect(self._edit_categories)
        ref_menu.addAction(self._act_ref_categories)

        self._act_ref_ingredients = QAction("Ingrédients…", self)
        self._act_ref_ingredients.setStatusTip("Gérer la liste des ingrédients")
        self._act_ref_ingredients.triggered.connect(self._edit_ingredients)
        ref_menu.addAction(self._act_ref_ingredients)

        self._act_ref_units = QAction("Unités…", self)
        self._act_ref_units.setStatusTip("Gérer les unités de mesure")
        self._act_ref_units.triggered.connect(self._edit_units)
        ref_menu.addAction(self._act_ref_units)

        self._act_ref_techniques = QAction("Techniques…", self)
        self._act_ref_techniques.setStatusTip("Gérer les techniques d'élaboration")
        self._act_ref_techniques.triggered.connect(self._edit_techniques)
        ref_menu.addAction(self._act_ref_techniques)

        self._act_ref_sources = QAction("Sources…", self)
        self._act_ref_sources.setStatusTip("Gérer les sources (livres, sites web…)")
        self._act_ref_sources.triggered.connect(self._edit_sources)
        ref_menu.addAction(self._act_ref_sources)

        self._act_ref_difficulty = QAction("Niveaux de difficulté…", self)
        self._act_ref_difficulty.setStatusTip("Gérer les niveaux de difficulté")
        self._act_ref_difficulty.triggered.connect(self._edit_difficulty_levels)
        ref_menu.addAction(self._act_ref_difficulty)

        ref_menu.addSeparator()
        self._act_consistency = QAction("&Vérifier la cohérence", self)
        self._act_consistency.setStatusTip(
            "Vérifier la cohérence des recettes et des techniques"
        )
        self._act_consistency.triggered.connect(self._check_consistency)
        ref_menu.addAction(self._act_consistency)

        # Help
        help_menu = menu_bar.addMenu("&Aide")
        act_about = QAction("&À propos…", self)
        act_about.setStatusTip("Informations sur l'application")
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _setup_toolbar(self) -> None:
        icons_dir = Path(__file__).parent.parent / "resources" / "icons"

        def _icon(name: str) -> QIcon:
            return QIcon(str(icons_dir / f"{name}.svg"))

        self._act_settings.setIcon(_icon("db_settings"))
        self._act_globals.setIcon(_icon("db_globals"))
        self._act_export_php.setIcon(_icon("export_php"))
        self._act_export_php_as.setIcon(_icon("export_php_as"))
        self._act_export_yaml.setIcon(_icon("export_yaml"))
        self._act_export_yaml_as.setIcon(_icon("export_yaml_as"))
        self._act_import_yaml.setIcon(_icon("import_yaml"))
        self._act_consistency.setIcon(_icon("consistency"))
        self._act_new_recipe.setIcon(_icon("recipe_new"))
        self._act_copy_recipe.setIcon(_icon("recipe_copy"))
        self._act_del_recipe.setIcon(_icon("recipe_delete"))

        self._act_ref_categories.setIcon(_icon("ref_categories"))
        self._act_ref_ingredients.setIcon(_icon("ref_ingredients"))
        self._act_ref_units.setIcon(_icon("ref_units"))
        self._act_ref_techniques.setIcon(_icon("ref_techniques"))
        self._act_ref_sources.setIcon(_icon("ref_sources"))
        self._act_ref_difficulty.setIcon(_icon("ref_difficulty"))

        self._act_ref_categories.setToolTip("Catégories")
        self._act_ref_ingredients.setToolTip("Ingrédients")
        self._act_ref_units.setToolTip("Unités")
        self._act_ref_techniques.setToolTip("Techniques")
        self._act_ref_sources.setToolTip("Sources")
        self._act_ref_difficulty.setToolTip("Niveaux de difficulté")

        def _tb(name: str, object_name: str) -> QToolBar:
            tb = QToolBar(name, self)
            tb.setObjectName(object_name)
            self.addToolBar(tb)
            return tb

        tb_db = _tb("Base de données", "tb_db")
        tb_db.addAction(self._act_settings)
        tb_db.addAction(self._act_globals)

        tb_php = _tb("Export PHP", "tb_php")
        tb_php.addAction(self._act_export_php)
        tb_php.addAction(self._act_export_php_as)

        tb_yaml = _tb("Export/Import YAML", "tb_yaml")
        tb_yaml.addAction(self._act_export_yaml)
        tb_yaml.addAction(self._act_export_yaml_as)
        tb_yaml.addAction(self._act_import_yaml)

        tb_recipe = _tb("Recettes", "tb_recipe")
        tb_recipe.addAction(self._act_new_recipe)
        tb_recipe.addAction(self._act_copy_recipe)
        tb_recipe.addAction(self._act_del_recipe)

        tb_ref = _tb("Référentiels", "tb_ref")
        tb_ref.addAction(self._act_ref_categories)
        tb_ref.addAction(self._act_ref_ingredients)
        tb_ref.addAction(self._act_ref_units)
        tb_ref.addAction(self._act_ref_techniques)
        tb_ref.addAction(self._act_ref_sources)
        tb_ref.addAction(self._act_ref_difficulty)
        tb_ref.addAction(self._act_consistency)

        if self._app_config.toolbar_state:
            self.restoreState(
                QByteArray.fromBase64(self._app_config.toolbar_state.encode())
            )

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = self._app_config.recent_files
        if not recent:
            act = QAction("(aucun)", self)
            act.setEnabled(False)
            self._recent_menu.addAction(act)
            return
        for path in recent:
            label = Path(path).name
            act = QAction(label, self)
            act.setToolTip(path)
            act.setStatusTip(f"Ouvrir : {path}")
            act.triggered.connect(lambda checked=False, p=path: self._open_recent(p))
            self._recent_menu.addAction(act)
        self._recent_menu.addSeparator()
        act_clear = QAction("Vider la liste", self)
        act_clear.setStatusTip("Effacer la liste des fichiers récents")
        act_clear.triggered.connect(self._clear_recent)
        self._recent_menu.addAction(act_clear)

    # ------------------------------------------------------------------
    # Auto-load at startup
    # ------------------------------------------------------------------

    def _auto_load(self, initial_path: str | None) -> None:
        path = initial_path or self._app_config.last_file
        if path:
            resolved = Path(path).expanduser()
            if resolved.exists():
                _log.debug("Chargement automatique : %s", resolved)
                try:
                    self._load_config(RecipeConfig.from_file(resolved))
                except Exception as exc:  # noqa: BLE001
                    _log.error("Chargement automatique échoué : %s — %s", resolved, exc)
                    QMessageBox.warning(
                        self,
                        "Chargement automatique",
                        f"Impossible d'ouvrir « {path} » :\n{exc}",
                    )
            else:
                _log.debug("Fichier de démarrage introuvable : %s", path)
        else:
            _log.debug("Aucun fichier à charger au démarrage")

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _new_config(self) -> None:
        dd = self._app_config.dialog_dirs
        dlg = ConfigDialog(RecipeConfig(), self, dialog_dirs=dd)
        if dlg.exec():
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer la configuration",
                dd.get("new_config"),
                "YAML (*.yaml *.yml)",
            )
            if path:
                dd.record("new_config", path)
                dlg.config.save(path)
                self._register_recent(dlg.config.path)
                self._load_config(dlg.config)

    def _open_config(self) -> None:
        dd = self._app_config.dialog_dirs
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir une configuration",
            dd.get("open_config"),
            "YAML (*.yaml *.yml)",
        )
        if path:
            dd.record("open_config", path)
            try:
                self._load_config(RecipeConfig.from_file(path))
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Erreur", str(exc))

    def _open_recent(self, path: str) -> None:
        resolved = Path(path).expanduser()
        if not resolved.exists():
            QMessageBox.warning(
                self,
                "Fichier introuvable",
                f"Le fichier suivant est introuvable :\n{path}",
            )
            return
        try:
            self._load_config(RecipeConfig.from_file(resolved))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erreur", str(exc))

    def _clear_recent(self) -> None:
        self._app_config.clear_recent()
        self._app_config.save()
        self._rebuild_recent_menu()

    def _edit_config(self) -> None:
        if self._config is None:
            return
        old_db = replace(self._config.db)
        dlg = ConfigDialog(self._config, self, dialog_dirs=self._app_config.dialog_dirs)
        if dlg.exec():
            self._config = dlg.config
            self._config.save()
            self._update_title()
            if self._config.db != old_db:
                try:
                    self._switch_database(self._config)
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.critical(self, "Erreur de connexion", str(exc))
            _log.info("Paramètres de la base mis à jour : «%s»", self._config.name)

    def _edit_globals(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.globals_dialog import GlobalsDialog

        GlobalsDialog(self._db, self).exec()

    def _edit_preferences(self) -> None:
        from pbrecipe.ui.preferences_dialog import PreferencesDialog

        PreferencesDialog(self._app_config, self).exec()

    def _load_config(self, config: RecipeConfig) -> None:
        if not self._confirm_discard():
            return
        try:
            self._switch_database(config)
        except Exception as exc:  # noqa: BLE001
            _log.error("Connexion échouée : %s", exc)
            reply = QMessageBox.critical(
                self,
                "Erreur de connexion",
                f"Impossible de se connecter à la base :\n{exc}\n\n"
                "Voulez-vous modifier les paramètres ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            dlg = ConfigDialog(config, self, dialog_dirs=self._app_config.dialog_dirs)
            if not dlg.exec():
                return
            config = dlg.config
            if config.path:
                config.save()
            try:
                self._switch_database(config)
            except Exception as exc2:  # noqa: BLE001
                QMessageBox.critical(self, "Erreur de connexion", str(exc2))

    def _switch_database(self, config: RecipeConfig) -> None:
        """Déconnecte l'ancienne base et connecte la nouvelle."""
        if self._db:
            self._db.disconnect()
            self._db = None

        db = create_database(config)
        db.connect()

        if config.db.type in ("mariadb", "postgresql"):
            status = db.check_schema()
            if status == "empty":
                reply = QMessageBox.question(
                    self,
                    "Base vide",
                    "La base de données est vide.\nVoulez-vous créer les tables ?",
                )
                if reply != QMessageBox.StandardButton.Yes:
                    db.disconnect()
                    self._config = None
                    self._update_title()
                    self._refresh_recipe_list()
                    return
            elif status == "foreign":
                db.disconnect()
                raise RuntimeError(
                    "La base de données contient des tables inconnues.\n"
                    "Impossible d'utiliser cette base."
                )

        db.create_schema()
        self._db = db
        self._config = config
        if config.path:
            self._register_recent(config.path)
        self._update_title()
        self._refresh_recipe_list()
        _log.info("Base chargée : «%s»", config.name)

    def _register_recent(self, path: Path | str | None) -> None:
        if path is None:
            return
        self._app_config.add_recent(path)
        self._app_config.save()
        self._rebuild_recent_menu()

    # ------------------------------------------------------------------
    # Recipe list
    # ------------------------------------------------------------------

    def _refresh_recipe_list(self, select_code: str | None = None) -> None:
        self._recipe_list.currentItemChanged.disconnect(self._on_recipe_selected)
        self._recipe_list.clear()
        if self._db is None:
            self._recipe_list.currentItemChanged.connect(self._on_recipe_selected)
            return
        recipes = self._db.list_recipes()
        for recipe in recipes:
            item = QListWidgetItem(recipe.name)
            item.setData(Qt.ItemDataRole.UserRole, recipe.code)
            self._recipe_list.addItem(item)
        if select_code is not None:
            for i in range(self._recipe_list.count()):
                if (
                    self._recipe_list.item(i).data(Qt.ItemDataRole.UserRole)
                    == select_code
                ):
                    self._recipe_list.setCurrentRow(i)
                    break
        self._recipe_list.currentItemChanged.connect(self._on_recipe_selected)
        _log.debug("Liste recettes rafraîchie : %d recettes", len(recipes))

    def _on_recipe_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None or self._db is None:
            self._recipe_editor.clear()
            self._stack.setCurrentWidget(self._empty_widget)
            return
        if not self._confirm_discard():
            self._recipe_list.currentItemChanged.disconnect(self._on_recipe_selected)
            self._recipe_list.setCurrentItem(_prev)
            self._recipe_list.currentItemChanged.connect(self._on_recipe_selected)
            return
        code = current.data(Qt.ItemDataRole.UserRole)
        _log.debug("Recette sélectionnée : %s", code)
        recipe = self._db.get_recipe(code)
        if recipe:
            self._recipe_editor.load(recipe, self._db, self._config)
            self._stack.setCurrentWidget(self._recipe_editor)

    def _new_recipe(self) -> None:
        if self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return
        if not self._confirm_discard():
            return
        _log.info("Nouvelle recette")
        recipe = Recipe()
        self._recipe_editor.load(recipe, self._db, self._config)
        self._stack.setCurrentWidget(self._recipe_editor)

    def _copy_recipe(self) -> None:
        item = self._recipe_list.currentItem()
        if item is None or self._db is None:
            return
        if not self._confirm_discard():
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        original = self._db.get_recipe(code)
        if original is None:
            return
        copy = Recipe(
            code="",
            name=f"Copie de {original.name}",
            difficulty=original.difficulty,
            serving=original.serving,
            prep_time=original.prep_time,
            wait_time=original.wait_time,
            cook_time=original.cook_time,
            description=original.description,
            comments=original.comments,
            source_id=original.source_id,
            categories=list(original.categories),
            ingredients=[
                RecipeIngredient(
                    id=None,
                    recipe_code="",
                    position=i.position,
                    prefix=i.prefix,
                    quantity=i.quantity,
                    unit_id=i.unit_id,
                    separator=i.separator,
                    ingredient_id=i.ingredient_id,
                    suffix=i.suffix,
                )
                for i in original.ingredients
            ],
            media=[
                RecipeMedia(
                    id=None,
                    recipe_code="",
                    position=m.position,
                    code=m.code,
                    mime_type=m.mime_type,
                    data=m.data,
                )
                for m in original.media
            ],
        )
        _log.info("Copie de recette : %s → (nouvelle)", original.code)
        self._recipe_editor.load(copy, self._db, self._config)
        self._stack.setCurrentWidget(self._recipe_editor)

    def _delete_recipe(self) -> None:
        item = self._recipe_list.currentItem()
        if item is None or self._db is None:
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer la recette « {item.text()} » ?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            _log.info(
                "Recette supprimée depuis l'interface : %s — «%s»", code, item.text()
            )
            self._db.delete_recipe(code)
            self._refresh_recipe_list()
            self._stack.setCurrentWidget(self._empty_widget)

    def _on_recipe_saved(self, recipe: Recipe) -> None:
        _log.debug("Signal sauvegarde reçu : %s", recipe.code)
        if self._db:
            original = self._recipe_editor._original_code
            self._db.save_recipe(
                recipe, original_code=original if original != recipe.code else None
            )
        self._refresh_recipe_list(select_code=recipe.code)

    # ------------------------------------------------------------------
    # Reference table editors
    # ------------------------------------------------------------------

    def _edit_categories(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.category_dialog import CategoryDialog

        CategoryDialog(self._db, self).exec()
        self._recipe_editor.reload_references()

    def _edit_ingredients(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.ingredient_dialog import IngredientDialog

        IngredientDialog(self._db, self).exec()
        self._recipe_editor.reload_references()

    def _edit_units(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.unit_dialog import UnitDialog

        UnitDialog(self._db, self).exec()
        self._recipe_editor.reload_references()

    def _edit_techniques(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.technique_dialog import TechniqueDialog

        TechniqueDialog(self._db, self).exec()
        self._recipe_editor.reload_references()

    def _edit_sources(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.source_dialog import SourceDialog

        SourceDialog(self._db, self).exec()
        self._recipe_editor.reload_references()

    def _edit_difficulty_levels(self) -> None:
        if self._db is None:
            return
        from pbrecipe.ui.dialogs.difficulty_dialog import DifficultyDialog

        DifficultyDialog(self._db, self).exec()

    # ------------------------------------------------------------------
    # YAML export / import
    # ------------------------------------------------------------------

    def _export_yaml(self) -> None:
        if self._config is None or self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return
        configured_file = self._config.yaml_export_file
        if configured_file and Path(configured_file).expanduser().parent.is_dir():
            path = str(Path(configured_file).expanduser())
        else:
            dd = self._app_config.dialog_dirs
            start = configured_file or dd.get("export_yaml")
            path, _ = QFileDialog.getSaveFileName(
                self, "Exporter en YAML", start, "YAML (*.yaml *.yml)"
            )
            if not path:
                return
            if not path.lower().endswith((".yaml", ".yml")):
                path += ".yaml"
            dd.record("export_yaml", path)
        from pbrecipe.export.yaml_io import YamlExport

        try:
            YamlExport(self._db).run(path)
            self._config.yaml_export_file = path
            self._config.save()
            _log.info("Export YAML terminé : %s", path)
            QMessageBox.information(
                self, "Export réussi", f"Base exportée dans :\n{path}"
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("Export YAML échoué : %s", exc)
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    def _export_yaml_as(self) -> None:
        if self._config is None or self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return
        dd = self._app_config.dialog_dirs
        configured_file = self._config.yaml_export_file
        start = configured_file or dd.get("export_yaml")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter en YAML sous…", start, "YAML (*.yaml *.yml)"
        )
        if not path:
            return
        if not path.lower().endswith((".yaml", ".yml")):
            path += ".yaml"
        dd.record("export_yaml", path)
        from pbrecipe.export.yaml_io import YamlExport

        _log.info("Export YAML (sous) → %s", path)
        try:
            YamlExport(self._db).run(path)
            self._config.yaml_export_file = path
            self._config.save()
            _log.info("Export YAML terminé : %s", path)
            QMessageBox.information(
                self, "Export réussi", f"Base exportée dans :\n{path}"
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("Export YAML échoué : %s", exc)
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    def _import_yaml(self) -> None:
        if self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return
        dd = self._app_config.dialog_dirs
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer depuis YAML", dd.get("import_yaml"), "YAML (*.yaml *.yml)"
        )
        if not path:
            return
        dd.record("import_yaml", path)
        if not self._confirm_discard():
            return

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Mode d'import")
        dlg.setText("Comment souhaitez-vous importer ce fichier YAML ?")
        dlg.setInformativeText(
            "« Remplacer » efface toute la base avant l'import.\n"
            "« Fusionner » ajoute ou met à jour sans rien supprimer."
        )
        btn_cancel = dlg.addButton("Annuler", QMessageBox.ButtonRole.RejectRole)
        dlg.addButton("Fusionner", QMessageBox.ButtonRole.AcceptRole)
        btn_replace = dlg.addButton("Remplacer", QMessageBox.ButtonRole.AcceptRole)
        dlg.setDefaultButton(btn_replace)
        dlg.exec()
        clicked = dlg.clickedButton()
        if clicked is btn_cancel or clicked is None:
            return
        replace_mode = clicked is btn_replace

        from pbrecipe.export.yaml_io import YamlImport

        try:
            stats = YamlImport(self._db).run(path, replace=replace_mode)
            self._refresh_recipe_list()
            self._stack.setCurrentWidget(self._empty_widget)
            msg = (
                f"Import terminé :\n"
                f"  Catégories créées : {stats['categories']}\n"
                f"  Unités créées : {stats['units']}\n"
                f"  Ingrédients créés : {stats['ingredients']}\n"
                f"  Sources créées : {stats['sources']}\n"
                f"  Techniques importées : {stats['techniques']}\n"
                f"  Recettes créées : {stats['recipes_created']}\n"
                f"  Recettes mises à jour : {stats['recipes_updated']}"
            )
            _log.info("Import YAML terminé : %s", path)
            QMessageBox.information(self, "Import réussi", msg)
        except Exception as exc:  # noqa: BLE001
            _log.error("Import YAML échoué : %s", exc)
            QMessageBox.critical(self, "Erreur d'import", str(exc))

    # ------------------------------------------------------------------
    # PHP export
    # ------------------------------------------------------------------

    def _export_php(self) -> None:
        if self._config is None or self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return

        configured_dir = self._config.php_export_dir
        if configured_dir and Path(configured_dir).expanduser().is_dir():
            target = str(Path(configured_dir).expanduser())
        else:
            dd = self._app_config.dialog_dirs
            target = QFileDialog.getExistingDirectory(
                self,
                "Répertoire cible pour l'export PHP",
                configured_dir or dd.get("export_php"),
            )
            if not target:
                return
            dd.record("export_php", target, is_dir=True)

        if not self._consistency_check_before_export():
            return

        from pbrecipe.export.php_export import PhpExport

        _log.info("Export PHP → %s", target)
        try:
            exporter = PhpExport(self._config, self._db, Path(target))
            exporter.run()
            self._config.php_export_dir = target
            self._config.save()
            _log.info("Export PHP terminé : %s", target)
            QMessageBox.information(
                self, "Export réussi", f"Fichiers PHP exportés dans :\n{target}"
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("Export PHP échoué : %s", exc)
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    def _export_php_as(self) -> None:
        if self._config is None or self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return

        configured_dir = self._config.php_export_dir
        dd = self._app_config.dialog_dirs
        target = QFileDialog.getExistingDirectory(
            self,
            "Répertoire cible pour l'export PHP",
            configured_dir or dd.get("export_php"),
        )
        if not target:
            return
        dd.record("export_php", target, is_dir=True)

        if not self._consistency_check_before_export():
            return

        from pbrecipe.export.php_export import PhpExport

        _log.info("Export PHP (sous) → %s", target)
        try:
            exporter = PhpExport(self._config, self._db, Path(target))
            exporter.run()
            self._config.php_export_dir = target
            self._config.save()
            _log.info("Export PHP terminé : %s", target)
            QMessageBox.information(
                self, "Export réussi", f"Fichiers PHP exportés dans :\n{target}"
            )
        except Exception as exc:  # noqa: BLE001
            _log.error("Export PHP échoué : %s", exc)
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    # ------------------------------------------------------------------
    # Consistency check
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        AboutDialog(self).exec()

    def _check_consistency(self) -> None:
        if self._db is None:
            QMessageBox.warning(
                self, "Aucune base", "Ouvrez d'abord une base de recettes."
            )
            return
        from pbrecipe.ui.consistency_dialog import (
            ConsistencyReportDialog,
            build_report,
            run_check,
        )

        recipe_issues, tech_issues, pres_issues = run_check(self._db)
        if not recipe_issues and not tech_issues and not pres_issues:
            QMessageBox.information(self, "Cohérence", "Aucun problème détecté.")
            return
        html = build_report(recipe_issues, tech_issues, pres_issues)
        self._consistency_dialog = ConsistencyReportDialog(html, self)
        self._consistency_dialog.show()

    def _consistency_check_before_export(self) -> bool:
        """Vérifie la cohérence. Retourne True si l'export peut continuer."""
        from pbrecipe.ui.consistency_dialog import (
            ConsistencyReportDialog,
            build_report,
            run_check,
        )

        recipe_issues, tech_issues, pres_issues = run_check(self._db)
        if not recipe_issues and not tech_issues and not pres_issues:
            return True

        n = (
            sum(len(r.refs) for r in recipe_issues)
            + sum(len(t.refs) for t in tech_issues)
            + len(pres_issues)
        )
        reply = QMessageBox.warning(
            self,
            "Problèmes de cohérence détectés",
            f"{n} problème(s) détecté(s) dans la base.\n"
            "L'export PHP peut produire des liens cassés.\n\n"
            "Voulez-vous afficher le rapport et annuler l'export ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            html = build_report(recipe_issues, tech_issues, pres_issues)
            self._consistency_dialog = ConsistencyReportDialog(html, self)
            self._consistency_dialog.show()
            return False
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_title(self) -> None:
        if self._config:
            self.setWindowTitle(f"PBRecipe — {self._config.name}")
        else:
            self.setWindowTitle("PBRecipe")
        self._update_db_label()

    def _update_db_label(self) -> None:
        if self._config is None:
            self._db_label.setText("")
            return
        db = self._config.db
        if db.type == "sqlite":
            name = Path(db.path).expanduser().name
        else:
            name = db.database
        self._db_label.setText(f"{db.type}:{name}")

    def _confirm_discard(self) -> bool:
        if not self._recipe_editor.has_unsaved_changes():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Modifications non enregistrées")
        box.setText("La recette a été modifiée. Que voulez-vous faire ?")
        btn_save = box.addButton("Enregistrer", QMessageBox.ButtonRole.AcceptRole)
        btn_discard = box.addButton(
            "Abandonner", QMessageBox.ButtonRole.DestructiveRole
        )
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_save:
            self._recipe_editor._save()  # noqa: SLF001
            return True
        return clicked is btn_discard

    def closeEvent(self, event) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        pos = self.pos()
        size = self.size()
        self._app_config.window_geometry = {
            "x": pos.x(),
            "y": pos.y(),
            "width": size.width(),
            "height": size.height(),
        }
        self._app_config.splitter_sizes = self._splitter.sizes()
        self._app_config.toolbar_state = self.saveState().toBase64().data().decode()
        self._app_config.save()
        _log.debug("Fermeture de l'application")
        if self._db:
            self._db.disconnect()
        super().closeEvent(event)
