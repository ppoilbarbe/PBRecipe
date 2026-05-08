# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au versionnement **AAAA.x** (année civile + séquence).

## [2026.3] — 2026-05-08

### Added

- Dialogue **Présentation et libellés** (`GlobalsDialog`) : édition de la présentation HTML du
  site et des libellés de l'application, sauvegardés en base dans la table `globals` ;
  accessible depuis le menu Fichier et la barre d'outils.
- `DbConfig` : champs `php_host`, `php_port`, `php_user`, `php_password` pour des identifiants
  d'accès export PHP distincts des identifiants programme (fallback sur valeurs programme si vides) ;
  panneau dédié « Accès export PHP » dans le dialogue de paramètres.
- Argument CLI `--check-connect` : diagnostique la connexion à la base de données en 6 étapes
  (lecture config, paramètres, construction URL, connexion, vérification schéma) sans ouvrir
  l'interface graphique.
- Format d'image dual `[IMG:CODE_RECETTE:CODE_IMAGE]` dans l'éditeur HTML : évite les collisions
  de codes entre recettes ; le sélecteur d'images propose un filtre « recette courante seulement ».
- Module `pbrecipe/constants.py` : toutes les longueurs de colonnes SQL et les règles métier
  centralisées en constantes ; `schema.py` et les widgets UI (`setMaxLength`, `setRange`) les
  importent directement.
- `Database.get_globals()` / `set_globals()` : CRUD pour la table `globals`.
- `Database.list_all_media()` : liste tous les médias toutes recettes confondues.
- Export/import YAML : la table `globals` est incluse dans le document exporté (clé `globals`)
  et rechargée à l'import.
- `SITE_PRESENTATION` dans `config.php.tpl` / `index.php` : le texte de présentation saisi dans
  le dialogue est affiché en haut de la page de recherche PHP.
- CSS `.site-presentation` dans `recipes.css` pour le bloc de présentation.
- Persistance de l'état des barres d'outils (`AppConfig.toolbar_state`).
- Vérification de cohérence étendue à la présentation globale (liens cassés dans `globals.presentation`).

### Changed

- Les libellés de l'application (`strings`) ne sont plus stockés dans le fichier YAML de
  configuration ; ils sont exclusivement gérés en base via le dialogue Présentation et libellés.
  `RecipeConfig` : champ `strings` et méthode `string()` supprimés.
- `save_recipe()` accepte un paramètre `original_code` pour gérer le renommage de recette :
  les sous-tables (catégories, ingrédients, médias) sont migrées vers le nouveau code.
- PHP `media.php` : paramètres `?recipe=CODE_RECETTE&code=CODE_IMAGE` (au lieu de `?code=CODE`) ;
  clé de cache composite pour éviter les collisions.
- PHP `display.php` : `parse_markers()` utilise des appels dynamiques à `media.php` pour les
  images ; paramètre `$tech_standalone` remplace l'ancien `$url_map`.
- Barres d'outils réorganisées en 5 groupes nommés (Base de données, Export PHP, YAML, Recettes,
  Référentiels) ; l'action « Vérifier la cohérence » déplacée dans Référentiels.
- Vérification de cohérence proposée automatiquement avant un export PHP si des problèmes sont
  détectés.
- `_ensure_all_varchar_sizes()` : parcourt le metadata SQLAlchemy pour ajuster automatiquement
  toutes les colonnes `VARCHAR` à leur longueur déclarée (MariaDB, PostgreSQL) ; SQLite ignoré.
- `clear_all_data()` vide désormais aussi la table `globals`.
- `_migrate()` : historique de migration (v2, v3) retiré, toutes les bases étant à jour.

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
