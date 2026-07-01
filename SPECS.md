# PBRecipe — Specifications

## Stack
- Python 3.12, PySide6, ruamel.yaml (YAML 1.2), SQLAlchemy ≥ 2.0, PyMySQL, psycopg2
- DB: SQLite | MariaDB | PostgreSQL (configurable)
- Web: PHP + PDO (MySQL/PgSQL/SQLite)
- Build: conda (`pbrecipe`), hatchling, `make`

## Program configuration files

Stored in `$XDG_CONFIG_HOME/pbrecipe/` (default: `~/.config/pbrecipe/`).

### `app.yaml` — program preferences

```yaml
recent_files:
  - /path/to/recipes.yaml
log_level: INFO          # DEBUG | INFO | WARNING
window_geometry:         # main window position/size; restored at startup
  x: 100
  y: 50
  width: 1200
  height: 800
splitter_sizes:          # recipe list / editor panel widths
  - 220
  - 640
```

Loaded at startup by `AppConfig.load()`. Editable via the **Préférences** dialogue.
`window_geometry` and `splitter_sizes` are written in `closeEvent` and restored in `_setup_ui`.

### `dialog_dirs.yaml` — last directories for file dialogues

```yaml
new_config: /home/…
open_config: /home/…
export_php: /home/…
php_export_dir: /home/…
export_yaml: /home/…
import_yaml: /home/…
```

Updated automatically after each file/directory dialogue confirmation.
Each dialogue opens in the last directory used for that key.

## Recipe database YAML config

YAML 1.2 file opened at startup or created via dialogue.

```yaml
name: "Mes Recettes"
site_type: recettes      # passed to SITE_TYPE in config.php (host site integration)
php_export_dir: /path/export   # optional; absent if not set
db:
  type: sqlite          # sqlite | mariadb | postgresql
  path: ~/recipes.db    # SQLite only
  host: localhost        # MariaDB / PostgreSQL
  port: 3306
  database: recipes
  user: ""
  password: ""
strings:                 # recipe-type-specific labels
  window_title: ...
  recipe_singular: ...
  serving_label: Quantité   # label for the serving/quantity field
  # + ~15 other keys (UI and website labels)
  # Difficulty labels and icons are now stored in the database (difficulty_levels table)
```

## DB schema

```
categories(id PK, name ≤20 NN)
units(id PK, name ≤15, name_plural ≤15 DEF'')  # name may be empty; name_plural: plural form
ingredients(id PK, name ≤50 NN,
            name_plural ≤50 DEF'')              # name_plural: optional plural form
sources(id PK, name TEXT NN)                   # TEXT (no length limit), may contain HTML
techniques(code ≤10 PK, title ≤200 NN, description TEXT)
difficulty_levels(level 0-3 PK, label ≤50 DEF'',
                  hide_label BOOLEAN DEF False,  # hide label, keep icon + tooltip
                  mime_type ≤50 DEF'image/jpeg',
                  data BLOB?)                    # bitmap icon; NULL if not defined
recipes(code ≤50 PK, name ≤200 NN, difficulty 0-3 DEF 0,
        serving ≤30 DEF'',
        prep_time INT?, wait_time INT?,
        description TEXT, comments TEXT, source_id→sources)
recipe_categories(recipe_code→recipes, category_id→categories, composite PK)
recipe_ingredients(id PK, recipe_code→recipes, position,
                   prefix ≤10 DEF'', quantity ≤10 DEF'1',
                   unit_id→units?, unit_plural BOOL DEF False,
                   separator ≤20 DEF'',
                   ingredient_id→ingredients?, ingredient_plural BOOL DEF False,
                   suffix ≤20 DEF'')
recipe_media(id PK, recipe_code→recipes, position,
             code ≤20 NN,        # reference in [IMG:CODE]
             mime_type ≤50 NN DEF'image/jpeg',
             data BLOB NN)       # binary image data
```

All FKs: ON DELETE CASCADE (children) or SET NULL (optional refs).
SQLAlchemy `LargeBinary` → BLOB (SQLite) / LONGBLOB (MariaDB) / BYTEA (PostgreSQL).

Migration at schema creation:
- If `difficulty_levels` is empty → insert 4 default levels (0 empty, 1 Facile, 2 Moyen, 3 Difficile).
- If column `recipe_media.filename` exists → drop it (obsolete column).
- If column `recipes.serving` is absent → `ALTER TABLE recipes ADD COLUMN serving VARCHAR(30) NOT NULL DEFAULT ''`.
- v3: if `units.name_plural`, `ingredients.name_plural`, `recipe_ingredients.unit_plural` or
  `recipe_ingredients.ingredient_plural` are absent → `ALTER TABLE … ADD COLUMN …`.
- v4: `_ensure_bool_columns()` — if `difficulty_levels.hide_label` is absent →
  `ALTER TABLE difficulty_levels ADD COLUMN hide_label BOOLEAN NOT NULL DEFAULT FALSE`.

Sorting of all lists: done on the Python side via `_sort_key()` (case- and
diacritics-insensitive: `unicodedata.normalize("NFD").casefold().encode("ascii","ignore")`).
SQL queries contain no `ORDER BY`.

## Special markers (HTML description/comments/techniques)
| Marker | Insertion | PHP rendering |
|---|---|---|
| `[RECIPE:CODE]` | picker from recipe list CODE — name | link `?RECIPE=CODE` |
| `[IMG:CODE]` | picker list + 240 px preview | `<img>` resolved via `$MEDIA_INDEX[CODE]` (manifest generated at export) |
| `[TECH:CODE]` | picker list CODE — title | anchor to technique panel |
| `<a href="URL">` | URL + display text dialogue | direct HTML link |

`[IMG]` absent in the technique editor (images belong to recipes, not techniques).
Techniques: recursive resolution with anti-loop guard (`resolve_techniques(html, seen[])`).

## HTML stored in database — clean format

`get_html()` applies `_clean_html()` on the verbose HTML produced by `QTextEdit.toHtml()`
before any storage (DB or export). Cleaning rules in order:

1. **Body extraction**: only content between `<body>` and `</body>` is kept
   (removes DOCTYPE, `<head>`, `<style>`, `<body>` attributes).
2. **Inter-block whitespace removal**: `_INTER_BLOCK_WS_RE` removes spaces/line breaks
   between block tags (`<p>`, `<h1>`–`<h6>`, `<ul>`, `<ol>`, `<li>`, `<div>`,
   `<blockquote>`) to prevent Qt from generating empty paragraphs on reload.
3. **Styled `<span>` conversion** (iterative passes from inner to outer):
   - `font-weight: 500–900` or `bold` → `<b>`
   - `font-style: italic` → `<i>`
   - `text-decoration: … underline …` → `<u>`
   - Combinations in a single span → nested tags `<b><i>…</i></b>` etc.
   - `<span>` without `style=` or whose style contains none of the above properties
     → content extracted (span removed).
4. **Removal of all residual `style="…"`** on every element
   (Qt margins, `-qt-block-indent`, font sizes, colours, etc.).
5. **Redundant `<b>` inside headings**: `<h1><b>…</b></h1>` → `<h1>…</h1>`
   (bold is already implicit in `<h1>`–`<h4>` tags).
6. **Empty content**: `get_html()` returns `""` if the cleaned HTML contains no visible text
   (e.g. a bare `<p></p>` leftover from an empty editor).

`set_html()` also applies `_INTER_BLOCK_WS_RE` on input and replaces `<p><br /></p>` with
`<p style="-qt-paragraph-type:empty;"><br /></p>` to avoid spurious Qt double line breaks.

Preserved tags: `<p>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<h1>`–`<h4>`,
`<a href="…">`, `<b>`, `<i>`, `<u>`, and the markers `[RECIPE:…]` `[IMG:…]` `[TECH:…]`.

PHP (`display.php`) inserts this HTML directly into `<div class="recipe-body">` and
styles it exclusively via CSS classes — no inline styles on the PHP side.

## Command line

```
python -m pbrecipe [FILE] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `FILE` | YAML configuration file to open at startup |
| `--export-php [DIRECTORY]` | PHP export without graphical interface. If DIRECTORY is omitted, uses `php_export_dir` from the configuration; error if not set. |
| `--debug` | Log level DEBUG (detailed messages) |
| `--verbose` | Log level INFO (default) |
| `--quiet` | Log level WARNING (warnings and errors only) |

The `--debug`/`--verbose`/`--quiet` options override the default level for the current
session without modifying `app.yaml`.

## Logging

- Default level: `INFO`, read from `app.yaml` at startup.
- DEBUG format: `%(asctime)s %(levelname)-8s %(name)s: %(message)s`
- INFO/WARNING format: `%(levelname)s: %(message)s`
- Reconfigurable live via the **Préférences** dialogue (no restart needed).
- `apply_log_level(level)` updates the root logger and all its handlers immediately.

## Python architecture (`src/pbrecipe/`)

```
__init__.py / __main__.py
app.py                      main(), apply_log_level(), _headless_export()
                            argparse: FILE, --export-php, --debug/--verbose/--quiet
config/
  __init__.py
  app_config.py             AppConfig — recent_files, log_level, dialog_dirs,
                                        window_geometry (dict), splitter_sizes (list[int])
                            load/save → ~/.config/pbrecipe/app.yaml
                            window_geometry and splitter_sizes saved in closeEvent,
                            restored in _setup_ui at startup.
  dialog_dirs.py            DialogDirs — remembers the last directory per dialogue key
                            get(key)/record(key, chosen, is_dir=False) — immediate save
                            load/save → ~/.config/pbrecipe/dialog_dirs.yaml
  recipe_config.py          RecipeConfig, DbConfig — load/save YAML
                            fields: name, db, strings, php_export_dir, site_type
                            site_type: free string passed to SITE_TYPE in config.php
                            serving_label added to _DEFAULT_STRINGS
database/
  schema.py                 MetaData + SQLAlchemy Tables (dialect-agnostic)
                            LargeBinary for recipe_media.data
                            sources.name: Text (no fixed length)
                            recipes: serving VARCHAR(30) NOT NULL DEFAULT '' column
  database.py               Database — single class, SQLAlchemy Core, engine.begin()
                            SQLite: "connect" event → PRAGMA foreign_keys=ON
                            _safe_url() masks password in logs
                            _sort_key(s): case+diacritics-insensitive sort (Python-side)
                            All list_*() sort by _sort_key (no ORDER BY in SQL)
                            sources: sorted on name stripped of HTML tags
                            list/get/save_difficulty_level(); auto-seed in _migrate()
                            Migration _migrate(): serving column if absent
  factory.py                create_database(config) → Database(url)
                            urls: sqlite:///path | mysql+pymysql://… | postgresql+psycopg2://…
models/
  recipe.py                 Recipe, RecipeIngredient, RecipeMedia (dataclasses)
                            Recipe: serving: str = "" field (quantity/servings, max 30 chars)
                            RecipeMedia: code, mime_type, data:bytes
  difficulty.py             DifficultyLevel (level, label, mime_type, data:bytes|None)
  category/ingredient/unit/source/technique.py
ui/
  main_window.py            QMainWindow: recipe list (left) + editor (right)
                            Splitter stored in self._splitter; sizes restored from app.yaml.
                            Window position/size restored from app.yaml (window_geometry).
                            Automatic loading of the last file at startup.
                            Confirmation before discarding unsaved changes
                            (navigation, close).
                            Filter below the list: QLineEdit + ✕ button; _normalize_filter()
                              (NFD casefold, strip 'Mn' category); _apply_recipe_filter() hides
                              items via setHidden(); the recipe selected by code remains
                              always visible.
                            Menus:
                              Fichier   → Nouvelle base… (Ctrl+N) | Ouvrir… (Ctrl+O)
                                          | Fichiers récents
                                          ── Export PHP… | Export PHP sous…
                                          ── Exporter YAML… | Exporter YAML sous…
                                             Importer YAML…
                                          ── Quitter
                              Recette   → Nouvelle recette (Ctrl+R)
                                          Copier la recette… (Ctrl+Shift+R)
                                          Supprimer la recette
                                          ── Enregistrer la recette (Ctrl+S)
                              Référentiels → Catégories… | Ingrédients… | Unités…
                                             Techniques… | Sources…
                                             Niveaux de difficulté…
                                             ── Vérifier la cohérence
                              Outils    → Paramètres de la base… | Contenu et apparence…
                                          Médias…
                                          ── Préférences du programme…
                              Aide      → À propos…
                            Toolbars (SVG icons from resources/icons/):
                              tb_db:     [db-settings] [db-globals]
                              tb_php:    [export-php] [export-php-as]
                              tb_yaml:   [export-yaml] [export-yaml-as] [import-yaml]
                              tb_recipe: [new] [duplicate] [delete]
                              tb_ref:    [recipe-categories] [ingredients] [units]
                                         [recipe-techniques] [recipe-sources] [difficulty]
                                         [consistency]
                            Menu-only icons (not in toolbar):
                              [new]                → Nouvelle base…
                              [open]               → Ouvrir…
                              [save]               → Enregistrer la recette
                              [medias]             → Médias…
                              [preferences-system] → Préférences du programme…
                              [help-about]         → À propos…
  recipe_editor.py          QTabWidget: Informations | Ingrédients | Réalisation | Commentaires | Médias
                            Informations tab: Quantité field (QLineEdit ≤30 chars, serving)
                              before Difficulté in the meta form.
                            _slugify(name) → CODE (ASCII upper, spaces→_)
                            Save button: disabled until a change is made.
                            "Enregistrer la recette" action (QAction) with Ctrl+S shortcut,
                              shared between the Recette menu and the Save button.
                            "Vérifier…" button (F7 shortcut): launches spell check
                              on Réalisation + Commentaires via run_spellcheck().
                            Validation on save: at least one category required
                            (error message + cancellation if none selected).
                            Source combo: display without HTML tags (re.sub r"<[^>]+>").
                            reload_references(): public method; reloads categories, sources,
                              ingredient_editor and html_editor references without reloading
                              the recipe; called from main_window after editing a reference item.
                            _reload_editor_references(recipe, db): called at each load();
                              populates desc_editor and comment_editor via set_references():
                              recipes=db.list_recipes(), images=[(m.code, m.data) for m in
                              recipe.media], techniques=db.list_techniques().
  ingredient_list_editor.py Scrollable rows: ↑ ↓ + − | prefix/qty/unit/[Pl.]/sep/ingredient/[Pl.]/suffix
                            Per-row buttons (left): ↑ move up (disabled at 1st pos),
                              ↓ move down (disabled at last pos), + insert after, − delete.
                            + button alone shown when the list is empty (_empty_btn).
                            Old "Ajouter/Supprimer dernier" toolbar removed.
                            "Pl." checkboxes: enable unit_plural / ingredient_plural per row
                              (uses name_plural if checked and the plural form is set).
                            reload(db): reloads unit/ingredient lists for each row
                              without losing entered values (used by reload_references()).
  html_editor.py            QTextEdit WYSIWYG.
                            Toolbar: G | I | U | H1 | H2 | H3 | H4 | • Liste | 1. Liste |
                                      [LIEN] | [RECETTE] | [IMG] | [TECH]
                            ([IMG] hidden if show_img=False)
                            Headings H1–H4: setHeadingLevel() + QTextCharFormat (size+bold)
                              explicit because Qt does not update visual rendering alone.
                              _HEADING_SIZES = {1:20, 2:16, 3:14, 4:12} pt.
                              Repeated click on the same level → back to normal paragraph.
                              _EDITOR_CSS: "p { margin: 0; } h1 { … } h2 { … } …"
                              applied via document().setDefaultStyleSheet().
                            [LIEN]: _LinkDialog (URL + display text, text pre-filled
                              from selection); insertHtml('<a href="...">...</a>').
                              URL and text escaped with html.escape().
                            Reference pickers (substitute for QInputDialog):
                              _RefPickerDialog(title, [(code,label)]) — filtered list,
                                double-click or OK; recipes and techniques.
                              _ImgPickerDialog([(code,bytes)]) — filtered list + preview
                                panel QLabel 240×240 px updated at selection via
                                QPixmap.loadFromData().
                            set_references(recipes, images, techniques): populated at
                              each recipe load from DB.
                              images = [(code, data:bytes)] of the recipe media.
                              Absent in TechniqueEditDialog (images=[] + show_img=False).
                            get_html() calls _clean_html(toHtml()) before returning.
                              Returns "" if the result contains no visible text.
                            set_html(html): applies _INTER_BLOCK_WS_RE + Qt empty-p patch
                              before setHtml() to avoid spurious empty paragraphs.
  media_tab.py              _MediaFileDialog: QFileDialog (DontUseNativeDialog) with a
                              240 px preview panel grafted onto the dialogue grid;
                              updated via the currentChanged(path) signal.
                            MediaTab: QSplitter list (80×80 thumbnails) + full-size preview;
                              after file selection → QInputDialog for the code (pre-filled
                              from the filename); buttons Ajouter… Supprimer Exporter… ↑ ↓
                            Exporter…: writes media.data to a file chosen via QFileDialog;
                              extension inferred from mime_type and added automatically if absent.
                            Accepted formats: JPEG, PNG, GIF, WebP, BMP (images only).
                            Videos not supported: the Qt6 multimedia backend (GStreamer/FFmpeg)
                              is required to generate thumbnails but is absent/non-functional.
  about_dialog.py           AboutDialog: 64×64 icon + title + version + description
                              author and version read from importlib.metadata("pbrecipe")
                              displays Python X.Y.Z · PySide6 X.Y.Z
  config_dialog.py          Database settings: name, PHP export directory (with Parcourir…
                            button), DB type (SQLite path | host/port/db/user/pass),
                            all strings (difficulty_* keys no longer part of strings)
  preferences_dialog.py     Program preferences: default log level (dropdown
                            DEBUG/INFO/WARNING) — applied immediately via apply_log_level()
  dialogs/
    _base_list_dialog.py    generic list+add+edit+delete (QInputDialog)
                              double-click on an item → inline editing
    category/source_dialog.py  (5 lines each)
    ingredient_dialog.py    dedicated dialogue: Nom + Nom pluriel fields (QLineEdit ≤50 chars)
    unit_dialog.py          dedicated dialogue: Nom + Nom pluriel fields (QLineEdit ≤15 chars)
    technique_dialog.py     TechniqueDialog: technique list + TechniqueEditDialog
                              double-click on an item → inline editing
                            TechniqueEditDialog (code+title+HtmlEditor(show_img=False))
                              receives db → set_references(recipes, [], techniques)
                              [IMG] absent: images belong to recipes
                              "Vérifier…" button (F7 shortcut): spell check
                              on Titre + Description via run_spellcheck()
    difficulty_dialog.py    DifficultyDialog: split panel — fixed 4-level list (left)
                              + editor (right): label + "Masquer le libellé" checkbox +
                              bitmap icon preview + Charger/Supprimer
                              immediate save to DB on each change
  spellcheck_dialog.py      run_spellcheck(sections, parent) — non-modal singleton window;
                              a 2nd click on "Vérifier…" updates content without a new window.
                            _html_to_plain(html): converts Qt HTML to plain text while
                              preserving \xa0 (via unescape() on &nbsp;/&#160;).
                            _patch_pygrammalecte(): fixes two pygrammalecte bugs —
                              (1) invalid JSON when paragraphs are empty (orphan commas);
                              (2) spell suggestions disabled (bSpellSugg=False hardcoded) → patched to True.
                              Attaches suggestions to the .suggestions field of GrammalecteSpellingMessage.
export/
  php_export.py             copies static PHP files + generates lib/config.php (.tpl)
                            Passes SITE_TYPE = config.site_type into template variables.
                            Creates empty media/ directory (disk cache for lib/media.php).
                            No image files extracted at export: images are served
                            on demand by lib/media.php from the database.
  yaml_io.py                YamlExport: serialises the entire database to YAML
                              references: name lists (or dicts for techniques/difficulty_levels)
                              recipes: resolved names, media encoded in base64
                              serving field included in each recipe
                            YamlImport: deserialises and merges into the database
                              automatically creates missing reference items
                              upsert of techniques and difficulty_levels; upsert of recipes
                              serving field imported (default "")
                              returns a stats dict (created/updated per type)
resources/
  icons/                    24×24 SVG icons for the toolbar (flat, coloured)
                              db_settings, export_php, export_yaml, import_yaml, consistency
                              recipe_new, recipe_copy, recipe_delete
                              ref_categories, ref_ingredients, ref_units,
                              ref_techniques, ref_sources, ref_difficulty
  php/
    lib/.htaccess             Options -Indexes / Deny from all (protects all of lib/)
    lib/config.php.tpl        template $DB_TYPE/$DB_HOST/…/$STRINGS_PHP/$SITE_TITLE/$SITE_TYPE
    media.php                 serves images from DB (GET ?code=CODE or ?diff=N) — at the root
                              of the export because lib/ is protected by .htaccess
                              Disk cache in media/: writes the file on first access,
                              serves from memory if the directory is not accessible.
                              Handles PostgreSQL BYTEA returned as a stream resource.
    index.php                 GET routing: RECIPE= → card | tech= → technique | else home
                              Integration mode: if ../include/General_recipe.lib.php exists and
                              contains recipe_header(), calls recipe_header/body/footer(SITE_TYPE)
                              around the content instead of the standalone HTML skeleton.
    lib/db.php                PDO (sqlite/mysql/pgsql), lazy static connection
    lib/recipe.php            get_recipe(), get_recipes_by_category(), search_recipes(),
                              get_all_categories/ingredients/techniques/sources()
                              search_recipes(name, category_ids[], ingredient_ids[], difficulty,
                                source_ids[], cat_mode, ing_mode, src_mode) — multi-value filters;
                                mode 'or' → IN(…), mode 'and' → subquery HAVING COUNT(DISTINCT …)=n
    lib/display.php           h(), media_url(code), get_difficulty_levels(), parse_markers(),
                              render_difficulty(), render_duration(), render_recipe(),
                              render_category_listing()
                              Generates indented HTML (2 spaces/level).
                              media_url(code) → 'media.php?code=CODE' (direct DB source)
                              get_difficulty_levels(): reads difficulty_levels from DB, cached
                                per request; returns [level => ['label'=>…, 'icon'=>…]]
                                icon = 'lib/media.php?diff=N' if data non-empty, else ''
                              render_difficulty(level): uses get_difficulty_levels()
                              [IMG:CODE] → media_url(); missing tag: [IMG:CODE]
    lib/technique.php         get_technique(), resolve_techniques() recursive with anti-loop,
                              render_techniques_panel(techniques, label, indent='')
                              indent parameter: indentation prefix for nesting
                              (passed as '    ' from render_recipe).
    lib/search.php            render_search_form(), render_search_results()
                              cat/ing/src: <select multiple> + OR/AND toggle (.search-filter-group)
                              Difficulty: simple select. Technique: simple select + onchange submit.
                              Tom Select placeholders via data-placeholder on each <select>.
    css/base.css              CSS variables (:root), reset, body/links, sticky header layout.
                              General @media print (colours, body, a). Shareable with the host site.
    css/tom-select.min.css    Tom Select (vendored). CSS variables overridden in .search-form
                              to match the graphic theme (--ts-font-size, --ts-border-color…).
    css/recipes.css           Search form, category listing <details>, recipe card,
                              hero image, hover gallery, status messages, @media print recipes.
                              .search-filter-group: flex column wrapper (select + OR/AND toggle).
                              .search-mode-toggle: OR/AND radio below each multi-select.
                              Depends on :root variables defined in base.css.
    js/tom-select.min.js      Tom Select (vendored).
    js/recipe.js              Opens category <details>. Initialises Tom Select on #ts-cat,
                              #ts-ing, #ts-src (remove_button plugin, unlimited maxOptions).
```

## YAML export format

```yaml
categories: [Entrée, Plat principal, Dessert]
units:
  - {name: g, name_plural: g}
  - {name: kg, name_plural: kg}
  - {name: L, name_plural: L}
ingredients:
  - {name: Beurre, name_plural: ""}
  - {name: Farine, name_plural: Farines}
  - {name: Sucre, name_plural: ""}
sources: [Larousse Gastronomique]
techniques:
  - code: BAIN_MA
    title: Bain-marie
    description: "<p>…</p>"
difficulty_levels:
  - level: 0
    label: ""
    mime_type: image/jpeg
    data: ""                 # base64; empty if no icon
  - level: 1
    label: Facile
    mime_type: image/png
    data: "<base64>"
  # … levels 2 and 3 …
recipes:
  - code: GATEAU_CHOC
    name: Gâteau au chocolat
    difficulty: 2
    serving: "6 parts"       # quantity/servings; "" if not set
    prep_time: 30
    wait_time: null
    description: "<p>…</p>"
    comments: ""
    source: Larousse Gastronomique   # null if none
    categories: [Dessert]
    ingredients:
      - position: 0
        prefix: ""
        quantity: "200"
        unit: g
        unit_plural: false
        ingredient: Farine
        ingredient_plural: false
        separator: ""
        suffix: ""
    media:
      - position: 0
        code: GATEAU_CHOC_1
        mime_type: image/jpeg
        data: "<base64>"
```

## PHP export — layout target/
```
target/
  index.php
  media.php      ← serves images from DB; disk cache in media/
                    (must be at root: lib/ is protected by .htaccess)
  lib/
    .htaccess    ← Deny from all (protects all of lib/)
    config.php   ← generated from config.php.tpl (includes SITE_TYPE)
    db.php / recipe.php / display.php / technique.php / search.php
  css/base.css
  css/recipes.css
  css/tom-select.min.css   ← Tom Select (vendored, updated via `make update-vendors`)
  js/tom-select.min.js
  js/recipe.js
  media/         ← disk cache (created empty at export, populated by media.php)
```

## PHP recipe display
1. `<h1>` name + categories right-aligned
2. Card: meta row — quantity/servings (`serving`) + difficulty (bitmap icon + label from `$DIFFICULTY_LEVELS`) + total duration (prep+wait)
3. Ingredient table: prefix | qty unit (plural if `unit_plural` and `name_plural` set) | separator **name** (plural if `ingredient_plural` and `name_plural` set) suffix
4. Description section (parsed HTML)
5. Comments section (parsed HTML) — if not empty
6. Mentioned techniques section (recursive, deduplicated) — if present
7. Additional image gallery — if present
8. Source right-aligned

## PHP home page
- Search form:
  - Free text
  - Category multi-select (Tom Select, `cat[]`) + OR/AND toggle (`cat_mode=or|and`)
  - Ingredient multi-select (Tom Select, `ing[]`) + OR/AND toggle (`ing_mode=or|and`)
  - Difficulty select (single value)
  - Source multi-select (Tom Select, `src[]`) + OR/AND toggle (`src_mode=or|and`)
  - Technique select (single value, triggers immediate submit)
  - AND logic between dimensions, OR or AND within a dimension
  - AND mode on sources: always 0 results if 2+ sources selected (source_id is a direct 1:1 FK)
- Without criteria: `<details open>` listing by category → recipe links
- With criteria: `search_recipes()` results list

## URLs
- Home: `index.php` (no parameter)
- Recipe: `index.php?RECIPE=CODE`
- Standalone technique: `index.php?tech=CODE`
- Search: `index.php?q=…&cat[]=ID&cat[]=ID&cat_mode=or&ing[]=ID&ing_mode=and&diff=N&src[]=ID&src_mode=or`

## Makefile (default target: `help`)
`help venv venv-update install run test test-php coverage lint format hooks dist srcdist update-vendors docs docs-live live-test clean`

## Project files
```
Makefile  environment.yml  pyproject.toml  LICENSE  CLAUDE.md  SPECS.md
src/  tests/
```

## Tests
- `tests/test_config.py`       : defaults, fallback string, roundtrip YAML
- `tests/test_sqlite_db.py`    : CRUD category/recipe/technique, search
- `tests/test_html_editor.py`  : unit tests for _clean_html() and HtmlEditor
- `tests/test_spellcheck.py`   : _html_to_plain (NBSP preservation, HTML stripping) +
                                   _patch_pygrammalecte (JSON robustness, suggestions)
- `tests/test_recipe_filter.py`: _normalize_filter (diacritics, case, real cases)

### Python coverage

`make coverage` runs pytest with `--cov`. Functions that execute the full
Grammalecte engine (`grammalecte_info`, `_run_with_suggestions` in
`spellcheck_dialog.py`) are marked `# pragma: no cover`: coverage instrumentation
traces every internal Grammalecte line, multiplying runtime by ×250 (~35 s instead
of 0.1 s). Tests that build `PreferencesDialog` mock `grammalecte_info` for the
same reason.

### PHP coverage

PHP coverage requires Xdebug or PCOV. The `coverage` target automatically detects
the available driver in the following order:

1. conda PHP (ideal, fully isolated) — unavailable until Xdebug/PCOV support PHP 8.5.
2. System PHP with Xdebug (current fallback — see README § Development).
   System prerequisites: `php-xdebug php-xml php-sqlite3`.
   `XDEBUG_MODE=coverage` is passed explicitly because Xdebug 3 defaults to
   `develop` mode; without it PHPUnit generates an empty report.
   `php-sqlite3` is required because `db.php` calls `die()` if PDO SQLite is
   absent, killing PHPUnit before it writes the report.
3. No driver: PHP tests run without coverage, with a warning.
   CI uses this mode (no native driver installed).

When Xdebug or PCOV support PHP 8.5 (`conda-forge`), remove the `elif`/`else`
branches from the `coverage` target and keep only the conda invocation.
