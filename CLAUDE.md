# Mode

`mixed-en` — Identifiers & inline comments in English, docs & prose in English, user-facing strings in French except debug messages.

# CHANGELOG language

CHANGELOG entries must be written in **English** (consistent with the `mixed-en` mode and the existing entries).

# PHP consistency

Any change to the database schema (`schema.py`) or configuration parameters
(`recipe_config.py` — `_DEFAULT_STRINGS`, `DbConfig`, `RecipeConfig`) must be reflected in
the static PHP files (`resources/php/`) and in the export generator (`php_export.py`):
- New table or column → check `db.php`, `recipe.php`, `display.php`, `search.php`
- New generated file → add it in `_write_*` and load it in `index.php`
- Removed or renamed string key → check all `$strings[…]` in PHP files
