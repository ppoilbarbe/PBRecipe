# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to **YYYY.x** versioning (calendar year + sequence).

## [2026.7] — 2026-06-25

### Fixed

- Linux bundle: Ubuntu is now explicitly set as the application font after
  registering bundled fonts. The bundled `libfontconfig.so` has its default
  config path hardcoded to the build machine's conda prefix, which does not
  exist on target machines; fontconfig therefore fails silently and Qt falls
  back to an unpredictable font. Forcing Ubuntu bypasses fontconfig for font
  selection; rendering settings (anti-aliasing, hinting) are still inherited
  from `/etc/fonts/fonts.conf` via the runtime hook's generated `fonts.conf`.

### Added

- **LanguageTool remote server**: new option in Preferences to use LanguageTool
  without Java or a local download. Supports the public API (`api.languagetool.org`,
  default when the URL field is empty) and any self-hosted server (e.g. Docker).
  The URL field is disabled when the checkbox is unchecked; an HTML tooltip describes
  the public API rate limits and the Docker self-hosting alternative. When neither
  Grammalecte nor LanguageTool is enabled, clicking "Vérifier…" shows an informational
  dialog inviting the user to enable a checker in Preferences.
- **LanguageTool — connection error**: when the server is unreachable or the URL is
  wrong, the spell-check window displays a clear error message (yellow banner) with
  a contextual hint (network issue for the public API; start command for a local
  server). No traceback is shown to the user.
- **Spell check — line numbers**: each reported error now shows the line number in
  the source text (both Grammalecte and LanguageTool).
- **Tools menu**: "Paramètres de la base…", "Présentation et libellés…" and
  "Préférences du programme…" moved from the File menu to a new "&Outils" menu,
  between "Référentiels" and "Aide".
- **Sphinx documentation** (`docs/`): user guide, Python API reference (autodoc),
  and PHP web export documentation (overview, routing, marker syntax, CSS reference,
  library reference, YAML backup, DOM structure pages with 11 Mermaid diagrams);
  RST files for changelog and DOM pages are regenerated from their Markdown sources
  at build time by `docs/conf.py`.
- **Mermaid diagrams** in DOM pages: rendered via `sphinxcontrib-mermaid`; node
  labels with line breaks use `<br/>` (was `\n`, rendered literally); click-to-zoom
  lightbox with zoom-in / zoom-out / reset buttons and keyboard shortcuts.
- **ReadTheDocs** (`.readthedocs.yaml`): configuration for automated hosted builds.
- **CI — `docs` job**: builds HTML documentation and uploads it as a workflow
  artifact; runs after the `test` job.
- **`make docs`** / **`make docs-live`**: build documentation locally, with optional
  live-reload via `sphinx-autobuild`.

### Changed

- Documentation translated to English: README, CHANGELOG, SPECS, CLAUDE.md.
- README: database schema diagram replaced with `classDiagram` (Mermaid) and updated
  to include all missing columns (`name_plural`, `hide_label`, `unit_plural`,
  `ingredient_plural`) and the `globals` table.
- **Preferences — Grammalecte**: checkbox label changed from "Utiliser Grammalecte
  en priorité" to "Utiliser Grammalecte"; tooltip updated to mention that Grammalecte
  handles French text only; "Installer / Mettre à jour" button is disabled when the
  checkbox is unchecked.
- **Preferences — LanguageTool**: status label added showing whether the
  `language-tool-python` module is installed and which version, consistent with the
  Grammalecte section.
- `language-tool-python>=3.0` added to dev dependencies (`pyproject.toml`) and to
  PyInstaller hidden imports (`pbrecipe.spec`); minimum version set to 3.0 (API
  change: `errorLength` → `error_length`).

## [2026.6] — 2026-06-23

### Added

- **`--config-dir DIRECTORY` option**: redirects all configuration
  (`app.yaml`, `dialog_dirs.yaml`) to an alternative directory. Intended for
  development to avoid overwriting the real configuration.
- **Makefile targets `bump-release` / `bump-year` / `bump-set VERSION=YYYY.x`**:
  increment the version in `src/pbrecipe/__init__.py` and `pyproject.toml`
  via `tools/bump_version.py`.
- **Cross-platform configuration directory** (`config/_config_root.py`):
  Linux (`$XDG_CONFIG_HOME/pbrecipe` or `~/.config/pbrecipe`),
  macOS (`~/Library/Preferences/pbrecipe`),
  Windows (`%APPDATA%\pbrecipe`).

### Changed

- **Spell check — internal references**: `[RECIPE:CODE]` and `[TECH:CODE]` markers
  are replaced by the recipe or technique title before being sent to the checker,
  instead of being simply removed (which caused truncated sentences and false positives).
- **Spell check window — persistent geometry**: position and size stored in the YAML
  configuration file (integers), restored on next open.
- **Spell check window — focus**: opening and updating content no longer steals focus
  from the main window.
- **Spell check window — close**: automatically closes when the main window closes.
- **Standalone `GeometryMixin`**: no longer requires an `app_config` parameter; the
  mixin reloads the configuration itself as needed.
- **Recipe list position**: scroll position is preserved when saving a recipe (no more
  unwanted scroll-to-top).
- **Save / Cancel / Discard dialogue**: fixed three anomalies when clicking a recipe
  while another has unsaved changes — selection, highlight and display are now
  consistent for all three buttons.
- **HTML editors**: visual spacing between paragraphs doubled (CSS `margin: 0.5em 0`)
  to improve readability; stored content is unchanged.
- **Direct HTML editing**: non-breaking spaces (`&nbsp;`) are no longer converted to
  regular spaces when validating the HTML source dialogue (Qt serialised non-breaking
  spaces as `\xa0` which `QPlainTextEdit` lost; the fix normalises to `&nbsp;` before
  display).
- **"À propos" dialogue**: version is read from `pbrecipe.__version__`
  (declared in `__init__.py`) instead of `importlib.metadata`, consistent with
  version management in PBRenamer.
- **Version**: `pyproject.toml` and `__init__.py` aligned to `2026.6` (were at `0.1.0`).

### Fixed

- Linux bundle: identical fonts between the local build and the CI build. The
  `fonts.conf` embedded by PyInstaller contained absolute paths to the conda
  environment of the build machine; on another machine, those paths are not found
  and Qt fell back to system fonts only.
  Fix: conda fonts (`fonts-conda-ecosystem`: Ubuntu, DejaVu, Inconsolata,
  SourceCodePro) are now included in the bundle via `pbrecipe.spec`, and a runtime
  hook (`hooks/pyi_rth_fonts.py`) generates a portable `fonts.conf` pointing to
  `_MEIPASS/fonts/` at frozen binary startup.

## [2026.5] — 2026-06-23

### Added

- **Recipe list filter**: text field below the list, case- and diacritics-insensitive
  (e.g. "gateau" finds "Gâteau au chocolat"). The filter persists across refreshes
  without hiding the recipe selected by code.
- **F7 shortcut** on the "Vérifier…" button in the recipe editor and in the technique
  edit dialogue (standard word-processor shortcut: LibreOffice, Word…).
- **Difficulty levels — "Masquer le libellé" checkbox** in `DifficultyDialog`: displays
  the icon alone; label visible only in the tooltip on hover.
- PHP: Tom Select vendored (`css/tom-select.min.css` + `js/tom-select.min.js`);
  updated via `make update-vendors`.
- PHP: search form — category, ingredient and source passed as `<select multiple>`
  with Tom Select; each filter offers an OR/AND radio (`.search-mode-toggle`).
  AND logic between dimensions; source multi-selects in AND mode always return 0 results
  (source_id is a direct 1:1 FK on recipes).
- `make run ARGS="…"`: pass CLI arguments to the program (e.g. `ARGS="--debug"`).
- `Makefile`: `update-vendors` target — downloads the latest Tom Select version
  from jsDelivr.
- Regression tests:
  - `tests/test_spellcheck.py` (37 tests) — `_html_to_plain` and `_patch_pygrammalecte`
    (JSON fix, NBSP, spell suggestions)
  - `tests/test_recipe_filter.py` (14 tests) — `MainWindow._normalize_filter`
  - 17 new Python test files (321 tests total); coverage 20% → 91%.
- **PHP coverage**: `make coverage` generates an HTML report for PHP code
  (`htmlcov/php/index.html`) via Xdebug (`XDEBUG_MODE=coverage`); coverage limited to
  `lib/` modules. Automatically detects the available driver: conda PHP (ideal), system
  PHP with Xdebug (fallback), or graceful skip with warning if no driver is present (CI).
- `argparse_qt.py`: parsing of Qt options (`--style`, `--platform`, `--display`, etc.)
  from the command line, imported from PBRenamer.
- **PyInstaller bundle**: `pygrammalecte` and `grammalecte` (modules + dictionaries
  `graphspell/_dictionaries/`) included in the executable.
- `README.md`: **Development** section documenting system prerequisites for PHP coverage
  (`php-xdebug`, `php-xml`, `php-sqlite3`) and the future migration to conda.

### Changed

- Spell check: **non-modal window** — remains open while editing text; a second click
  on "Vérifier…" updates the content without opening a new window.
- Spell check (Grammalecte): **spell suggestions enabled** (`bSpellSugg=True`) — e.g.
  "cannelle" suggested for "canelle".
- Spell check: switched from `get_plain_text()` to `get_html()` + `_html_to_plain()`
  to preserve non-breaking spaces (`\xa0`) when sending to the checker.
- PHP: `media.php` moved from `lib/` to the export root (`.htaccess` protects all of
  `lib/`; `media.php` must be directly accessible by the browser).
- `Makefile`: `designer` target removed (unused).
- Tests: `grammalecte_info()` and `_run_with_suggestions()` marked `# pragma: no cover` —
  running the full Grammalecte engine under coverage multiplies runtime by ×250; tests
  that build `PreferencesDialog` now mock `grammalecte_info`.
  Gain: Python suite 61 s → 26 s.

### Fixed

- Grammalecte: `JSONDecodeError` when checking texts with empty paragraphs
  (pygrammalecte produced an invalid JSON array with orphan commas).
- Grammalecte: non-breaking space incorrectly flagged as missing — `QTextEdit.toPlainText()`
  converts `\xa0` to a regular space; fixed by using the raw HTML as source.
- PHP `render_difficulty()`: `hide_label` respected — icon displayed alone when the
  option is checked.
- CI: `pygrammalecte` added to `[dev]` extras in `pyproject.toml` — `test_spellcheck.py`
  module tests were failing (`ModuleNotFoundError`) on GitHub Actions runners.
- Bundle: `_patch_pygrammalecte` was looking for `grammalecte-cli.py` via
  `get_paths()["scripts"]`, an invalid path inside a PyInstaller executable — replaced
  by direct module import.
- `make coverage`: PHP coverage now working (PHPUnit 11 no longer supports `phpdbg`;
  `XDEBUG_MODE=coverage` required for Xdebug 3; `php-sqlite3` required to avoid a fatal
  `die()` in `db.php` before the report is written).

## [2026.4] — 2026-06-03

### Added

- PHP: source filter in the search form (`search.php`).
- Preferences: **PHP DEBUG mode** option (`SITE_DEBUG` in `config.php`).
- `AppConfig`: geometry persistence (position + size) for each dialogue via
  `GeometryMixin`; all reference dialogues benefit from it.
- Database: automatic `BLOB → MEDIUMBLOB` migration on MariaDB; column declared
  `LargeBinary(16_777_215)`.
- `Makefile`: `dist` and `srcdist` targets with git versioning via `tools/git_version.sh`.
- YAML export and import: modal progress window showing recipe-by-recipe progress
  ("Recette N/M: CODE"); only appears after 500 ms to avoid disrupting fast operations.
- Spell and grammar checking in the recipe editor (Réalisation + Commentaires) and in
  the technique edit dialogue (Titre + Description), via the **Vérifier…** button.
- Two checkers supported as optional dependencies:
  - **Grammalecte** (`pip install pygrammalecte`) — used in priority if enabled; the
    displayed version is that of the embedded engine (e.g. 2.1.1), not the wrapper.
  - **LanguageTool** (`pip install language-tool-python`, requires Java) — used as fallback.
- **Preferences**: new "Vérification grammaticale" section to enable/disable Grammalecte,
  view its status (installed/not installed + version), and install or update Grammalecte
  directly from the dialogue (via `pip`, without blocking the interface).
- YAML import: explicit error message if an image exceeds 16 MB
  (e.g. "Recette CARBONARA, image PHOTO1: 18.3 Mo dépasse la limite de 16 Mo par image")
  instead of the raw MariaDB message.
- `MAX_MEDIA_BYTES = 16_777_215` constant in `constants.py`; `schema.py` now uses it
  instead of the literal value.

### Changed

- PHP: `strings` and `presentation` moved to `index.php` (loaded from DB);
  `config.php.tpl` simplified accordingly.
- `IngredientListEditor`: column widths proportional to `MAX_*` constants instead of
  fixed pixels.
- YAML export: unlimited line width to avoid breaks in long strings.
- pre-commit: updated `pre-commit-hooks` → v6.0.0, `ruff` → v0.15.13.

### Fixed

- `SearchTest`: fixed calls to `render_search_form` after the `$sources` parameter was
  added in version 2026.3; `$current` was passed in 5th position instead of 6th.

## [2026.3] — 2026-05-08

### Added

- **Présentation et libellés dialogue** (`GlobalsDialog`): editing of the site HTML
  presentation and application labels, saved to the database in the `globals` table;
  accessible from the Fichier menu and the toolbar.
- `DbConfig`: `php_host`, `php_port`, `php_user`, `php_password` fields for PHP export
  access credentials separate from the program credentials (fallback to program values if
  empty); dedicated "Accès export PHP" panel in the settings dialogue.
- CLI argument `--check-connect`: diagnoses the database connection in 6 steps (read
  config, parameters, URL construction, connection, schema verification) without opening
  the graphical interface.
- Dual image format `[IMG:RECIPE_CODE:IMAGE_CODE]` in the HTML editor: avoids code
  collisions between recipes; the image picker offers a "current recipe only" filter.
- `pbrecipe/constants.py` module: all SQL column lengths and business rules centralised
  as constants; `schema.py` and UI widgets (`setMaxLength`, `setRange`) import them directly.
- `Database.get_globals()` / `set_globals()`: CRUD for the `globals` table.
- `Database.list_all_media()`: lists all media across all recipes.
- YAML export/import: the `globals` table is included in the exported document (`globals`
  key) and reloaded on import.
- `SITE_PRESENTATION` in `config.php.tpl` / `index.php`: the presentation text entered in
  the dialogue is displayed at the top of the PHP search page.
- CSS `.site-presentation` in `recipes.css` for the presentation block.
- Toolbar state persistence (`AppConfig.toolbar_state`).
- Consistency check extended to the global presentation (broken links in
  `globals.presentation`).

### Changed

- Application labels (`strings`) are no longer stored in the YAML configuration file;
  they are managed exclusively in the database via the Présentation et libellés dialogue.
  `RecipeConfig`: `strings` field and `string()` method removed.
- `save_recipe()` accepts an `original_code` parameter to handle recipe renaming:
  sub-tables (categories, ingredients, media) are migrated to the new code.
- PHP `media.php`: parameters `?recipe=RECIPE_CODE&code=IMAGE_CODE` (instead of
  `?code=CODE`); composite cache key to avoid collisions.
- PHP `display.php`: `parse_markers()` uses dynamic calls to `media.php` for images;
  `$tech_standalone` parameter replaces the old `$url_map`.
- Toolbars reorganised into 5 named groups (Base de données, Export PHP, YAML, Recettes,
  Référentiels); the consistency check action moved to Référentiels.
- Consistency check automatically proposed before a PHP export if problems are detected.
- `_ensure_all_varchar_sizes()`: iterates over SQLAlchemy metadata to automatically adjust
  all `VARCHAR` columns to their declared length (MariaDB, PostgreSQL); SQLite ignored.
- `clear_all_data()` now also clears the `globals` table.
- `_migrate()`: migration history (v2, v3) removed; all databases are up to date.

## [2026.2] — 2026-05-07

### Added

- Plural form for units (`Unit.name_plural`) and ingredients (`Ingredient.name_plural`):
  field entered in the edit dialogues, stored in the database, propagated in YAML
  export/import and displayed on the PHP side when the "Pl." checkbox is checked on an
  ingredient row.
- "Pl." checkboxes in `IngredientListEditor` (after the unit and after the ingredient)
  to enable the plural form row by row (`unit_plural`, `ingredient_plural`).
- **Ctrl+S** keyboard shortcut to save the current recipe; action also added to the
  **Recette** menu.
- Drag handle (⠿) in the ingredient list to reorder rows; replaces the ↑↓ buttons.
- Automatic focus on the Préfixe field when adding a new ingredient row.
- Explicit tooltips on the ingredient list buttons and the `HtmlEditor` toolbar.
- PHP DOM documentation: main page (`index.php`) and recipe card (`?RECIPE=CODE`),
  with Mermaid diagrams (now part of the Sphinx documentation).
- Extended unit tests for `HtmlEditor._clean_html()` (`tests/test_html_editor.py`).

### Changed

- **+** and **−** buttons in the ingredient list moved after the Suffixe field (right
  end of the row).
- DB schema: new columns `units.name_plural`, `ingredients.name_plural`,
  `recipe_ingredients.unit_plural`, `recipe_ingredients.ingredient_plural`; automatic
  migration (v3).
- YAML export/import: units and ingredients exported as dicts `{name, name_plural}`
  instead of plain strings; backward compatibility ensured on import.
- PHP `recipe.php`: `recipe_ingredients` query extended with `u.name_plural` and
  `i.name_plural`.
- PHP `display.php`: conditional rendering — uses the plural form if the flag is active
  and the plural form is set.
- CI: release artefacts named with OS and architecture
  (`pbrecipe-<os>-<arch>[.ext]`, e.g. `pbrecipe-linux-x86_64`).
- PHP tests: the SQLite test database is now created by `tests/test_php_fixtures.py`
  via `Database.create_schema()`, eliminating schema duplication with `bootstrap.php`;
  `make test-php` drives the sequence via `PBRECIPE_TEST_DB`.

## [2026.1] — 2026-05-04

### Added

- PySide6 graphical interface: recipe list, editor, toolbar with SVG icons.
- Reference management: categories, difficulties, ingredients, sources, techniques, units.
- Multi-database engine via SQLAlchemy: SQLite, MariaDB/MySQL, PostgreSQL.
- YAML file configuration (`app.yaml`, `dialog_dirs.yaml`, `recipe_config.yaml`) stored in `$XDG_CONFIG_HOME/pbrecipe/`.
- PHP export: generation of a complete PHP website (PDO) from the recipe database.
- YAML import/export of recipes.
- Single-file cross-platform executable via PyInstaller (`make dist`, `pbrecipe.spec`).
- Python test suite (pytest + pytest-qt + pytest-cov) and PHP (PHPUnit).
- Quality chain: ruff (lint + format), pre-commit.
- Makefile with targets `venv`, `install`, `run`, `test`, `test-php`, `coverage`, `lint`, `format`, `dist`, `clean`, `icons`.
- Native icons per platform: `pbrecipe.ico` (Windows) and `pbrecipe.icns` (macOS) generated from the source PNG via `tools/make_icons.py` (Pillow).

[2026.2]: https://github.com/ppoilbarbe/PBRecipe/releases/tag/2026.2
[2026.1]: https://github.com/ppoilbarbe/PBRecipe/releases/tag/2026.1
