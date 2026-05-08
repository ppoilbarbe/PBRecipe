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
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.config.dialog_dirs import DialogDirs
from pbrecipe.config.recipe_config import DbConfig, RecipeConfig
from pbrecipe.constants import MAX_SITE_TYPE


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
        self._site_type_edit.setMaxLength(MAX_SITE_TYPE)
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
        sqlite_row = QHBoxLayout()
        self._sqlite_path = QLineEdit()
        self._sqlite_path.setPlaceholderText("~/recipes.db")
        browse_sqlite_btn = QPushButton("…")
        browse_sqlite_btn.setFixedWidth(30)
        browse_sqlite_btn.clicked.connect(self._browse_sqlite_path)
        sqlite_row.addWidget(self._sqlite_path)
        sqlite_row.addWidget(browse_sqlite_btn)
        sqlite_form.addRow("Fichier :", sqlite_row)
        self._db_stack.addWidget(sqlite_widget)

        # Network DB panel (shared by MariaDB / PostgreSQL)
        net_widget = QWidget()
        net_layout = QVBoxLayout(net_widget)
        net_layout.setContentsMargins(0, 0, 0, 0)

        prog_group = QGroupBox("Accès programme")
        prog_form = QFormLayout(prog_group)
        self._db_host = QLineEdit()
        self._db_port = QSpinBox()
        self._db_port.setRange(1, 65535)
        self._db_name = QLineEdit()
        self._db_user = QLineEdit()
        self._db_pass = QLineEdit()
        self._db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        prog_form.addRow("Hôte :", self._db_host)
        prog_form.addRow("Port :", self._db_port)
        prog_form.addRow("Base :", self._db_name)
        prog_form.addRow("Utilisateur :", self._db_user)
        prog_form.addRow("Mot de passe :", self._db_pass)
        test_btn = QPushButton("Tester la connexion")
        test_btn.clicked.connect(self._test_connection)
        prog_form.addRow("", test_btn)
        net_layout.addWidget(prog_group)

        php_group = QGroupBox("Accès export PHP")
        php_group.setToolTip(
            "Laisser vide pour utiliser les mêmes paramètres que l'accès programme."
        )
        php_form = QFormLayout(php_group)
        self._php_db_host = QLineEdit()
        self._php_db_host.setPlaceholderText("(identique à l'accès programme)")
        self._php_db_port = QSpinBox()
        self._php_db_port.setRange(0, 65535)
        self._php_db_port.setSpecialValueText("(par défaut)")
        self._php_db_user = QLineEdit()
        self._php_db_user.setPlaceholderText("(identique à l'accès programme)")
        self._php_db_pass = QLineEdit()
        self._php_db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._php_db_pass.setPlaceholderText("(identique à l'accès programme)")
        php_form.addRow("Hôte :", self._php_db_host)
        php_form.addRow("Port :", self._php_db_port)
        php_form.addRow("Utilisateur :", self._php_db_user)
        php_form.addRow("Mot de passe :", self._php_db_pass)
        net_layout.addWidget(php_group)

        self._db_stack.addWidget(net_widget)

        db_layout.addWidget(self._db_stack)
        root.addWidget(db_group)

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

    def _browse_sqlite_path(self) -> None:
        start = self._sqlite_path.text()
        if not start and self._dialog_dirs is not None:
            start = self._dialog_dirs.get("sqlite_path")
        path, _ = QFileDialog.getSaveFileName(
            self, "Fichier de base SQLite", start, "SQLite (*.db)"
        )
        if path:
            if not path.lower().endswith(".db"):
                path += ".db"
            self._sqlite_path.setText(path)
            if self._dialog_dirs is not None:
                self._dialog_dirs.record("sqlite_path", path)

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
        self._php_db_host.setText(db.php_host)
        self._php_db_port.setValue(db.php_port)
        self._php_db_user.setText(db.php_user)
        self._php_db_pass.setText(db.php_password)

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
            db.php_host = self._php_db_host.text().strip()
            db.php_port = self._php_db_port.value()
            db.php_user = self._php_db_user.text().strip()
            db.php_password = self._php_db_pass.text()
        self._config.db = db
        self.accept()

    @property
    def config(self) -> RecipeConfig:
        return self._config
