"""Vérification orthographique et grammaticale via Grammalecte ou LanguageTool."""

from __future__ import annotations

import importlib
import importlib.metadata
import re
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

_MARKER_RE = re.compile(r"\[(IMG|TECH|RECIPE):[^\]]+\]", re.IGNORECASE)

_lt_tool = None  # lazy singleton LanguageTool


# ──────────────────────────────────────────────────────────────────────────────
# Détection des correcteurs disponibles


def grammalecte_info() -> tuple[bool, str]:
    """Retourne (disponible, version_ou_erreur).

    La version retournée est celle de grammalecte embarqué (ex. 2.1.1),
    pas celle du wrapper pygrammalecte.
    """
    try:
        importlib.invalidate_caches()
        import pygrammalecte  # noqa: F401
        from pygrammalecte import grammalecte_text

        list(grammalecte_text("Test."))
        try:
            import grammalecte.fr as _gfr

            version = str(_gfr.version)
        except Exception:  # noqa: BLE001
            version = "?"
        return True, version
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def language_tool_info() -> tuple[bool, str]:
    """Retourne (disponible, version_ou_erreur)."""
    try:
        import language_tool_python  # noqa: F401

        try:
            version = importlib.metadata.version("language-tool-python")
        except importlib.metadata.PackageNotFoundError:
            version = "?"
        return True, version
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


# ──────────────────────────────────────────────────────────────────────────────
# Point d'entrée public


def run_spellcheck(
    sections: list[tuple[str, str]],
    parent: QWidget | None = None,
) -> None:
    """Ouvre le dialogue, ou avertit si aucun correcteur n'est disponible."""
    from pbrecipe.config.app_config import AppConfig

    app_config = AppConfig.load()

    use_grammalecte = app_config.grammalecte_enabled
    gram_ok, _ = grammalecte_info() if use_grammalecte else (False, "")
    lt_ok, _ = language_tool_info()

    if use_grammalecte and gram_ok:
        engine = "grammalecte"
    elif lt_ok:
        engine = "languagetool"
    else:
        _no_checker_warning(parent, use_grammalecte)
        return

    SpellCheckDialog(sections, engine, parent).exec()


def _no_checker_warning(parent: QWidget | None, grammalecte_preferred: bool) -> None:
    if grammalecte_preferred:
        msg = (
            "Ni Grammalecte ni LanguageTool ne sont disponibles.\n\n"
            "Pour installer Grammalecte :\n"
            "    pip install pygrammalecte\n\n"
            "Pour installer LanguageTool (requiert Java) :\n"
            "    pip install language-tool-python"
        )
    else:
        msg = (
            "Le module « language-tool-python » n'est pas installé.\n\n"
            "Pour l'installer :\n"
            "    pip install language-tool-python\n\n"
            "Note : Java (JRE 8+) est également requis.\n\n"
            "Vous pouvez aussi activer Grammalecte dans les Préférences."
        )
    QMessageBox.warning(parent, "Aucun correcteur disponible", msg)


# ──────────────────────────────────────────────────────────────────────────────
# Dialogue de résultats


class SpellCheckDialog(QDialog):
    def __init__(
        self,
        sections: list[tuple[str, str]],
        engine: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._sections = sections
        self._engine = engine
        engine_label = "Grammalecte" if engine == "grammalecte" else "LanguageTool"
        self.setWindowTitle(
            f"Vérification orthographique et grammaticale — {engine_label}"
        )
        self.setMinimumSize(700, 500)
        self._setup_ui()
        self._run_check()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        self._browser = QTextBrowser()
        self._browser.setHtml("<p><i>Vérification en cours…</i></p>")
        root.addWidget(self._browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _run_check(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self._engine == "grammalecte":
                html = self._build_report_grammalecte()
            else:
                html = self._build_report_languagetool()
        finally:
            QApplication.restoreOverrideCursor()
        self._browser.setHtml(html)

    # ------------------------------------------------------------------
    # Grammalecte

    def _build_report_grammalecte(self) -> str:
        from pygrammalecte import (
            GrammalecteGrammarMessage,
            GrammalecteSpellingMessage,
            grammalecte_text,
        )

        parts: list[str] = []
        any_text = False

        for label, text in self._sections:
            clean = _MARKER_RE.sub("", text).strip()
            if not clean:
                continue
            any_text = True
            matches = list(grammalecte_text(clean))
            parts.append(f"<h3>{escape(label)}</h3>")
            if not matches:
                parts.append("<p><i>Aucun problème détecté.</i></p>")
                continue
            lines = clean.split("\n")
            for m in matches:
                line_text = lines[m.line - 1] if 1 <= m.line <= len(lines) else ""
                if isinstance(m, GrammalecteGrammarMessage):
                    error_text = line_text[m.start : m.end]
                    message = m.message
                    suggestions = list(m.suggestions)
                elif isinstance(m, GrammalecteSpellingMessage):
                    error_text = m.word
                    message = m.message
                    suggestions = []
                else:
                    continue
                ctx = _build_context(line_text, m.start, len(error_text))
                sugg_html = (
                    ", ".join(f"<i>{escape(s)}</i>" for s in suggestions[:5])
                    or "<i>(aucune suggestion)</i>"
                )
                parts.append(_format_match(message, ctx, sugg_html))

        if not any_text:
            return "<p><i>Aucun texte à vérifier.</i></p>"
        return "".join(parts)

    # ------------------------------------------------------------------
    # LanguageTool

    def _build_report_languagetool(self) -> str:
        global _lt_tool  # noqa: PLW0603
        import language_tool_python

        if _lt_tool is None:
            _lt_tool = language_tool_python.LanguageTool("fr")

        parts: list[str] = []
        any_text = False

        for label, text in self._sections:
            clean = _MARKER_RE.sub("", text).strip()
            if not clean:
                continue
            any_text = True
            matches = _lt_tool.check(clean)
            parts.append(f"<h3>{escape(label)}</h3>")
            if not matches:
                parts.append("<p><i>Aucun problème détecté.</i></p>")
                continue
            for m in matches:
                ctx = _build_context(clean, m.offset, m.errorLength)
                sugg_html = (
                    ", ".join(f"<i>{escape(r)}</i>" for r in m.replacements[:5])
                    or "<i>(aucune suggestion)</i>"
                )
                parts.append(_format_match(m.message, ctx, sugg_html))

        if not any_text:
            return "<p><i>Aucun texte à vérifier.</i></p>"
        return "".join(parts)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers


def _build_context(text: str, offset: int, length: int) -> str:
    ctx_start = max(0, offset - 40)
    ctx_end = min(len(text), offset + length + 40)
    return (
        ("…" if ctx_start > 0 else "")
        + escape(text[ctx_start:offset])
        + f"<u><b>{escape(text[offset : offset + length])}</b></u>"
        + escape(text[offset + length : ctx_end])
        + ("…" if ctx_end < len(text) else "")
    )


def _format_match(message: str, ctx: str, sugg_html: str) -> str:
    return (
        '<div style="margin-bottom:10px;padding:8px;'
        'background:#fff8f8;border-left:3px solid #cc4444;">'
        f"<b>{escape(message)}</b><br/>"
        f'<code style="font-size:0.95em">{ctx}</code><br/>'
        f"Suggestion(s) : {sugg_html}"
        "</div>"
    )
