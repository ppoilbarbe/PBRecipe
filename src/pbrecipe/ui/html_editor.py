from __future__ import annotations

import re
import xml.dom.minidom
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QAction,
    QFont,
    QPixmap,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

# Tailles de police (pt) pour chaque niveau de titre dans l'éditeur.
_HEADING_SIZES: dict[int, int] = {1: 20, 2: 16, 3: 14, 4: 12}

# Feuille de style appliquée au QTextDocument pour que setHtml() rende les
# titres correctement lorsque le contenu nettoyé est rechargé.
_EDITOR_CSS = "p { margin: 0; } " + " ".join(
    f"h{lvl} {{ font-size: {pt}pt; font-weight: bold; margin: 4px 0; }}"
    for lvl, pt in _HEADING_SIZES.items()
)

# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

_BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.DOTALL | re.IGNORECASE)

# Removes insignificant whitespace (including newlines) between block-level tags.
# Qt's HTML parser creates spurious empty paragraphs from these newlines.
_INTER_BLOCK_WS_RE = re.compile(
    r"(</?(?:p|h[1-6]|ul|ol|li|div|blockquote)(?:\s[^>]*)?>)\s+(?=<)",
    re.IGNORECASE,
)

# Matches an innermost <span> (content contains no other <span> tags).
_SPAN_RE = re.compile(
    r"<span\b([^>]*)>((?:[^<]|<(?!/?span\b))*)</span>",
    re.DOTALL | re.IGNORECASE,
)

# Matches any remaining style="…" attribute on any element.
_STYLE_ATTR_RE = re.compile(r'\s+style="[^"]*"', re.IGNORECASE)


def _style_flags(style: str) -> tuple[bool, bool, bool]:
    """Return (bold, italic, underline) from a CSS style string."""
    bold = bool(re.search(r"font-weight\s*:\s*(bold|[5-9]\d\d)", style, re.I))
    italic = bool(re.search(r"font-style\s*:\s*italic", style, re.I))
    underline = bool(re.search(r"text-decoration[^;]*underline", style, re.I))
    return bold, italic, underline


def _replace_span(m: re.Match) -> str:
    attrs, content = m.group(1), m.group(2)
    style_m = re.search(r'\bstyle="([^"]*)"', attrs, re.I)
    if not style_m:
        return content  # bare span → simple unwrap
    bold, italic, underline = _style_flags(style_m.group(1))
    result = content
    if underline:
        result = f"<u>{result}</u>"
    if italic:
        result = f"<i>{result}</i>"
    if bold:
        result = f"<b>{result}</b>"
    return result


def _clean_html(raw: str) -> str:
    """Nettoie le HTML verbeux de QTextEdit pour ne garder que l'essentiel.

    - Extrait uniquement le contenu entre <body> et </body>.
    - Convertit les spans avec font-weight/font-style/text-decoration
      en balises sémantiques <b>/<i>/<u>.
    - Supprime tous les attributs style= résiduels (marges Qt, etc.).
    """
    if not raw:
        return ""
    m = _BODY_RE.search(raw)
    html = m.group(1).strip() if m else raw

    # Convertit les spans stylisés de l'intérieur vers l'extérieur.
    for _ in range(10):
        new_html = _SPAN_RE.sub(_replace_span, html)
        if new_html == html:
            break
        html = new_html

    # Supprime tous les style="…" résiduels (body, p, li, ul, ol…).
    html = _STYLE_ATTR_RE.sub("", html)

    # Supprime le <b> redondant que Qt ajoute à l'intérieur des balises de titre
    # (le gras y est déjà implicite).
    html = re.sub(
        r"(<h[1-4][^>]*>)\s*<b>(.*?)</b>\s*(</h[1-4]>)",
        r"\1\2\3",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Supprime les espaces/sauts de ligne entre balises de bloc pour éviter que
    # Qt ne crée des paragraphes vides au rechargement.
    html = _INTER_BLOCK_WS_RE.sub(r"\1", html)

    return html


def _pretty_html(html: str) -> str:
    """Indente le HTML avec minidom ; retourne le HTML brut en cas d'erreur."""
    try:
        dom = xml.dom.minidom.parseString(f"<root>{html}</root>")
        pretty = dom.toprettyxml(indent="  ")
        # Supprime la déclaration XML et le <root> englobant
        lines = pretty.splitlines()[2:-1]  # saute <?xml …?> et <root>, retire </root>
        # Dédente d'un niveau (minidom indente <root> à 0, son contenu à 1)
        result = "\n".join(
            line[2:] if line.startswith("  ") else line for line in lines
        )
        return result.strip()
    except Exception:  # noqa: BLE001
        return html


class _HtmlSourceDialog(QDialog):
    """Dialogue d'édition directe du HTML brut."""

    def __init__(self, html: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Éditer le HTML source")
        self.setMinimumSize(640, 480)
        self._html = html
        self._setup_ui(html)

    def _setup_ui(self, html: str) -> None:
        root = QVBoxLayout(self)

        self._editor = QPlainTextEdit()
        self._editor.setPlainText(html)
        font = QFont("Monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._editor.setFont(font)
        root.addWidget(self._editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        self._html = self._editor.toPlainText()
        self.accept()

    @property
    def html(self) -> str:
        return self._html


class _LinkDialog(QDialog):
    """Dialogue de saisie d'un lien HTML externe (URL + texte affiché)."""

    def __init__(self, selected_text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insérer un lien")
        self.setMinimumWidth(420)
        self._url = ""
        self._text = ""
        self._setup_ui(selected_text)

    def _setup_ui(self, selected_text: str) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://…")
        form.addRow("URL :", self._url_edit)

        self._text_edit = QLineEdit(selected_text)
        self._text_edit.setPlaceholderText("Texte affiché (vide = URL)")
        form.addRow("Texte :", self._text_edit)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        url = self._url_edit.text().strip()
        if not url:
            return
        self._url = url
        self._text = self._text_edit.text().strip() or url
        self.accept()

    @property
    def url(self) -> str:
        return self._url

    @property
    def text(self) -> str:
        return self._text


class _RefPickerDialog(QDialog):
    """Dialogue de sélection d'une référence (code + libellé) avec filtre."""

    def __init__(
        self,
        title: str,
        items: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(420, 320)
        self._all_items = items
        self._selected_code: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrer…")
        self._filter.textChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self._list)

        self._populate(self._all_items)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, items: list[tuple[str, str]]) -> None:
        self._list.clear()
        for code, label in items:
            text = f"{code} — {label}" if label else code
            item = QListWidgetItem(text)
            item.setData(0x0100, code)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _apply_filter(self, text: str) -> None:
        low = text.lower()
        self._populate(
            [
                (code, label)
                for code, label in self._all_items
                if low in code.lower() or low in label.lower()
            ]
        )

    def _accept_item(self, item: QListWidgetItem) -> None:
        self._selected_code = item.data(0x0100)
        self.accept()

    def _accept_selection(self) -> None:
        item = self._list.currentItem()
        if item:
            self._selected_code = item.data(0x0100)
            self.accept()

    @property
    def selected_code(self) -> str | None:
        return self._selected_code


class _ImgPickerDialog(QDialog):
    """Dialogue de sélection d'une image : liste filtrée + prévisualisation."""

    _PREVIEW_SIZE = 240

    def __init__(
        self,
        items: list[tuple[str, bytes]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sélectionner une image")
        self.setMinimumSize(580, 360)
        self._all_items = items
        self._selected_code: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)

        content = QHBoxLayout()

        left = QVBoxLayout()
        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filtrer…")
        self._filter.textChanged.connect(self._apply_filter)
        left.addWidget(self._filter)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._accept_item)
        left.addWidget(self._list)
        content.addLayout(left, 1)

        self._preview = QLabel()
        self._preview.setFixedSize(self._PREVIEW_SIZE, self._PREVIEW_SIZE)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFrameShape(QFrame.Shape.StyledPanel)
        content.addWidget(self._preview)

        root.addLayout(content)

        self._populate(self._all_items)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self, items: list[tuple[str, bytes]]) -> None:
        self._list.clear()
        for code, _data in items:
            item = QListWidgetItem(code)
            item.setData(0x0100, code)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _apply_filter(self, text: str) -> None:
        low = text.lower()
        self._populate(
            [(code, data) for code, data in self._all_items if low in code.lower()]
        )

    def _on_selection_changed(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            self._preview.clear()
            return
        code = current.data(0x0100)
        data = next((d for c, d in self._all_items if c == code), b"")
        if data:
            pix = QPixmap()
            pix.loadFromData(data)
            self._preview.setPixmap(
                pix.scaled(
                    self._PREVIEW_SIZE,
                    self._PREVIEW_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self._preview.clear()

    def _accept_item(self, item: QListWidgetItem) -> None:
        self._selected_code = item.data(0x0100)
        self.accept()

    def _accept_selection(self) -> None:
        item = self._list.currentItem()
        if item:
            self._selected_code = item.data(0x0100)
            self.accept()

    @property
    def selected_code(self) -> str | None:
        return self._selected_code


class HtmlEditor(QWidget):
    """Minimal WYSIWYG HTML editor with special-marker insertion.

    Special markers stored in the HTML content:
      [RECIPE:CODE]    — link to another recipe
      [IMG:filename]   — inline image (hover preview on the web)
      [TECH:CODE]      — inline technique reference
    """

    changed = Signal()

    def __init__(self, show_img: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._show_img = show_img
        self._recipes: list[tuple[str, str]] = []
        self._images: list[tuple[str, bytes]] = []
        self._techniques: list[tuple[str, str]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        toolbar = QToolBar()
        toolbar.setIconSize(toolbar.iconSize() * 0.8)

        def _fmt_action(label: str, fmt_fn, tooltip: str = "") -> None:
            act = QAction(label, self)
            if tooltip:
                act.setToolTip(tooltip)
            act.triggered.connect(fmt_fn)
            toolbar.addAction(act)

        _fmt_action("G", self._bold, "Gras")
        _fmt_action("I", self._italic, "Italique")
        _fmt_action("U", self._underline, "Souligné")
        toolbar.addSeparator()
        for lvl in (1, 2, 3, 4):
            _fmt_action(
                f"H{lvl}",
                lambda _checked, lv=lvl: self._heading(lv),
                f"Titre de niveau {lvl}",
            )
        toolbar.addSeparator()
        _fmt_action("• Liste", self._bullet_list, "Liste à puces")
        _fmt_action("1. Liste", self._numbered_list, "Liste numérotée")
        toolbar.addSeparator()
        _fmt_action("[LIEN]", self._insert_link, "Insérer un lien hypertexte")
        _fmt_action(
            "[RECETTE]",
            self._insert_recipe_marker,
            "Insérer un lien vers une autre recette",
        )
        if self._show_img:
            _fmt_action("[IMG]", self._insert_img_marker, "Insérer une image")
        _fmt_action(
            "[TECH]",
            self._insert_tech_marker,
            "Insérer une référence de technique",
        )
        toolbar.addSeparator()
        _fmt_action("</>", self._edit_html_source, "Éditer le HTML source")

        layout.addWidget(toolbar)

        self._edit = QTextEdit()
        self._edit.setAcceptRichText(True)
        self._edit.document().setDefaultStyleSheet(_EDITOR_CSS)
        self._edit.textChanged.connect(self.changed)
        layout.addWidget(self._edit)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_html(self, html: str) -> None:
        html = _INTER_BLOCK_WS_RE.sub(r"\1", html)
        # Without this marker Qt creates a U+2028 line-separator block for
        # <p><br /></p>, which renders as two blank lines instead of one.
        html = html.replace(
            "<p><br /></p>",
            '<p style="-qt-paragraph-type:empty;"><br /></p>',
        )
        self._edit.setHtml(html)

    def get_html(self) -> str:
        result = _clean_html(self._edit.toHtml())
        # Return "" if there's no actual text content (e.g. single empty <p></p>)
        if not re.sub(r"<[^>]+>", "", result).strip():
            return ""
        return result

    def clear(self) -> None:
        self._edit.clear()

    def set_references(
        self,
        recipes: list[tuple[str, str]],
        images: list[tuple[str, bytes]],
        techniques: list[tuple[str, str]],
    ) -> None:
        """Fournit les listes de références disponibles pour les pickers."""
        self._recipes = recipes
        self._images = images
        self._techniques = techniques

    def set_images(self, images: list[tuple[str, bytes]]) -> None:
        self._images = images

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _apply_char_format(self, fmt: QTextCharFormat) -> None:
        cursor = self._edit.textCursor()
        cursor.mergeCharFormat(fmt)
        self._edit.mergeCurrentCharFormat(fmt)

    def _bold(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(
            QFont.Weight.Normal
            if self._edit.currentCharFormat().fontWeight() == QFont.Weight.Bold
            else QFont.Weight.Bold
        )
        self._apply_char_format(fmt)

    def _italic(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self._edit.currentCharFormat().fontItalic())
        self._apply_char_format(fmt)

    def _underline(self) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self._edit.currentCharFormat().fontUnderline())
        self._apply_char_format(fmt)

    def _heading(self, level: int) -> None:
        cursor = self._edit.textCursor()
        new_level = 0 if cursor.blockFormat().headingLevel() == level else level

        # Niveau de bloc (pour l'export HTML correct).
        block_fmt = QTextBlockFormat()
        block_fmt.setHeadingLevel(new_level)
        cursor.mergeBlockFormat(block_fmt)

        # Format de caractères : Qt ne modifie pas visuellement l'éditeur via
        # setHeadingLevel() seul ; il faut forcer taille + graisse explicitement.
        char_fmt = QTextCharFormat()
        if new_level == 0:
            default_pt = self._edit.document().defaultFont().pointSize()
            char_fmt.setFontPointSize(default_pt if default_pt > 0 else 10)
            char_fmt.setFontWeight(QFont.Weight.Normal)
        else:
            char_fmt.setFontPointSize(_HEADING_SIZES[new_level])
            char_fmt.setFontWeight(QFont.Weight.Bold)

        # Appliquer sur tout le bloc sans déplacer le curseur visible.
        block_cursor = QTextCursor(cursor)
        block_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        block_cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        block_cursor.mergeCharFormat(char_fmt)

    def _bullet_list(self) -> None:
        from PySide6.QtGui import QTextListFormat

        cursor = self._edit.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDisc)

    def _numbered_list(self) -> None:
        from PySide6.QtGui import QTextListFormat

        cursor = self._edit.textCursor()
        cursor.insertList(QTextListFormat.Style.ListDecimal)

    # ------------------------------------------------------------------
    # Special markers
    # ------------------------------------------------------------------

    def _insert_marker(self, text: str) -> None:
        self._edit.textCursor().insertText(text)

    def _pick_ref(self, title: str, items: list[tuple[str, str]]) -> str | None:
        dlg = _RefPickerDialog(title, items, self)
        if dlg.exec():
            return dlg.selected_code
        return None

    def _insert_link(self) -> None:
        cursor = self._edit.textCursor()
        selected = cursor.selectedText().replace(" ", " ").strip()
        dlg = _LinkDialog(selected, self)
        if dlg.exec():
            cursor.insertHtml(
                f'<a href="{escape(dlg.url, quote=True)}">{escape(dlg.text)}</a>'
            )

    def _insert_recipe_marker(self) -> None:
        code = self._pick_ref("Sélectionner une recette", self._recipes)
        if code:
            self._insert_marker(f"[RECIPE:{code}]")

    def _insert_img_marker(self) -> None:
        dlg = _ImgPickerDialog(self._images, self)
        if dlg.exec() and dlg.selected_code:
            self._insert_marker(f"[IMG:{dlg.selected_code}]")

    def _insert_tech_marker(self) -> None:
        code = self._pick_ref("Sélectionner une technique", self._techniques)
        if code:
            self._insert_marker(f"[TECH:{code}]")

    def _edit_html_source(self) -> None:
        dlg = _HtmlSourceDialog(_pretty_html(self.get_html()), self)
        if dlg.exec():
            self.set_html(dlg.html)
