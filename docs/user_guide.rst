User Guide
==========

.. contents::
   :local:
   :depth: 2

Overview
--------

PBRecipe lets you manage culinary and cocktail recipes in a structured
database.  Each recipe is composed of:

- a title, category, difficulty, source and optional notes
- a list of ingredients with quantities and units
- preparation steps written in a rich-text HTML editor
- optional media (photos)

From the database, PBRecipe can generate a set of PHP files that constitute a
complete, autonomous web application ready to be deployed on any PHP-capable
server.

Installation
------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.12 or later
- A conda environment (recommended) — see ``environment.yml``
- One of the supported database backends:

  - **SQLite** — no server required; suitable for single-user use
  - **MariaDB / MySQL** — recommended for shared or networked use
  - **PostgreSQL** — alternative relational backend

Create and activate the conda environment::

    conda env create -f environment.yml
    conda activate pbrecipe

Install the package in editable mode::

    make install

Launching the application
--------------------------

::

    make run

or directly::

    python -m pbrecipe [FICHIER] [options]

Command-line options
~~~~~~~~~~~~~~~~~~~~

``FICHIER``
    Path to the YAML configuration file to open on start-up.  If omitted,
    PBRecipe opens the last used configuration or shows an empty state.

``--config-dir DIRECTORY``
    Redirect all configuration files (``app.yaml``, ``dialog_dirs.yaml``) to
    *DIRECTORY* instead of the platform default
    (``~/.config/pbrecipe`` on Linux, ``~/Library/Preferences/pbrecipe`` on
    macOS, ``%APPDATA%\pbrecipe`` on Windows).  Useful during development to
    avoid overwriting the real configuration.

``--export-php [DIRECTORY]``
    Generate the PHP export without opening the GUI.  If *DIRECTORY* is
    omitted, the directory configured in the YAML file is used.

``--export-yaml [FILE]``
    Export all recipes to a YAML file without opening the GUI.  If *FILE* is
    omitted, the path configured in the YAML file is used.

Database configuration
-----------------------

On first launch, PBRecipe displays the database configuration dialog.  Fill in:

- **Engine** — ``sqlite``, ``mysql`` or ``postgresql``
- **Host / Port** — for MySQL/PostgreSQL (ignored for SQLite)
- **Database name** — for SQLite, the path to the ``.db`` file
- **User / Password** — for MySQL/PostgreSQL

The configuration is saved in the YAML file (``app.yaml``).  PBRecipe creates
the schema automatically on first connection.

Managing reference data
-----------------------

Before adding recipes, populate the reference tables via the **Edit** menu:

Categories
~~~~~~~~~~

Each recipe belongs to one category (e.g. *Entrées*, *Cocktails*).  The
category list dialog lets you add, rename and delete categories, and control
whether the category label is shown in the web export.

Difficulties
~~~~~~~~~~~~

A difficulty level (e.g. *Easy*, *Medium*, *Expert*) is optional for each
recipe.

Units
~~~~~

Units are used for ingredient quantities (e.g. *g*, *cl*, *tbsp*).  A unit can
have a singular and plural form for display purposes.

Ingredients
~~~~~~~~~~~

Ingredients are shared across recipes.  Each ingredient belongs to a category
and can have a plural form.

Techniques
~~~~~~~~~~

Techniques are short preparation methods referenced from recipe steps (e.g.
*brunoise*, *bain-marie*).

Sources
~~~~~~~

A source (book, website, person) can be attached to a recipe to track its
origin.

Recipes
-------

Creating a recipe
~~~~~~~~~~~~~~~~~

Click **New recipe** or press :kbd:`Ctrl+N`.  Fill in:

- **Title** — required
- **Category**, **Difficulty**, **Source** — selected from drop-down lists
- **Portions** — number of servings
- **Preparation / Cooking / Rest time** — in minutes
- **Notes** — free-text field

Adding ingredients
~~~~~~~~~~~~~~~~~~

The ingredient list editor allows you to add rows with:

- ingredient name (auto-completed from the database)
- quantity (numeric)
- unit (selected from the unit list)
- optional note (e.g. *finely chopped*)

Ingredients can be reordered by dragging rows.

Writing preparation steps
~~~~~~~~~~~~~~~~~~~~~~~~~

Steps are written in the embedded **HTML editor**, which provides:

- bold, italic, underline formatting
- paragraph / heading styles (Normal, H1–H3)
- hyperlinks
- undo / redo

Spell checking
~~~~~~~~~~~~~~

Open the spell-check panel from **Tools → Spell check**.  PBRecipe supports
two backends (installed separately):

- `LanguageTool <https://languagetool.org/>`_ (``pip install language-tool-python``)
- `Grammalecte <https://grammalecte.net/>`_ (``pip install pygrammalecte``)

The spell-check window is non-modal and updates live as you edit.

Media
~~~~~

The **Media** tab displays photos attached to the recipe.  Photos are stored
in the database as binary blobs.

Saving and discarding
~~~~~~~~~~~~~~~~~~~~~

- :kbd:`Ctrl+S` — save the current recipe
- :kbd:`Escape` or clicking another recipe — prompts to save, discard or cancel

Consistency check
-----------------

**Tools → Check consistency** scans the database for common issues:

- recipes with no ingredients
- ingredients referenced in recipes but missing from the ingredient table
- orphan reference rows

Globals
-------

**Edit → Global settings** manages application-wide strings used in the web
export (site title, footer text, etc.).

PHP web export
--------------

**File → Export PHP** (or ``--export-php``) generates a set of PHP files in
the configured output directory.  The export includes:

- ``index.php`` — entry point with search and listing
- ``recipe.php`` — recipe detail page
- ``display.php`` — shared rendering helpers
- ``db.php`` — database access layer
- ``search.php`` — search logic
- ``config.php`` — generated configuration (strings, DB credentials)
- Vendored JS/CSS assets (Tom Select for search)

The generated site requires only PHP 7.4+ and a database accessible from the
web server; no framework is needed.

YAML import / export
--------------------

**File → Export YAML** (or ``--export-yaml``) serialises all recipes to a
single YAML file.  The same file can be used to seed a fresh database or
transfer data between instances.

Makefile targets
----------------

.. code-block:: none

    make help          Show all available targets
    make run           Launch PBRecipe
    make test          Run Python test suite
    make test-php      Run PHP test suite
    make coverage      Run tests and open HTML coverage report
    make lint          Check code style (ruff)
    make format        Auto-format source code
    make docs          Build HTML documentation
    make docs-live     Build docs with live reload
    make dist          Build a standalone executable (PyInstaller)
    make srcdist       Build a source distribution
    make bump-release  Bump the release counter (2026.5 → 2026.6)
    make bump-year     Start a new year (2026.x → 2027.1)
