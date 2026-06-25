PHP Web Export
==============

.. contents::
   :local:
   :depth: 2

Overview
--------

The PHP export produces a self-contained web application that displays the
recipe database in a browser.  The application requires only a PHP 8.0+
server with PDO support and access to the same database used by PBRecipe.
No framework, no build step, no static file generation: everything is
rendered server-side on each request.

**Technology stack**

- PHP 8.0+ with PDO (SQLite, MariaDB/MySQL, PostgreSQL)
- `Tom Select <https://tom-select.js.org/>`_ for multi-select filter dropdowns
- Vanilla CSS + JavaScript (no framework dependency)

**Two deployment modes**

Standalone
    The export ships its own HTML skeleton (``<html>``/``<head>``/``<body>``).
    Suitable for a dedicated subdirectory or subdomain.

Integration
    If ``../include/recipe_integration.lib.php`` is present, the host site's
    ``recipe_header()`` / ``recipe_body()`` / ``recipe_footer()`` functions
    wrap the content instead.  See :ref:`php-integration-mode`.

Triggering the export
---------------------

From the GUI
    **File → Export PHP** opens a directory picker, then generates all files.

From the command line
    .. code-block:: bash

        python -m pbrecipe --export-php /path/to/webroot/recipes

    If the directory is omitted, the path configured in the YAML file is used.

From Python
    .. code-block:: python

        from pbrecipe.export.php_export import PhpExport
        from pbrecipe.config import RecipeConfig
        from pbrecipe.database import Database

        exporter = PhpExport(config, db, target=Path("/var/www/recipes"))
        exporter.export()

Generated file layout
---------------------

.. code-block:: none

    target/
      index.php               ← router and page renderer
      media.php               ← image / icon server
      lib/
        .htaccess             ← deny all direct browser access
        config.php            ← generated: DB credentials and site settings
        db.php                ← PDO singleton factory
        recipe.php            ← recipe data-access layer
        display.php           ← HTML rendering functions
        technique.php         ← technique loading and rendering
        search.php            ← search form rendering
      css/
        base.css              ← layout, variables, print rules
        recipes.css           ← recipe card, search form, gallery
        tom-select.min.css    ← Tom Select (vendored)
      js/
        tom-select.min.js     ← Tom Select (vendored)
        recipe.js             ← Tom Select init, gallery lightbox
      media/                  ← disk cache for media.php (created empty)

Database configuration
----------------------

``lib/config.php`` is generated from ``lib/config.php.tpl`` at export time.
It defines the PHP constants used by ``lib/db.php``:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Constant
     - Type
     - Description
   * - ``DB_TYPE``
     - string
     - ``'sqlite'`` | ``'mysql'`` | ``'pgsql'``
   * - ``DB_HOST``
     - string
     - Hostname (MySQL/PostgreSQL)
   * - ``DB_PORT``
     - int
     - Port (MySQL default 3306, PostgreSQL default 5432)
   * - ``DB_NAME``
     - string
     - Database name (MySQL/PostgreSQL)
   * - ``DB_USER``
     - string
     - Database user
   * - ``DB_PASS``
     - string
     - Database password
   * - ``DB_PATH``
     - string
     - Absolute path to the SQLite file (``~`` expanded at export time)
   * - ``SITE_TYPE``
     - string
     - Passed to integration hooks (see :ref:`php-integration-mode`)
   * - ``SITE_DEBUG``
     - bool
     - ``true`` → display PHP errors (development only)

**Separate PHP credentials**

:class:`~pbrecipe.config.recipe_config.DbConfig` supports optional
``php_host`` / ``php_port`` / ``php_user`` / ``php_password`` fields.
When set, these override the main DB credentials in the generated
``config.php``, so the web application can use a read-only account while
PBRecipe itself uses a write-capable one.

URL routing
-----------

All routes go through ``index.php``:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - URL
     - Content
   * - ``index.php``
     - Home: search form + category listing
   * - ``index.php?RECIPE=CODE``
     - Recipe detail card
   * - ``index.php?tech=CODE``
     - Standalone technique panel
   * - ``index.php?q=TEXT``
     - Text search results (substring match on recipe name)
   * - ``index.php?cat[]=ID&cat_mode=or|and``
     - Category filter (multi-select, OR or AND)
   * - ``index.php?ing[]=ID&ing_mode=or|and``
     - Ingredient filter (multi-select, OR or AND)
   * - ``index.php?src[]=ID&src_mode=or|and``
     - Source filter (multi-select, OR or AND)
   * - ``index.php?diff=N``
     - Difficulty filter (N = 0–3)
   * - ``media.php?recipe=CODE&code=IMG_CODE``
     - Recipe image (served from DB, optionally cached in ``media/``)
   * - ``media.php?diff=N``
     - Difficulty level icon (N = 0–3)

Filters can be combined freely.  Within each multi-select dimension the
``or`` / ``and`` toggle controls whether a recipe must match **at least one**
or **all** selected values.  A source filter in AND mode with two or more
values always returns zero results because ``source_id`` is a 1:1 FK
(a recipe can only belong to one source).

Search and filtering
--------------------

The search form is rendered by ``lib/search.php``.  Multi-select dropdowns
for categories, ingredients and sources use Tom Select (initialised by
``js/recipe.js``).  Each dropdown has an OR/AND toggle rendered as radio
buttons.

Filter logic in ``lib/recipe.php`` (``search_recipes()``):

- **OR mode**: ``recipe_code IN (SELECT recipe_code FROM … WHERE id IN (…))``
- **AND mode**: ``recipe_code IN (SELECT recipe_code FROM … WHERE id IN (…) GROUP BY recipe_code HAVING COUNT(DISTINCT id) = N)``
- **Text**: ``r.name LIKE '%TEXT%'``
- Multiple dimensions are combined with ``AND`` between them.

Marker syntax
-------------

Three special markers can be embedded in recipe description, comments and
technique descriptions.  ``parse_markers()`` in ``lib/display.php`` expands
them at render time.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Marker
     - Rendered output
   * - ``[RECIPE:CODE]``
     - Hyperlink to the recipe page: ``<a href="?RECIPE=CODE">Recipe name</a>``
   * - ``[IMG:RECIPE_CODE:IMAGE_CODE]``
     - Inline thumbnail with hover lightbox preview:
       ``<span class="recipe-img-ref"><img class="recipe-thumb" …><span class="recipe-img-preview"><img …></span></span>``
   * - ``[TECH:CODE]``
     - Link to the technique.  Rendered as an anchor (``#tech-CODE``) when the
       technique is already loaded in the same page, or as a page link
       (``?tech=CODE``) for standalone technique pages.

Techniques also reference each other via ``[TECH:CODE]`` markers in their
descriptions.  ``resolve_techniques()`` in ``lib/technique.php`` expands all
nested references recursively (depth-first, with cycle detection via a
``$seen`` set).

Media server
------------

``media.php`` serves binary blobs from the database.  It supports an
optional disk cache in ``media/`` to avoid repeated database reads:

- Cache TTL: 7 200 seconds (2 hours).
- Cache files are named ``<recipe>_<code>.<ext>`` or ``diff_<N>.<ext>``.
- The ``media/`` directory is created empty at each export run.
- PostgreSQL ``BYTEA`` columns may return a stream resource; ``media.php``
  reads it with ``stream_get_contents()`` before writing the cache file.

.. _php-integration-mode:

Integration mode
----------------

If the file ``../include/recipe_integration.lib.php`` exists relative to
``index.php``, the application runs in *integration mode*: ``index.php``
calls the host site's PHP functions instead of generating its own
``<html>``/``<head>``/``<body>`` skeleton.

The three hook functions must be defined in that file:

.. code-block:: php

    function recipe_header(string $site_type): void
    {
        // Output <!DOCTYPE html>, <html>, <head>, opening <body>
    }

    function recipe_body(string $site_type): void
    {
        // Output site navigation / wrapper opening
    }

    function recipe_footer(string $site_type): void
    {
        // Output wrapper closing, </body>, </html>
    }

``$site_type`` receives the value of the ``SITE_TYPE`` constant from
``config.php`` (set via :attr:`~pbrecipe.config.recipe_config.RecipeConfig.site_type`).

PHP library reference
---------------------

``lib/db.php`` — PDO singleton
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides ``get_db() : PDO``, a lazy singleton that opens the database
connection on first call using the constants defined in ``config.php``.
Error mode is ``PDO::ERRMODE_EXCEPTION``; persistent connections are not
used.

``lib/recipe.php`` — data access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All recipe-related queries.  Key functions:

``get_categories_with_recipes()``
    Returns categories that have at least one recipe, with their recipe
    lists sorted case- and diacritic-insensitively by ``sort_key()``.

``get_recipe(string $code)``
    Loads a single recipe with all its relationships: categories, ingredient
    rows (with unit and ingredient names + plurals), media codes, and source.

``search_recipes(array $filters)``
    Multi-dimensional filter query.  ``$filters`` keys:
    ``q``, ``cat`` + ``cat_mode``, ``ing`` + ``ing_mode``,
    ``src`` + ``src_mode``, ``diff``.

``get_available_ingredients()`` / ``get_available_categories()`` / ``get_available_sources()``
    Return only the reference items that are actually used by at least one
    recipe (used to populate the search form selects).

``get_globals_map()``
    Returns all rows from the ``globals`` table as ``[key => value]``.

``lib/display.php`` — HTML rendering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stateless rendering functions that write directly to output:

``render_recipe(array $recipe)``
    Full recipe card: meta row, ingredients block or section, description,
    comments, techniques, gallery, source.

``render_difficulty(int $level)``
    Difficulty badge (``<span class="difficulty">``) with optional icon
    and label.  Icon data fetched from ``difficulty_levels`` on first call
    and cached in the global ``$DIFFICULTY_LEVELS``.

``format_duration(int $minutes) : string``
    Converts minutes to a human-readable string: ``"1h 30min"``, ``"45min"``,
    ``"2h"``.

``parse_markers(string $html, bool $tech_standalone) : string``
    Expands ``[RECIPE:…]``, ``[IMG:…]`` and ``[TECH:…]`` markers in
    rich-text HTML.  Recipe and technique name caches are populated once per
    request.  Unknown image codes produce a ``<span class="img-missing">``
    placeholder.

``lib/technique.php`` — techniques
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_technique(string $code) : ?array``
    Loads a single technique row.

``resolve_techniques(string $html) : array``
    Scans ``$html`` for ``[TECH:CODE]`` markers and returns all referenced
    techniques (recursively), depth-first, deduplicating with a ``$seen``
    set.  Used to collect and render the full technique panel for a recipe.

``render_techniques(array $techniques)``
    Renders the ``<section class="recipe-techniques">`` panel with one
    ``<div class="technique">`` per entry.

``lib/search.php`` — search form
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``render_search_form(array $available, array $current_filters)``
    Builds the ``<form class="search-form">`` HTML with Tom Select
    multi-selects for categories, ingredients and sources, a text input,
    a difficulty select and a technique select.  Active filter values are
    pre-selected.

Database schema (PHP view)
--------------------------

The tables queried by the PHP application:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Table
     - Key columns
   * - ``recipes``
     - ``code`` (PK), ``name``, ``difficulty``, ``serving``, ``prep_time``,
       ``wait_time``, ``cook_time``, ``description``, ``comments``,
       ``source_id`` (FK)
   * - ``categories``
     - ``id`` (PK), ``name``
   * - ``recipe_categories``
     - ``recipe_code`` (FK), ``category_id`` (FK)
   * - ``recipe_ingredients``
     - ``id``, ``recipe_code`` (FK), ``position``, ``prefix``,
       ``quantity``, ``unit_id`` (FK), ``unit_plural``, ``separator``,
       ``ingredient_id`` (FK), ``ingredient_plural``, ``suffix``
   * - ``ingredients``
     - ``id`` (PK), ``name``, ``name_plural``
   * - ``units``
     - ``id`` (PK), ``name``, ``name_plural``
   * - ``sources``
     - ``id`` (PK), ``name``
   * - ``techniques``
     - ``code`` (PK), ``title``, ``description``
   * - ``recipe_media``
     - ``id``, ``recipe_code`` (FK), ``position``, ``code``,
       ``mime_type``, ``data`` (BLOB)
   * - ``difficulty_levels``
     - ``level`` (0–3), ``label``, ``hide_label``, ``mime_type``,
       ``data`` (BLOB)
   * - ``globals``
     - ``key`` (PK), ``value``

YAML backup and restore
-----------------------

:mod:`pbrecipe.export.yaml_io` provides full database serialisation
independently of the PHP export.

Export (``--export-yaml``)
    Serialises all tables to a single YAML file.  Binary data
    (``recipe_media.data``, ``difficulty_levels.data``) is encoded as
    base64.  A modal progress window is shown for large databases
    (appears after 500 ms).

Import
    Deserialises and *merges* into the target database:

    - Reference items (categories, units, ingredients, sources) are
      auto-created if missing.
    - Techniques and difficulty levels are upserted.
    - Recipes are created or updated.
    - Images exceeding 16 MB raise an explicit error
      (e.g. *"Recette CARBONARA, image PHOTO1 : 18.3 Mo dépasse la
      limite de 16 Mo"*) instead of a raw database exception.

CSS reference
-------------

``css/base.css`` defines CSS custom properties and the page skeleton
(sticky header, ``main.site-main``, ``footer.site-footer``).
``css/recipes.css`` defines all recipe-specific classes:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Class
     - Element
   * - ``.search-form``
     - Search ``<form>``
   * - ``.search-filter-group``
     - Wrapper for one multi-select + its OR/AND toggle
   * - ``.search-mode-toggle``
     - OR/AND radio button pair
   * - ``.category-listing``
     - Wrapper for the category accordion
   * - ``.category-block``
     - ``<details>`` element for one category
   * - ``.category-name``
     - ``<summary>`` heading of a category block
   * - ``.recipe-links``
     - ``<ul>`` of recipe links (listing or search results)
   * - ``.search-results``
     - Additional class on ``.recipe-links`` in search mode
   * - ``.no-results``
     - Paragraph shown when a search returns zero results
   * - ``.recipe``
     - ``<article>`` wrapping a full recipe card
   * - ``.recipe-card``
     - Inner ``<div>`` containing all recipe sections
   * - ``.recipe-meta``
     - Row with serving, duration and difficulty badge
   * - ``.serving`` / ``.duration``
     - Individual meta spans
   * - ``.difficulty``
     - Difficulty badge ``<span>`` (tooltip = label)
   * - ``.diff-icon`` / ``.diff-icon-img``
     - Icon wrapper and ``<img>`` inside the badge
   * - ``.diff-label``
     - Text label inside the badge
   * - ``.recipe-ingredients-block``
     - Ingredients + hero image side-by-side layout
   * - ``.hero-item`` / ``.recipe-hero-img``
     - Hero image ``<figure>`` and ``<img>``
   * - ``.hero-preview``
     - Hover lightbox for the hero image
   * - ``.recipe-ingredients``
     - ``<section>`` for the ingredients list
   * - ``.ingredients-table``
     - ``<table>`` of ingredient rows
   * - ``.ing-prefix`` / ``.ing-qty`` / ``.ing-rest``
     - Table cells: optional prefix, quantity + unit, name + suffix
   * - ``.recipe-description`` / ``.recipe-comments``
     - Rich-text sections
   * - ``.recipe-body``
     - ``<div>`` holding the parsed HTML content
   * - ``.recipe-techniques``
     - Techniques ``<section>``
   * - ``.technique``
     - One technique ``<div>``
   * - ``.technique-body``
     - Technique description ``<div>``
   * - ``.recipe-gallery``
     - Additional images grid (``no-print``)
   * - ``.gallery-item`` / ``.gallery-thumb``
     - Gallery ``<figure>`` and thumbnail ``<img>``
   * - ``.gallery-preview``
     - Hover lightbox for gallery images
   * - ``.recipe-source``
     - Source ``<p>``
   * - ``.recipe-img-ref``
     - Inline image from a ``[IMG:…]`` marker
   * - ``.recipe-thumb``
     - Thumbnail ``<img>`` inside ``.recipe-img-ref``
   * - ``.recipe-img-preview``
     - Lightbox preview inside ``.recipe-img-ref``
   * - ``.tech-link``
     - ``<a>`` generated by a ``[TECH:…]`` marker
   * - ``.img-missing``
     - Placeholder when an ``[IMG:…]`` image is not found
   * - ``.no-print``
     - Applied to the gallery; hidden in print media query
   * - ``.error``
     - Error message paragraph
   * - ``.site-presentation-block`` / ``.site-presentation``
     - Optional site description block on the home page
