# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au versionnement **AAAA.x** (année civile + séquence).

## [2026.2] — 2026-05-07

### Added

- Forme plurielle pour les unités (`Unit.name_plural`) et les ingrédients (`Ingredient.name_plural`) :
  champ saisi dans les dialogues d'édition, stocké en base, propagé dans l'export/import YAML et
  affiché côté PHP si la case « Pl. » est cochée sur la ligne d'ingrédient.
- Cases à cocher « Pl. » dans `IngredientListEditor` (après l'unité et après l'ingrédient) pour
  activer la forme plurielle ligne par ligne (`unit_plural`, `ingredient_plural`).
- Raccourci clavier **Ctrl+S** pour enregistrer la recette en cours ; action également ajoutée dans
  le menu **Recette**.
- Poignée de glisser-déposer (⠿) dans la liste d'ingrédients pour réordonner les lignes ;
  remplace les boutons ↑↓.
- Focus automatique sur le champ Préfixe lors de l'ajout d'une nouvelle ligne d'ingrédient.
- Tooltips explicites sur les boutons de la liste d'ingrédients et de la barre d'outils `HtmlEditor`.
- Documentation du DOM PHP : `MAIN_DOM.md` (page principale) et `RECIPE_DOM.md` (fiche recette),
  avec diagrammes Mermaid.
- Tests unitaires étendus pour `HtmlEditor._clean_html()` (`tests/test_html_editor.py`).

### Changed

- Boutons **+** et **−** de la liste d'ingrédients déplacés après le champ Suffixe (extrémité droite
  de la ligne).
- Schéma DB : nouvelles colonnes `units.name_plural`, `ingredients.name_plural`,
  `recipe_ingredients.unit_plural`, `recipe_ingredients.ingredient_plural` ; migration automatique (v3).
- Export/import YAML : unités et ingrédients exportés en dicts `{name, name_plural}` au lieu de
  simples chaînes ; rétrocompatibilité assurée à l'import.
- PHP `recipe.php` : requête `recipe_ingredients` étendue avec `u.name_plural` et `i.name_plural`.
- PHP `display.php` : rendu conditionnel — utilise la forme plurielle si le flag est actif et la
  forme plurielle renseignée.
- CI : artefacts de release nommés avec l'OS et l'architecture
  (`pbrecipe-<os>-<arch>[.ext]`, ex. `pbrecipe-linux-x86_64`).
- Tests PHP : la base SQLite de test est désormais créée par `tests/test_php_fixtures.py`
  via `Database.create_schema()`, éliminant la duplication du schéma avec `bootstrap.php` ;
  `make test-php` pilote la séquence via `PBRECIPE_TEST_DB`.

## [2026.1] — 2026-05-04

### Added

- Interface graphique PySide6 : liste des recettes, éditeur, barre d'outils avec icônes SVG.
- Gestion des référentiels : catégories, difficultés, ingrédients, sources, techniques, unités.
- Multi-moteur de base de données via SQLAlchemy : SQLite, MariaDB/MySQL, PostgreSQL.
- Configuration par fichier YAML (`app.yaml`, `dialog_dirs.yaml`, `recipe_config.yaml`) stockée dans `$XDG_CONFIG_HOME/pbrecipe/`.
- Export PHP : génération d'un site PHP complet (PDO) à partir de la base de recettes.
- Import/export YAML des recettes.
- Exécutable monofichier multiplateforme via PyInstaller (`make dist`, `pbrecipe.spec`).
- Suite de tests Python (pytest + pytest-qt + pytest-cov) et PHP (PHPUnit).
- Chaîne de qualité : ruff (lint + format), pre-commit.
- Makefile avec cibles `venv`, `install`, `run`, `test`, `test-php`, `coverage`, `lint`, `format`, `dist`, `clean`, `icons`.
- Icônes natives par plateforme : `pbrecipe.ico` (Windows) et `pbrecipe.icns` (macOS) générées depuis le PNG source via `tools/make_icons.py` (Pillow).

[2026.2]: https://github.com/ppoilbarbe/PBRecipe/releases/tag/2026.2
[2026.1]: https://github.com/ppoilbarbe/PBRecipe/releases/tag/2026.1
