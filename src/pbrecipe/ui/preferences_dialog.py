from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from pbrecipe.app import apply_log_level
from pbrecipe.config.app_config import AppConfig

_LEVELS = [
    ("Débogage (DEBUG)", "DEBUG", logging.DEBUG),
    ("Informations (INFO)", "INFO", logging.INFO),
    ("Avertissements (WARNING)", "WARNING", logging.WARNING),
]


class PreferencesDialog(QDialog):
    def __init__(self, app_config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app_config = app_config
        self.setWindowTitle("Préférences du programme")
        self.setMinimumWidth(360)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        self._level_combo = QComboBox()
        for label, _name, _int in _LEVELS:
            self._level_combo.addItem(label, _name)
        form.addRow("Niveau de log par défaut :", self._level_combo)
        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load(self) -> None:
        for i, (_label, name, _int) in enumerate(_LEVELS):
            if name == self._app_config.log_level:
                self._level_combo.setCurrentIndex(i)
                break

    def _accept(self) -> None:
        name = self._level_combo.currentData()
        level_int = next(i for _l, n, i in _LEVELS if n == name)
        self._app_config.log_level = name
        self._app_config.save()
        apply_log_level(level_int)
        self.accept()
