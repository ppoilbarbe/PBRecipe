from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.config.dialog_dirs import DialogDirs
from pbrecipe.config.recipe_config import _DEFAULT_STRINGS, DbConfig, RecipeConfig


class ConfigDialog(QDialog):
    def __init__(
        self,
        config: RecipeConfig,
        parent: QWidget | None = None,
        dialog_dirs: DialogDirs | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._dialog_dirs = dialog_dirs
        self.setWindowTitle("Paramètres de la base de recettes")
        self.setMinimumWidth(520)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()

        # Name
        self._name_edit = QLineEdit()
        form.addRow("Nom de la base :", self._name_edit)

        # PHP export directory
        php_row = QHBoxLayout()
        self._php_export_edit = QLineEdit()
        self._php_export_edit.setPlaceholderText("(non défini)")
        browse_php_btn = QPushButton("…")
        browse_php_btn.setFixedWidth(30)
        browse_php_btn.clicked.connect(self._browse_php_export_dir)
        php_row.addWidget(self._php_export_edit)
        php_row.addWidget(browse_php_btn)
        form.addRow("Répertoire d'export PHP :", php_row)

        # YAML export directory
        yaml_row = QHBoxLayout()
        self._yaml_export_edit = QLineEdit()
        self._yaml_export_edit.setPlaceholderText("(non défini)")
        browse_yaml_btn = QPushButton("…")
        browse_yaml_btn.setFixedWidth(30)
        browse_yaml_btn.clicked.connect(self._browse_yaml_export_file)
        yaml_row.addWidget(self._yaml_export_edit)
        yaml_row.addWidget(browse_yaml_btn)
        form.addRow("Fichier d'export YAML :", yaml_row)

        # Site type (used by recipe_integration.lib.php when integrated)
        self._site_type_edit = QLineEdit()
        self._site_type_edit.setPlaceholderText("recettes")
        self._site_type_edit.setMaxLength(40)
        form.addRow("Type de site :", self._site_type_edit)

        root.addLayout(form)

        # DB type selector
        db_group = QGroupBox("Base de données")
        db_layout = QVBoxLayout(db_group)
        db_form = QFormLayout()
        self._db_type = QComboBox()
        for label, value in [
            ("SQLite", "sqlite"),
            ("MariaDB", "mariadb"),
            ("PostgreSQL", "postgresql"),
        ]:
            self._db_type.addItem(label, value)
        self._db_type.currentIndexChanged.connect(self._on_db_type_changed)
        db_form.addRow("Type :", self._db_type)
        db_layout.addLayout(db_form)

        self._db_stack = QStackedWidget()

        # SQLite panel
        sqlite_widget = QWidget()
        sqlite_form = QFormLayout(sqlite_widget)
        self._sqlite_path = QLineEdit()
        self._sqlite_path.setPlaceholderText("~/recipes.db")
        sqlite_form.addRow("Fichier :", self._sqlite_path)
        self._db_stack.addWidget(sqlite_widget)

        # Network DB panel (shared by MariaDB / PostgreSQL)
        net_widget = QWidget()
        net_form = QFormLayout(net_widget)
        self._db_host = QLineEdit()
        self._db_port = QSpinBox()
        self._db_port.setRange(1, 65535)
        self._db_name = QLineEdit()
        self._db_user = QLineEdit()
        self._db_pass = QLineEdit()
        self._db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        net_form.addRow("Hôte :", self._db_host)
        net_form.addRow("Port :", self._db_port)
        net_form.addRow("Base :", self._db_name)
        net_form.addRow("Utilisateur :", self._db_user)
        net_form.addRow("Mot de passe :", self._db_pass)
        test_btn = QPushButton("Tester la connexion")
        test_btn.clicked.connect(self._test_connection)
        net_form.addRow("", test_btn)
        self._db_stack.addWidget(net_widget)

        db_layout.addWidget(self._db_stack)
        root.addWidget(db_group)

        # Strings
        strings_group = QGroupBox("Textes spécifiques au type de recettes")
        strings_layout = QVBoxLayout(strings_group)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        self._strings_form = QFormLayout(inner)
        self._string_edits: dict[str, QLineEdit] = {}
        for key, default in _DEFAULT_STRINGS.items():
            edit = QLineEdit()
            edit.setPlaceholderText(default)
            self._string_edits[key] = edit
            self._strings_form.addRow(f"{key} :", edit)
        scroll.setWidget(inner)
        strings_layout.addWidget(scroll)
        root.addWidget(strings_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_db_type_changed(self, index: int) -> None:
        db_type = self._db_type.itemData(index)
        self._db_stack.setCurrentIndex(0 if db_type == "sqlite" else 1)
        if db_type == "mariadb":
            self._db_port.setValue(3306)
        elif db_type == "postgresql":
            self._db_port.setValue(5432)

    def _test_connection(self) -> None:
        from urllib.parse import quote_plus

        from sqlalchemy import create_engine, text

        db_type = self._db_type.currentData()
        host = self._db_host.text().strip() or "localhost"
        port = self._db_port.value()
        name = self._db_name.text().strip()
        user = self._db_user.text().strip()
        pwd = self._db_pass.text()
        if db_type == "mariadb":
            url = (
                f"mysql+pymysql://{quote_plus(user)}:{quote_plus(pwd)}"
                f"@{host}:{port}/{name}?charset=utf8mb4"
            )
        elif db_type == "postgresql":
            url = (
                f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(pwd)}"
                f"@{host}:{port}/{name}"
            )
        else:
            return
        try:
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            QMessageBox.information(self, "Test de connexion", "Connexion réussie !")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Test de connexion", f"Échec de la connexion :\n{exc}"
            )

    def _browse_php_export_dir(self) -> None:
        if self._dialog_dirs is not None:
            start = self._dialog_dirs.get(
                "php_export_dir", self._php_export_edit.text()
            )
        else:
            start = self._php_export_edit.text()
        d = QFileDialog.getExistingDirectory(self, "Répertoire d'export PHP", start)
        if d:
            self._php_export_edit.setText(d)
            if self._dialog_dirs is not None:
                self._dialog_dirs.record("php_export_dir", d, is_dir=True)

    def _browse_yaml_export_file(self) -> None:
        start = self._yaml_export_edit.text()
        if not start and self._dialog_dirs is not None:
            start = self._dialog_dirs.get("yaml_export_file")
        path, _ = QFileDialog.getSaveFileName(
            self, "Fichier d'export YAML", start, "YAML (*.yaml *.yml)"
        )
        if path:
            if not path.lower().endswith((".yaml", ".yml")):
                path += ".yaml"
            self._yaml_export_edit.setText(path)
            if self._dialog_dirs is not None:
                self._dialog_dirs.record("yaml_export_file", path)

    def _load(self) -> None:
        self._name_edit.setText(self._config.name)
        self._php_export_edit.setText(self._config.php_export_dir)
        self._yaml_export_edit.setText(self._config.yaml_export_file)
        self._site_type_edit.setText(self._config.site_type)
        db = self._config.db
        for i in range(self._db_type.count()):
            if self._db_type.itemData(i) == db.type:
                self._db_type.setCurrentIndex(i)
                break
        self._sqlite_path.setText(db.path)
        self._db_host.setText(db.host)
        self._db_port.setValue(db.port)
        self._db_name.setText(db.database)
        self._db_user.setText(db.user)
        self._db_pass.setText(db.password)
        for key, edit in self._string_edits.items():
            edit.setText(self._config.strings.get(key, ""))

    def _accept(self) -> None:
        self._config.name = self._name_edit.text().strip() or "Mes Recettes"
        self._config.php_export_dir = self._php_export_edit.text().strip()
        self._config.yaml_export_file = self._yaml_export_edit.text().strip()
        self._config.site_type = self._site_type_edit.text().strip() or "recettes"
        db_type = self._db_type.currentData()
        db = DbConfig(type=db_type)
        if db_type == "sqlite":
            db.path = self._sqlite_path.text().strip() or "~/recipes.db"
        else:
            db.host = self._db_host.text().strip() or "localhost"
            db.port = self._db_port.value()
            db.database = self._db_name.text().strip()
            db.user = self._db_user.text().strip()
            db.password = self._db_pass.text()
        self._config.db = db
        for key, edit in self._string_edits.items():
            val = edit.text()
            if val:
                self._config.strings[key] = val
        self.accept()

    @property
    def config(self) -> RecipeConfig:
        return self._config
