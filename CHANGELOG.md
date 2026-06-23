# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au versionnement **AAAA.x** (année civile + séquence).

## [2026.6] — 2026-06-23

### Added

- **Option `--config-dir RÉPERTOIRE`** : redirige toute la configuration
  (`app.yaml`, `dialog_dirs.yaml`) vers un répertoire alternatif. Destinée au
  développement pour éviter d'écraser la configuration réelle.
- **Cibles Makefile `bump-release` / `bump-year` / `bump-set VERSION=AAAA.x`** :
  incrémentent la version dans `src/pbrecipe/__init__.py` et `pyproject.toml`
  via `tools/bump_version.py`.
- **Répertoire de configuration multi-plateforme** (`config/_config_root.py`) :
  Linux (`$XDG_CONFIG_HOME/pbrecipe` ou `~/.config/pbrecipe`),
  macOS (`~/Library/Preferences/pbrecipe`),
  Windows (`%APPDATA%\pbrecipe`).

### Changed

- **Vérification orthographique — références internes** : les marqueurs
  `[RECIPE:CODE]` et `[TECH:CODE]` sont remplacés par le titre de la recette ou
  de la technique avant envoi au correcteur, au lieu d'être simplement supprimés
  (évitait des phrases tronquées et des faux positifs).
- **Fenêtre de vérification orthographique — géométrie persistante** : position
  et taille mémorisées dans le fichier YAML de configuration (entiers), restaurées
  à la prochaine ouverture.
- **Fenêtre de vérification orthographique — focus** : l'ouverture et la mise à
  jour du contenu ne volent plus le focus à la fenêtre principale.
- **Fenêtre de vérification orthographique — fermeture** : se ferme
  automatiquement à la fermeture de la fenêtre principale.
- **`GeometryMixin` autonome** : plus aucun paramètre `app_config` requis ; le
  mixin recharge lui-même la configuration au besoin.
- **Position de la liste des recettes** : la position de défilement est préservée
  lors de la sauvegarde d'une recette (plus de remontée intempestive en haut).
- **Dialogue Save / Cancel / Discard** : correction de trois anomalies lors du
  clic sur une recette alors qu'une autre a des modifications non sauvegardées —
  sélection, surbrillance et affichage sont maintenant cohérents pour les trois
  boutons.
- **Éditeurs HTML** : espacement visuel entre paragraphes doublé (CSS
  `margin: 0.5em 0`) pour améliorer la lisibilité ; le contenu stocké est
  inchangé.
- **Édition HTML directe** : les espaces insécables (`&nbsp;`) ne sont plus
  convertis en espaces ordinaires lors de la validation du dialogue source HTML
  (Qt sérialisait les espaces insécables en `\xa0` que `QPlainTextEdit` perdait ;
  la correction normalise en `&nbsp;` avant affichage).
- **Dialogue « À propos »** : la version est lue depuis `pbrecipe.__version__`
  (déclaré dans `__init__.py`) au lieu d'`importlib.metadata`, cohérent avec la
  gestion de la version dans PBRenamer.
- **Version** : `pyproject.toml` et `__init__.py` alignés sur `2026.6` (étaient
  à `0.1.0`).

### Fixed

- Bundle Linux : polices identiques entre le build local et le build CI. Le
  `fonts.conf` embarqué par PyInstaller contenait des chemins absolus vers
  l'environnement conda de la machine de build ; sur une autre machine, ces
  chemins sont introuvables et Qt se rabattait sur les seules polices système.
  Fix : les polices conda (`fonts-conda-ecosystem` : Ubuntu, DejaVu, Inconsolata,
  SourceCodePro) sont désormais incluses dans le bundle via `pbrecipe.spec`, et
  un runtime hook (`hooks/pyi_rth_fonts.py`) génère un `fonts.conf` portable
  pointant vers `_MEIPASS/fonts/` au démarrage du binaire frozen.

## [2026.5] — 2026-06-23

### Added

- **Filtre de la liste des recettes** : zone de saisie sous la liste, insensible à la casse et aux
  diacritiques (ex. « gateau » trouve « Gâteau au chocolat »). Le filtre persiste lors des
  rafraîchissements sans masquer la recette sélectionnée par code.
- **Raccourci F7** sur le bouton « Vérifier… » dans l'éditeur de recette et dans le dialogue
  d'édition de technique (standard traitement de texte : LibreOffice, Word…).
- **Niveaux de difficulté — case « Masquer le libellé »** dans `DifficultyDialog` : affiche
  l'icône seule, libellé visible uniquement dans l'infobulle au survol.
- PHP : Tom Select vendorisé (`css/tom-select.min.css` + `js/tom-select.min.js`) ;
  mis à jour via `make update-vendors`.
- PHP : formulaire de recherche — catégorie, ingrédient et source passés en `<select multiple>`
  avec Tom Select ; chaque filtre propose un radio OU/ET (`.search-mode-toggle`).
  Logique ET entre dimensions ; les multi-select sources en mode ET renvoient toujours 0 résultat
  (source_id est une FK directe 1:1 sur les recettes).
- `make run ARGS="…"` : passage d'arguments CLI au programme (ex. `ARGS="--debug"`).
- `Makefile` : cible `update-vendors` — télécharge la dernière version de Tom Select
  depuis jsDelivr.
- Tests de non-régression :
  - `tests/test_spellcheck.py` (37 tests) — `_html_to_plain` et `_patch_pygrammalecte`
    (correction JSON, NBSP, suggestions orthographiques)
  - `tests/test_recipe_filter.py` (14 tests) — `MainWindow._normalize_filter`
  - 17 nouveaux fichiers de test Python (321 tests au total) ; couverture 20 % → 91 %.
- **Coverage PHP** : `make coverage` génère un rapport HTML pour le code PHP
  (`htmlcov/php/index.html`) via Xdebug (`XDEBUG_MODE=coverage`) ; couverture limitée aux
  modules `lib/`. Détecte automatiquement le driver disponible : PHP conda (idéal), PHP système
  avec Xdebug (fallback), ou skip gracieux avec avertissement si aucun driver n'est présent (CI).
- `argparse_qt.py` : parsing des options Qt (`--style`, `--platform`, `--display`, etc.)
  en ligne de commande, importé de PBRenamer.
- **Bundle PyInstaller** : `pygrammalecte` et `grammalecte` (modules + dictionnaires
  `graphspell/_dictionaries/`) inclus dans l'exécutable.
- `README.md` : section **Développement** documentant les prérequis système pour la couverture
  PHP (`php-xdebug`, `php-xml`, `php-sqlite3`) et la migration future vers conda.

### Changed

- Vérification orthographique : **fenêtre non modale** — reste ouverte pendant l'édition du texte ;
  un deuxième clic sur « Vérifier… » met à jour le contenu sans ouvrir une nouvelle fenêtre.
- Vérification orthographique (Grammalecte) : **suggestions pour les fautes d'orthographe**
  activées (`bSpellSugg=True`) — ex. « cannelle » proposé pour « canelle ».
- Vérification orthographique : passage de `get_plain_text()` à `get_html()` + `_html_to_plain()`
  pour préserver les espaces insécables (`\xa0`) lors de la transmission au correcteur.
- PHP : `media.php` déplacé de `lib/` vers la racine de l'export (`.htaccess` protège `lib/`
  entier, `media.php` doit être accessible directement par le navigateur).
- `Makefile` : cible `designer` supprimée (non utilisée).
- Tests : `grammalecte_info()` et `_run_with_suggestions()` marqués `# pragma: no cover` —
  exécuter le moteur Grammalecte complet sous `coverage` multiplie la durée par ×250 ;
  les tests qui construisent `PreferencesDialog` mockent désormais `grammalecte_info`.
  Gain : suite Python 61 s → 26 s.

### Fixed

- Grammalecte : `JSONDecodeError` lors de la vérification de textes avec des paragraphes vides
  (pygrammalecte produisait un tableau JSON invalide avec des virgules orphelines).
- Grammalecte : espace insécable signalé à tort comme manquant — `QTextEdit.toPlainText()`
  convertit `\xa0` en espace ordinaire ; corrigé en utilisant le HTML brut comme source.
- PHP `render_difficulty()` : `hide_label` respecté — l'icône s'affiche seule quand l'option
  est cochée.
- CI : `pygrammalecte` ajouté aux extras `[dev]` dans `pyproject.toml` — les tests du module
  `test_spellcheck.py` échouaient (`ModuleNotFoundError`) sur les runners GitHub Actions.
- Bundle : `_patch_pygrammalecte` cherchait `grammalecte-cli.py` via `get_paths()["scripts"]`,
  chemin invalide dans un exécutable PyInstaller — remplacé par l'import direct du module.
- `make coverage` : couverture PHP désormais fonctionnelle (PHPUnit 11 ne supporte plus `phpdbg` ;
  `XDEBUG_MODE=coverage` requis pour Xdebug 3 ; `php-sqlite3` requis pour éviter un `die()`
  fatal dans `db.php` avant l'écriture du rapport).

## [2026.4] — 2026-06-03

### Added

- PHP : filtre par source dans le formulaire de recherche (`search.php`).
- Préférences : option **mode DEBUG PHP** (`SITE_DEBUG` dans `config.php`).
- `AppConfig` : persistance de la géométrie (position + taille) de chaque dialogue via
  `GeometryMixin` ; tous les dialogues de référentiels en bénéficient.
- Base de données : migration automatique `BLOB → MEDIUMBLOB` sur MariaDB ;
  colonne déclarée `LargeBinary(16_777_215)`.
- `Makefile` : cibles `dist` et `srcdist` avec versionnage git via `tools/git_version.sh`.
- Export et import YAML : fenêtre de progression modale affichant l'avancement recette par recette
  (« Recette N/M : CODE ») ; n'apparaît qu'au-delà de 500 ms pour ne pas gêner les opérations
  rapides.
- Vérification orthographique et grammaticale dans l'éditeur de recette (Réalisation +
  Commentaires) et dans le dialogue d'édition de technique (Titre + Description), via le bouton
  **Vérifier…**.
- Deux correcteurs pris en charge comme dépendances facultatives :
  - **Grammalecte** (`pip install pygrammalecte`) — utilisé en priorité si activé ; la version
    affichée est celle du moteur embarqué (ex. 2.1.1), pas celle du wrapper.
  - **LanguageTool** (`pip install language-tool-python`, requiert Java) — utilisé en fallback.
- **Préférences** : nouvelle section « Vérification grammaticale » permettant d'activer/désactiver
  Grammalecte, de voir son statut (installé/non installé + version), et d'installer ou mettre à
  jour Grammalecte directement depuis le dialogue (via `pip`, sans bloquer l'interface).
- Import YAML : message d'erreur explicite si une image dépasse 16 Mo
  (ex. « Recette CARBONARA, image PHOTO1 : 18.3 Mo dépasse la limite de 16 Mo par image »)
  au lieu du message brut de MariaDB.
- Constante `MAX_MEDIA_BYTES = 16_777_215` dans `constants.py` ; `schema.py` l'utilise désormais
  au lieu de la valeur littérale.

### Changed

- PHP : `strings` et `presentation` déplacés dans `index.php` (chargés depuis la BDD) ;
  `config.php.tpl` allégé en conséquence.
- `IngredientListEditor` : largeurs de colonnes proportionnelles aux constantes `MAX_*` au lieu
  de pixels fixes.
- Export YAML : largeur de ligne illimitée pour éviter les coupures dans les chaînes longues.
- pre-commit : mise à jour `pre-commit-hooks` → v6.0.0, `ruff` → v0.15.13.

### Fixed

- `SearchTest` : correction des appels à `render_search_form` après l'ajout du paramètre
  `$sources` en version 2026.3 ; `$current` était passé en 5ème position au lieu de la 6ème.

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
