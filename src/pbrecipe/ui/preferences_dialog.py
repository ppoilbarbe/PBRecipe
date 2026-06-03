from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        self._install_proc: QProcess | None = None
        self.setWindowTitle("Préférences du programme")
        self.setMinimumWidth(420)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()
        self._level_combo = QComboBox()
        for label, _name, _int in _LEVELS:
            self._level_combo.addItem(label, _name)
        form.addRow("Niveau de log par défaut :", self._level_combo)
        self._php_debug_cb = QCheckBox("Activer le mode DEBUG PHP")
        self._php_debug_cb.setToolTip(
            "Génère define('SITE_DEBUG', true) dans config.php lors de l'export PHP.\n"
            "Permet l'affichage des erreurs PHP sur le serveur."
        )
        form.addRow("Export PHP :", self._php_debug_cb)
        root.addLayout(form)

        # ── Grammalecte ────────────────────────────────────────────────
        grp = QGroupBox("Vérification grammaticale")
        grp_layout = QVBoxLayout(grp)

        self._gram_status = QLabel()
        grp_layout.addWidget(self._gram_status)

        self._gram_cb = QCheckBox("Utiliser Grammalecte en priorité")
        self._gram_cb.setToolTip(
            "Si Grammalecte est installé, il sera utilisé à la place de LanguageTool."
        )
        grp_layout.addWidget(self._gram_cb)

        btn_row = QHBoxLayout()
        self._gram_install_btn = QPushButton("Installer / Mettre à jour Grammalecte")
        self._gram_install_btn.clicked.connect(self._install_grammalecte)
        btn_row.addWidget(self._gram_install_btn)
        btn_row.addStretch()
        grp_layout.addLayout(btn_row)

        self._gram_install_log = QLabel()
        self._gram_install_log.setWordWrap(True)
        grp_layout.addWidget(self._gram_install_log)

        root.addWidget(grp)
        # ───────────────────────────────────────────────────────────────

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
        self._php_debug_cb.setChecked(self._app_config.php_debug)
        self._refresh_grammalecte_status()
        self._gram_cb.setChecked(self._app_config.grammalecte_enabled)

    def _refresh_grammalecte_status(self) -> None:
        from pbrecipe.ui.spellcheck_dialog import grammalecte_info

        ok, info = grammalecte_info()
        if ok:
            self._gram_status.setText(f"Grammalecte : <b>installé</b> (v{info})")
            self._gram_cb.setEnabled(True)
        else:
            self._gram_status.setText("Grammalecte : <b>non installé</b>")
            self._gram_cb.setEnabled(False)
            self._gram_cb.setChecked(False)

    def _install_grammalecte(self) -> None:
        if self._install_proc is not None:
            return
        self._gram_install_btn.setEnabled(False)
        self._gram_install_log.setText("Installation en cours…")
        proc = QProcess(self)
        proc.setProgram(sys.executable)
        proc.setArguments(["-m", "pip", "install", "--upgrade", "pygrammalecte"])
        proc.finished.connect(self._on_install_finished)
        proc.readyReadStandardError.connect(
            lambda: self._gram_install_log.setText(
                proc.readAllStandardError()
                .data()
                .decode(errors="replace")
                .strip()[-300:]
            )
        )
        self._install_proc = proc
        proc.start()

    def _on_install_finished(self, exit_code: int, _exit_status) -> None:
        self._install_proc = None
        self._gram_install_btn.setEnabled(True)

        from pbrecipe.ui.spellcheck_dialog import grammalecte_info

        ok, info = grammalecte_info()
        if exit_code == 0 and ok:
            self._gram_install_log.setText(f"Installation réussie (v{info}).")
            self._gram_cb.setEnabled(True)
            self._gram_cb.setChecked(True)
            self._gram_status.setText(f"Grammalecte : <b>installé</b> (v{info})")
        else:
            msg = info if not ok else f"pip a retourné le code {exit_code}."
            self._gram_install_log.setText(f"Échec : {msg}")
            self._gram_cb.setEnabled(False)
            self._gram_cb.setChecked(False)
            self._gram_status.setText("Grammalecte : <b>non installé</b>")
            self._app_config.grammalecte_enabled = False
            self._app_config.save()

    def _accept(self) -> None:
        name = self._level_combo.currentData()
        level_int = next(i for _l, n, i in _LEVELS if n == name)
        self._app_config.log_level = name
        self._app_config.php_debug = self._php_debug_cb.isChecked()
        self._app_config.grammalecte_enabled = self._gram_cb.isChecked()
        self._app_config.save()
        apply_log_level(level_int)
        self.accept()
