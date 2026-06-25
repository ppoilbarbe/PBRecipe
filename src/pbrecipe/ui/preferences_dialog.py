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
    QLineEdit,
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

        self._gram_cb = QCheckBox("Utiliser Grammalecte")
        self._gram_cb.setToolTip(
            "Si Grammalecte est installé, il sera utilisé en priorité.\n"
            "Grammalecte ne traite que le texte en français."
        )
        self._gram_cb.toggled.connect(self._on_gram_toggled)
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

        # ── LanguageTool ───────────────────────────────────────────────
        lt_grp = QGroupBox("LanguageTool")
        lt_layout = QVBoxLayout(lt_grp)

        self._lt_status = QLabel()
        lt_layout.addWidget(self._lt_status)

        self._lt_cb = QCheckBox("Utiliser LanguageTool")
        self._lt_cb.setToolTip(
            "Active la vérification via un serveur LanguageTool.\n"
            "Grammalecte reste prioritaire s'il est activé et installé."
        )
        self._lt_cb.toggled.connect(self._on_lt_toggled)
        lt_layout.addWidget(self._lt_cb)

        lt_url_form = QFormLayout()
        self._lt_url_edit = QLineEdit()
        self._lt_url_edit.setPlaceholderText(
            "https://api.languagetool.org (défaut, API publique)"
        )
        _lt_url_tooltip = (
            "<b>URL du serveur LanguageTool</b><br/><br/>"
            "Laissez vide pour utiliser l'<b>API publique</b> "
            "(<tt>api.languagetool.org</tt>).<br/><br/>"
            "<b>Limites de l'API publique :</b><br/>"
            "&bull;&nbsp;20&nbsp;requêtes par minute<br/>"
            "&bull;&nbsp;20&nbsp;000&nbsp;caractères par requête<br/>"
            "&bull;&nbsp;Le texte transite sur les serveurs LanguageTool<br/><br/>"
            "Pour héberger votre propre serveur (aucune limite, texte local) :<br/>"
            "<tt>docker run -p 8010:8010 erikvl87/languagetool</tt><br/>"
            "puis saisissez&nbsp;<tt>http://localhost:8010</tt> ici."
        )
        self._lt_url_edit.setToolTip(_lt_url_tooltip)
        lt_url_form.addRow("URL du serveur :", self._lt_url_edit)
        lt_layout.addLayout(lt_url_form)

        root.addWidget(lt_grp)
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
        self._refresh_languagetool_status()
        self._lt_cb.setChecked(self._app_config.languagetool_enabled)
        self._lt_url_edit.setText(self._app_config.languagetool_url)
        self._on_lt_toggled(self._app_config.languagetool_enabled)

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
        # Sync install button with checkbox state after status refresh
        self._gram_install_btn.setEnabled(self._gram_cb.isChecked())

    def _on_gram_toggled(self, checked: bool) -> None:
        self._gram_install_btn.setEnabled(checked)

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
        self._gram_install_btn.setEnabled(self._gram_cb.isChecked())

    def _refresh_languagetool_status(self) -> None:
        from pbrecipe.ui.spellcheck_dialog import language_tool_info

        ok, info = language_tool_info()
        if ok:
            self._lt_status.setText(
                f"Module language-tool-python : <b>installé</b> (v{info})"
            )
            self._lt_cb.setEnabled(True)
        else:
            self._lt_status.setText("Module language-tool-python : <b>non installé</b>")
            self._lt_cb.setEnabled(False)
            self._lt_cb.setChecked(False)

    def _on_lt_toggled(self, checked: bool) -> None:
        self._lt_url_edit.setEnabled(checked)

    def _accept(self) -> None:
        from pbrecipe.ui.spellcheck_dialog import reset_lt_tool

        name = self._level_combo.currentData()
        level_int = next(i for _l, n, i in _LEVELS if n == name)
        self._app_config.log_level = name
        self._app_config.php_debug = self._php_debug_cb.isChecked()
        self._app_config.grammalecte_enabled = self._gram_cb.isChecked()
        new_lt_enabled = self._lt_cb.isChecked()
        new_lt_url = self._lt_url_edit.text().strip()
        if (
            new_lt_enabled != self._app_config.languagetool_enabled
            or new_lt_url != self._app_config.languagetool_url
        ):
            reset_lt_tool()
        self._app_config.languagetool_enabled = new_lt_enabled
        self._app_config.languagetool_url = new_lt_url
        self._app_config.save()
        apply_log_level(level_int)
        self.accept()
