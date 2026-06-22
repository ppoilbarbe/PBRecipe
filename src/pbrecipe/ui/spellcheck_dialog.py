"""Vérification orthographique et grammaticale via Grammalecte ou LanguageTool."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import re
from html import escape, unescape

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

_log = logging.getLogger(__name__)

_MARKER_RE = re.compile(r"\[(IMG|TECH|RECIPE):[^\]]+\]", re.IGNORECASE)
_BLOCK_TAG_RE = re.compile(r"</?(p|br|div|li|h[1-6]|tr|td|th)[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_MULTI_NL_RE = re.compile(r"\n{3,}")
_EMPTY_COMMA_RE = re.compile(r",\s*,|\[\s*,|,\s*\]")


def _patch_pygrammalecte() -> None:
    """Patch pygrammalecte bugs:
    1. Empty paragraphs produce invalid JSON arrays (bEmptyIfNoErrors=True).
    2. Spelling suggestions are disabled (bSpellSugg=False hard-coded).
    """
    try:
        import json as _json
        from pathlib import Path
        from sysconfig import get_paths

        import pygrammalecte.pygrammalecte as _pg

        def _fixed(json_str: str):
            # Strip grammalecte comment lines (grammalecte 1.12+ adds # lines)
            cleaned = "\n".join(
                line for line in json_str.splitlines() if not line.startswith("#")
            )
            # Fix empty array elements produced when some paragraphs have no errors:
            # getParagraphErrorsAsJSON(bEmptyIfNoErrors=True) returns "" for
            # error-free paragraphs; joining with ",\n" then yields invalid JSON.
            # Each re.sub pass removes one "layer" of consecutive empty elements,
            # so loop until the string is stable (handles N consecutive empties).
            while True:
                prev = cleaned
                cleaned = re.sub(r",\s*,", ",", cleaned)  # collapse ,,
                cleaned = re.sub(r"\[\s*,", "[", cleaned)  # remove leading ,
                cleaned = re.sub(r",\s*\]", "]", cleaned)  # remove trailing ,
                if cleaned == prev:
                    break
            warnings = _json.loads(cleaned)
            for warning in warnings["data"]:
                lineno = int(warning["iParagraph"])
                messages = []
                for error in warning["lGrammarErrors"]:
                    messages.append(
                        _pg.GrammalecteGrammarMessage.from_dict(lineno, error)
                    )
                for error in warning["lSpellingErrors"]:
                    msg = _pg.GrammalecteSpellingMessage.from_dict(lineno, error)
                    msg.suggestions = error.get("aSuggestions", [])
                    messages.append(msg)
                yield from sorted(messages)

        _pg._convert_to_messages = _fixed

        # Enable spelling suggestions (bSpellSugg is False in the original)
        def _run_with_suggestions(filepath: str) -> str:
            grammalecte_script = Path(get_paths()["scripts"]) / "grammalecte-cli.py"
            if not grammalecte_script.exists():
                exc = FileNotFoundError()
                exc.filename = "grammalecte-cli.py"
                raise exc
            import grammalecte as _gc
            from grammalecte.grammalecte_cli import generateParagraphFromFile

            warnings_list = []
            oGC = _gc.GrammarChecker("fr")  # noqa: N806
            oGC.gce.setOptions({"html": True, "latex": True, "apos": False})
            for i, sText, lLineSet in generateParagraphFromFile(filepath, False):  # noqa: N806
                sText = oGC.getParagraphErrorsAsJSON(  # noqa: N806
                    i,
                    sText,
                    bContext=False,
                    bEmptyIfNoErrors=True,
                    bSpellSugg=True,
                    bReturnText=False,
                    lLineSet=lLineSet,
                )
                warnings_list.append(sText)
            warnings = ",\n".join(warnings_list)
            return f'{{"data": [\n{warnings}\n]}}'

        _pg._run_grammalecte = _run_with_suggestions
    except Exception:  # noqa: BLE001
        pass


def _html_to_plain(html: str) -> str:
    """Convert Qt rich-text HTML to plain text for spell-checkers."""
    text = _STYLE_RE.sub("", html)
    text = _BLOCK_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = _MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


_lt_tool = None  # lazy singleton LanguageTool
_spellcheck_dialog: SpellCheckDialog | None = None  # non-modal singleton


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

        _patch_pygrammalecte()
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
    """Ouvre (ou met à jour) la fenêtre de vérification orthographique non modale."""
    global _spellcheck_dialog

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

    if _spellcheck_dialog is not None and _spellcheck_dialog.isVisible():
        _spellcheck_dialog.update_check(sections, engine)
        _spellcheck_dialog.raise_()
        _spellcheck_dialog.activateWindow()
    else:
        # Parent=None : fenêtre indépendante dont la durée de vie n'est pas
        # liée à la fenêtre appelante (évite un crash si l'appelant est détruit)
        _spellcheck_dialog = SpellCheckDialog(sections, engine)
        _spellcheck_dialog.show()


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

    def update_check(self, sections: list[tuple[str, str]], engine: str) -> None:
        """Met à jour le contenu sans ouvrir une nouvelle fenêtre."""
        self._sections = sections
        self._engine = engine
        engine_label = "Grammalecte" if engine == "grammalecte" else "LanguageTool"
        self.setWindowTitle(
            f"Vérification orthographique et grammaticale — {engine_label}"
        )
        self._run_check()

    def _run_check(self) -> None:
        self._browser.setHtml("<p><i>Vérification en cours…</i></p>")
        QApplication.processEvents()
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
            clean = _html_to_plain(_MARKER_RE.sub("", text))
            if not clean:
                continue
            any_text = True
            _log.debug("Grammalecte — section «%s» :\n%s", label, clean)
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
                    suggestions = list(getattr(m, "suggestions", []))
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
            clean = _html_to_plain(_MARKER_RE.sub("", text))
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
