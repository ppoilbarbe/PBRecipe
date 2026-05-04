from __future__ import annotations

import re
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from pbrecipe.database import Database

_MARKER_RE = re.compile(r"\[(IMG|RECIPE|TECH):([A-Z0-9_]+)\]", re.IGNORECASE)


@dataclass
class _BrokenRef:
    kind: str  # 'IMG', 'RECIPE', 'TECH'
    code: str
    field: str  # 'description', 'commentaires'
    label: str = ""  # nom/titre résolu (vide si introuvable)


@dataclass
class _RecipeIssues:
    code: str
    name: str
    refs: list[_BrokenRef] = field(default_factory=list)


@dataclass
class _TechIssues:
    code: str
    title: str
    refs: list[_BrokenRef] = field(default_factory=list)


def run_check(db: Database) -> tuple[list[_RecipeIssues], list[_TechIssues]]:
    recipe_stubs = db.list_recipes()
    tech_stubs = db.list_techniques()

    recipe_codes = {r.code.upper() for r in recipe_stubs}
    tech_codes = {t.code.upper() for t in tech_stubs}

    recipe_name: dict[str, str] = {r.code.upper(): r.name for r in recipe_stubs}
    tech_title: dict[str, str] = {t.code.upper(): t.title for t in tech_stubs}

    media_codes: set[str] = set()
    full_recipes = []
    for stub in recipe_stubs:
        r = db.get_recipe(stub.code)
        if r:
            full_recipes.append(r)
            for m in r.media:
                if m.code:
                    media_codes.add(m.code.upper())

    def _check(text: str, field_name: str) -> list[_BrokenRef]:
        broken = []
        for m in _MARKER_RE.finditer(text or ""):
            kind = m.group(1).upper()
            code = m.group(2).upper()
            if kind == "IMG" and code not in media_codes:
                broken.append(_BrokenRef(kind, code, field_name))
            elif kind == "RECIPE" and code not in recipe_codes:
                broken.append(
                    _BrokenRef(kind, code, field_name, recipe_name.get(code, ""))
                )
            elif kind == "TECH" and code not in tech_codes:
                broken.append(
                    _BrokenRef(kind, code, field_name, tech_title.get(code, ""))
                )
        return broken

    recipe_issues: list[_RecipeIssues] = []
    for r in full_recipes:
        refs = _check(r.description, "description") + _check(r.comments, "commentaires")
        if refs:
            recipe_issues.append(_RecipeIssues(r.code, r.name, refs))

    tech_issues: list[_TechIssues] = []
    for t in tech_stubs:
        refs = _check(t.description, "description")
        if refs:
            tech_issues.append(_TechIssues(t.code, t.title, refs))

    return recipe_issues, tech_issues


# ── HTML report ───────────────────────────────────────────────────────────────

_KIND_META = {
    "IMG": ("image introuvable", "#c05000"),
    "RECIPE": ("recette introuvable", "#2e6b2e"),
    "TECH": ("technique introuvable", "#8a4a00"),
}


def _h(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ref_line(ref: _BrokenRef) -> str:
    label, color = _KIND_META.get(ref.kind, ("?", "#888"))
    display = _h(ref.label) if ref.label else f"<code>{_h(ref.code)}</code>"
    return (
        f'<div class="item">'
        f'<span class="badge" style="background:{color}">{ref.kind}</span>'
        f"{display} — {label}"
        f' <span class="field">[{ref.field}]</span>'
        f"</div>"
    )


def build_report(
    recipe_issues: list[_RecipeIssues], tech_issues: list[_TechIssues]
) -> str:
    n = sum(len(r.refs) for r in recipe_issues) + sum(len(t.refs) for t in tech_issues)
    parts = [
        '<html><head><meta charset="utf-8"><style>'
        "body{font-family:sans-serif;font-size:13px;margin:10px;color:#222}"
        "h1{font-size:15px;color:#8b0000;margin-bottom:8px}"
        "h2{font-size:13px;font-weight:bold;color:#444;"
        "border-bottom:1px solid #ddd;margin:14px 0 5px;padding-bottom:3px}"
        "p.entry{margin:6px 0 2px}"
        ".item{margin:2px 0 2px 16px}"
        ".badge{display:inline-block;border-radius:3px;padding:1px 5px;"
        "font-family:monospace;font-size:11px;color:white;margin-right:4px}"
        "code{font-family:monospace;font-size:12px}"
        ".field{color:#999;font-style:italic;font-size:11px}"
        "</style></head><body>"
        f"<h1>Rapport de cohérence — {n} problème(s) détecté(s)</h1>"
    ]

    if recipe_issues:
        parts.append("<h2>Recettes</h2>")
        for ri in recipe_issues:
            parts.append(f'<p class="entry"><b>{_h(ri.name)}</b></p>')
            for ref in ri.refs:
                parts.append(_ref_line(ref))

    if tech_issues:
        parts.append("<h2>Techniques</h2>")
        for ti in tech_issues:
            parts.append(f'<p class="entry"><b>{_h(ti.title)}</b></p>')
            for ref in ti.refs:
                parts.append(_ref_line(ref))

    parts.append("</body></html>")
    return "".join(parts)


# ── Report dialog (non-modal) ─────────────────────────────────────────────────


class ConsistencyReportDialog(QDialog):
    def __init__(self, html: str, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Rapport de cohérence")
        self.setMinimumSize(640, 460)

        layout = QVBoxLayout(self)

        browser = QTextBrowser()
        browser.setHtml(html)
        browser.setOpenLinks(False)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
