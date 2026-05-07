# PBRecipe — Specifications

## Stack
- Python 3.12, PySide6, ruamel.yaml (YAML 1.2), SQLAlchemy ≥ 2.0, PyMySQL, psycopg2
- DB: SQLite | MariaDB | PostgreSQL (au choix par config)
- Web: PHP + PDO (MySQL/PgSQL/SQLite)
- Build: conda (`pbrecipe`), hatchling, `make`

## Fichiers de configuration du programme

Stockés dans `$XDG_CONFIG_HOME/pbrecipe/` (défaut : `~/.config/pbrecipe/`).

### `app.yaml` — préférences programme

```yaml
recent_files:
  - /chemin/vers/recettes.yaml
log_level: INFO          # DEBUG | INFO | WARNING
window_geometry:         # position/taille de la fenêtre principale ; restauré au démarrage
  x: 100
  y: 50
  width: 1200
  height: 800
splitter_sizes:          # largeurs des panneaux liste recettes / éditeur
  - 220
  - 640
```

Chargé au démarrage par `AppConfig.load()`. Modifiable via le dialogue **Préférences**.
`window_geometry` et `splitter_sizes` sont écrits dans `closeEvent` et restaurés dans `_setup_ui`.

### `dialog_dirs.yaml` — derniers répertoires des dialogues fichier

```yaml
new_config: /home/…
open_config: /home/…
export_php: /home/…
php_export_dir: /home/…
export_yaml: /home/…
import_yaml: /home/…
```

Mis à jour automatiquement après chaque validation d'un dialogue fichier/répertoire.
Chaque dialogue s'ouvre dans le dernier répertoire utilisé pour cette clé.

## Config YAML de la base de recettes

Fichier YAML 1.2 ouvert au démarrage ou créé via dialogue.

```yaml
name: "Mes Recettes"
site_type: recettes      # transmis à SITE_TYPE dans config.php (intégration site hôte)
php_export_dir: /chemin/export   # optionnel ; absent si non défini
db:
  type: sqlite          # sqlite | mariadb | postgresql
  path: ~/recipes.db    # SQLite uniquement
  host: localhost        # MariaDB / PostgreSQL
  port: 3306
  database: recipes
  user: ""
  password: ""
strings:                 # textes spécifiques au type de recette
  window_title: ...
  recipe_singular: ...
  serving_label: Quantité   # label du champ portions/quantité
  # + ~15 autres clés (labels UI et site web)
  # Les libellés et icônes de difficulté sont désormais stockés en base (table difficulty_levels)
```

## Schéma DB

```
categories(id PK, name ≤20 NN)
units(id PK, name ≤15, name_plural ≤15 DEF'')  # name peut être vide ; name_plural : forme plurielle
ingredients(id PK, name ≤50 NN,
            name_plural ≤50 DEF'')              # name_plural : forme plurielle optionnelle
sources(id PK, name TEXT NN)                   # TEXT (pas de limite), peut contenir du HTML
techniques(code ≤10 PK, title ≤40 NN, description TEXT)
difficulty_levels(level 0-3 PK, label ≤50 DEF'',
                  mime_type ≤50 DEF'image/jpeg',
                  data BLOB?)                  # icône bitmap ; NULL si non définie
recipes(code ≤50 PK, name ≤200 NN, difficulty 0-3 DEF 0,
        serving ≤30 DEF'',
        prep_time INT?, wait_time INT?,
        description TEXT, comments TEXT, source_id→sources)
recipe_categories(recipe_code→recipes, category_id→categories, PK composée)
recipe_ingredients(id PK, recipe_code→recipes, position,
                   prefix ≤10 DEF'', quantity ≤10 DEF'1',
                   unit_id→units?, unit_plural BOOL DEF False,
                   separator ≤20 DEF'',
                   ingredient_id→ingredients?, ingredient_plural BOOL DEF False,
                   suffix ≤20 DEF'')
recipe_media(id PK, recipe_code→recipes, position,
             code ≤20 NN,        # référence dans [IMG:CODE]
             mime_type ≤50 NN DEF'image/jpeg',
             data BLOB NN)       # données binaires de l'image
```

Toutes FK : ON DELETE CASCADE (enfants) ou SET NULL (refs optionnelles).
SQLAlchemy `LargeBinary` → BLOB (SQLite) / LONGBLOB (MariaDB) / BYTEA (PostgreSQL).

Migration : à la création du schéma :
- Si `difficulty_levels` est vide → insertion des 4 niveaux par défaut (0 vide, 1 Facile, 2 Moyen, 3 Difficile).
- Si la colonne `recipe_media.filename` existe → suppression (colonne obsolète).
- Si la colonne `recipes.serving` est absente → `ALTER TABLE recipes ADD COLUMN serving VARCHAR(30) NOT NULL DEFAULT ''`.
- v3 : si `units.name_plural`, `ingredients.name_plural`, `recipe_ingredients.unit_plural` ou
  `recipe_ingredients.ingredient_plural` sont absentes → `ALTER TABLE … ADD COLUMN …`.

Tri de toutes les listes : effectué côté Python via `_sort_key()` (insensible à la casse et aux
diacritiques : `unicodedata.normalize("NFD").casefold().encode("ascii","ignore")`). Les requêtes SQL
ne contiennent pas d'`ORDER BY`.

## Marqueurs spéciaux (HTML description/commentaires/techniques)
| Marqueur | Insertion | Rendu PHP |
|---|---|---|
| `[RECIPE:CODE]` | picker liste CODE — nom | lien `?RECIPE=CODE` |
| `[IMG:CODE]` | picker liste + prévisualisation 240 px | `<img>` résolu via `$MEDIA_INDEX[CODE]` (manifeste généré à l'export) |
| `[TECH:CODE]` | picker liste CODE — titre | ancre vers panneau technique |
| `<a href="URL">` | dialogue URL + texte affiché | lien HTML direct |

`[IMG]` absent dans l'éditeur de techniques (images liées aux recettes, pas aux techniques).
Techniques : résolution récursive avec garde anti-boucle (`resolve_techniques(html, seen[])`).

## HTML stocké en base — format propre

`get_html()` applique `_clean_html()` sur le HTML verbeux produit par `QTextEdit.toHtml()`
avant tout stockage (DB ou export). Règles de nettoyage dans l'ordre :

1. **Extraction du corps** : seul le contenu entre `<body>` et `</body>` est conservé
   (supprime DOCTYPE, `<head>`, `<style>`, attributs du `<body>`).
2. **Suppression des espaces inter-blocs** : `_INTER_BLOCK_WS_RE` retire les espaces/sauts de
   ligne entre balises de bloc (`<p>`, `<h1>`–`<h6>`, `<ul>`, `<ol>`, `<li>`, `<div>`,
   `<blockquote>`) pour éviter que Qt ne génère des paragraphes vides au rechargement.
3. **Conversion des `<span>` stylisés** (passes itératives de l'intérieur vers l'extérieur) :
   - `font-weight: 500–900` ou `bold` → `<b>`
   - `font-style: italic` → `<i>`
   - `text-decoration: … underline …` → `<u>`
   - Combinaisons dans un même span → balises imbriquées `<b><i>…</i></b>` etc.
   - `<span>` sans `style=` ou dont le style ne contient aucune des propriétés ci-dessus
     → contenu extrait (span supprimé).
4. **Suppression de tous les `style="…"`** résiduels sur tout élément
   (marges Qt, `-qt-block-indent`, tailles de police, couleurs, etc.).
5. **`<b>` redondant dans les titres** : `<h1><b>…</b></h1>` → `<h1>…</h1>`
   (le gras est déjà implicite dans les balises `<h1>`–`<h4>`).
6. **Contenu vide** : `get_html()` retourne `""` si le HTML nettoyé ne contient pas de texte visible
   (ex. simple `<p></p>` résidu d'un éditeur vide).

`set_html()` applique aussi `_INTER_BLOCK_WS_RE` à l'entrée et remplace `<p><br /></p>` par
`<p style="-qt-paragraph-type:empty;"><br /></p>` pour éviter le double saut de ligne Qt.

Balises préservées intactes : `<p>`, `<ul>`, `<ol>`, `<li>`, `<br>`, `<h1>`–`<h4>`,
`<a href="…">`, `<b>`, `<i>`, `<u>`, et les marqueurs `[RECIPE:…]` `[IMG:…]` `[TECH:…]`.

Le PHP (`display.php`) insère ce HTML directement dans `<div class="recipe-body">` et
le stylise exclusivement via des classes CSS — aucun style inline côté PHP.

## Ligne de commande

```
python -m pbrecipe [FICHIER] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `FICHIER` | Fichier de configuration YAML à ouvrir au démarrage |
| `--export-php [RÉPERTOIRE]` | Export PHP sans interface graphique. Si RÉPERTOIRE est omis, utilise `php_export_dir` depuis la configuration ; erreur si non défini. |
| `--debug` | Niveau de log DEBUG (messages détaillés) |
| `--verbose` | Niveau de log INFO (défaut) |
| `--quiet` | Niveau de log WARNING (avertissements et erreurs uniquement) |

Les options `--debug`/`--verbose`/`--quiet` surchargent le niveau par défaut pour la session courante sans modifier `app.yaml`.

## Logging

- Niveau par défaut : `INFO`, lu depuis `app.yaml` au démarrage.
- Format DEBUG : `%(asctime)s %(levelname)-8s %(name)s: %(message)s`
- Format INFO/WARNING : `%(levelname)s: %(message)s`
- Reconfigurable en direct via le dialogue **Préférences** (sans redémarrage).
- `apply_log_level(level)` met à jour le logger racine et tous ses handlers immédiatement.

## Architecture Python (`src/pbrecipe/`)

```
__init__.py / __main__.py
app.py                      main(), apply_log_level(), _headless_export()
                            argparse : FICHIER, --export-php, --debug/--verbose/--quiet
config/
  __init__.py
  app_config.py             AppConfig — recent_files, log_level, dialog_dirs,
                                        window_geometry (dict), splitter_sizes (list[int])
                            load/save → ~/.config/pbrecipe/app.yaml
                            window_geometry et splitter_sizes sauvegardés dans closeEvent,
                            restaurés dans _setup_ui au démarrage.
  dialog_dirs.py            DialogDirs — mémorise le dernier répertoire par clé de dialogue
                            get(key)/record(key, chosen, is_dir=False) — sauvegarde immédiate
                            load/save → ~/.config/pbrecipe/dialog_dirs.yaml
  recipe_config.py          RecipeConfig, DbConfig — load/save YAML
                            champs : name, db, strings, php_export_dir, site_type
                            site_type : chaîne libre transmise à SITE_TYPE dans config.php
                            serving_label ajouté aux _DEFAULT_STRINGS
database/
  schema.py                 MetaData + Tables SQLAlchemy (dialecte-agnostique)
                            LargeBinary pour recipe_media.data
                            sources.name : Text (pas de longueur fixe)
                            recipes : colonne serving VARCHAR(30) NOT NULL DEFAULT ''
  database.py               Database — classe unique, SQLAlchemy Core, engine.begin()
                            SQLite: event "connect" → PRAGMA foreign_keys=ON
                            _safe_url() masque le mot de passe dans les logs
                            _sort_key(s) : tri insensible casse+diacritiques (Python-side)
                            Toutes les list_*() trient par _sort_key (pas d'ORDER BY SQL)
                            sources : tri sur le nom sans balises HTML
                            list/get/save_difficulty_level() ; seed auto dans _migrate()
                            Migration _migrate() : colonne serving si absente
  factory.py                create_database(config) → Database(url)
                            urls: sqlite:///path | mysql+pymysql://… | postgresql+psycopg2://…
models/
  recipe.py                 Recipe, RecipeIngredient, RecipeMedia (dataclasses)
                            Recipe : champ serving: str = "" (quantité/portions, max 30 chars)
                            RecipeMedia: code, mime_type, data:bytes
  difficulty.py             DifficultyLevel (level, label, mime_type, data:bytes|None)
  category/ingredient/unit/source/technique.py
ui/
  main_window.py            QMainWindow : liste recettes (gauche) + éditeur (droite)
                            Splitter mémorisé dans self._splitter ; tailles restaurées depuis app.yaml.
                            Position/taille fenêtre restaurées depuis app.yaml (window_geometry).
                            Chargement automatique du dernier fichier au démarrage.
                            Confirmation avant abandon des modifications non enregistrées
                            (navigation, fermeture).
                            Menus :
                              Fichier   → Nouvelle base… | Ouvrir… | Fichiers récents
                                          Paramètres de la base… | Préférences du programme…
                                          ── Export PHP…
                                          ── Exporter YAML… | Importer YAML…
                                          ── Quitter
                              Recette   → Nouvelle recette (Ctrl+R)
                                          Copier la recette… (Ctrl+Shift+R)
                                          Supprimer la recette
                              Référentiels → Catégories… | Ingrédients… | Unités…
                                             Techniques… | Sources…
                                             Niveaux de difficulté…
                              Aide      → À propos…
                            Barre d'outils (icônes SVG colorées) :
                              [db_settings] [export_php] | [export_yaml] [import_yaml]
                              | [consistency] | [recipe_new] [recipe_copy] [recipe_delete]
                              | [ref_categories] [ref_ingredients] [ref_units]
                                [ref_techniques] [ref_sources] [ref_difficulty]
  recipe_editor.py          QTabWidget : Informations | Ingrédients | Réalisation | Commentaires | Médias
                            Onglet Informations : champ Quantité (QLineEdit ≤30 chars, serving)
                              avant Difficulté dans le formulaire méta.
                            _slugify(name) → CODE (ASCII upper, espaces→_)
                            Bouton Enregistrer : désactivé tant qu'aucune modification.
                            Action « Enregistrer la recette » (QAction) avec raccourci Ctrl+S,
                              partagée entre le menu Recette et le bouton Enregistrer.
                            Validation à l'enregistrement : au moins une catégorie requise
                            (message d'erreur + annulation si aucune sélectionnée).
                            Combo sources : affichage sans balises HTML (re.sub r"<[^>]+>").
                            reload_references() : méthode publique ; recharge categories, sources,
                              ingredient_editor et html_editor references sans recharger la recette ;
                              appelée depuis main_window après édition d'un référentiel.
                            _reload_editor_references(recipe, db) : appelé à chaque load() ;
                              alimente desc_editor et comment_editor via set_references() :
                              recipes=db.list_recipes(), images=[(m.code, m.data) for m in
                              recipe.media], techniques=db.list_techniques().
  ingredient_list_editor.py Lignes scrollables : ↑ ↓ + − | prefix/qty/unit/[Pl.]/sep/ingredient/[Pl.]/suffix
                            Boutons par ligne (à gauche) : ↑ déplacer vers le haut (désactivé en 1re pos),
                              ↓ vers le bas (désactivé en dernière pos), + insérer après, − supprimer.
                            Bouton + seul affiché quand la liste est vide (_empty_btn).
                            Ancienne barre "Ajouter/Supprimer dernier" supprimée.
                            Cases à cocher « Pl. » : activent unit_plural / ingredient_plural par ligne
                              (utilise name_plural si coché et la forme plurielle est renseignée).
                            reload(db) : recharge les listes unit/ingredient de chaque ligne
                              sans perdre les valeurs saisies (utilisé par reload_references()).
  html_editor.py            QTextEdit WYSIWYG.
                            Toolbar : G | I | U | H1 | H2 | H3 | H4 | • Liste | 1. Liste |
                                      [LIEN] | [RECETTE] | [IMG] | [TECH]
                            ([IMG] masqué si show_img=False)
                            Titres H1–H4 : setHeadingLevel() + QTextCharFormat (taille+gras)
                              explicite car Qt ne met pas à jour le rendu visuel seul.
                              _HEADING_SIZES = {1:20, 2:16, 3:14, 4:12} pt.
                              Clic répété sur le même niveau → retour paragraphe normal.
                              _EDITOR_CSS : "p { margin: 0; } h1 { … } h2 { … } …"
                              appliqué via document().setDefaultStyleSheet().
                            [LIEN] : _LinkDialog (URL + texte affiché, texte pré-rempli
                              depuis la sélection) ; insertHtml('<a href="...">...</a>').
                              URL et texte échappés avec html.escape().
                            Pickers de référence (se substituent aux QInputDialog) :
                              _RefPickerDialog(title, [(code,label)]) — liste filtrée,
                                double-clic ou OK ; recettes et techniques.
                              _ImgPickerDialog([(code,bytes)]) — liste filtrée + panneau
                                de prévisualisation QLabel 240×240 px mis à jour à la
                                sélection via QPixmap.loadFromData().
                            set_references(recipes, images, techniques) : alimenté à
                              chaque chargement de recette depuis la DB.
                              images = [(code, data:bytes)] des médias de la recette.
                              Absent dans TechniqueEditDialog (images=[] + show_img=False).
                            get_html() appelle _clean_html(toHtml()) avant retour.
                              Retourne "" si le résultat ne contient pas de texte visible.
                            set_html(html) : applique _INTER_BLOCK_WS_RE + patch Qt empty-p
                              avant setHtml() pour éviter les paragraphes vides parasites.
  media_tab.py              _MediaFileDialog : QFileDialog (DontUseNativeDialog) avec panneau
                              de prévisualisation 240 px greffé sur la grille du dialogue ;
                              mise à jour via signal currentChanged(path)
                            MediaTab : QSplitter liste (miniatures 80×80) + aperçu pleine taille ;
                              après sélection fichier → QInputDialog pour le code (pré-rempli
                              depuis le nom de fichier) ; boutons Ajouter… Supprimer Exporter… ↑ ↓
                            Exporter… : écrit media.data dans un fichier choisi via QFileDialog ;
                              extension déduite du mime_type et ajoutée automatiquement si absente.
                            Formats acceptés : JPEG, PNG, GIF, WebP, BMP (images uniquement).
                            Vidéos non supportées : le backend multimédia Qt6 (GStreamer/FFmpeg)
                              est requis pour générer des vignettes mais est absent/non fonctionnel.
  about_dialog.py           AboutDialog : icône 64×64 + titre + version + description
                              auteur et version lus depuis importlib.metadata("pbrecipe")
                              affiche Python X.Y.Z · PySide6 X.Y.Z
  config_dialog.py          Paramètres de la base : nom, répertoire d'export PHP (avec bouton
                            Parcourir…), type DB (SQLite path | host/port/db/user/pass),
                            tous les strings (les clés difficulty_* ne font plus partie des strings)
  preferences_dialog.py     Préférences du programme : niveau de log par défaut (liste déroulante
                            DEBUG/INFO/WARNING) — appliqué immédiatement via apply_log_level()
  dialogs/
    _base_list_dialog.py    générique liste+ajout+modif+suppression (QInputDialog)
                              double-clic sur un élément → édition directe
    category/source_dialog.py  (5 lignes chacun)
    ingredient_dialog.py    dialogue dédié : champs Nom + Nom pluriel (QLineEdit ≤50 chars)
    unit_dialog.py          dialogue dédié : champs Nom + Nom pluriel (QLineEdit ≤15 chars)
    technique_dialog.py     TechniqueDialog : liste des techniques + TechniqueEditDialog
                              double-clic sur un élément → édition directe
                            TechniqueEditDialog (code+titre+HtmlEditor(show_img=False))
                              reçoit db → set_references(recipes, [], techniques)
                              [IMG] absent : les images appartiennent aux recettes
    difficulty_dialog.py    DifficultyDialog : panneau scindé — liste fixe 4 niveaux (gauche)
                              + éditeur (droite) : libellé + aperçu icône bitmap + Charger/Supprimer
                              sauvegarde immédiate en DB à chaque modification
export/
  php_export.py             copie fichiers PHP statiques + génère lib/config.php (.tpl)
                            Passe SITE_TYPE = config.site_type dans les variables du template.
                            Crée media/ vide (cache disque pour lib/media.php).
                            Aucun fichier image extrait à l'export : les images sont servies
                            à la demande par lib/media.php depuis la base de données.
  yaml_io.py                YamlExport : sérialise toute la base en YAML
                              référentiels : listes de noms (ou dicts pour techniques/difficulty_levels)
                              recettes : noms résolus, médias encodés en base64
                              champ serving inclus dans chaque recette
                            YamlImport : désérialise et fusionne dans la base
                              crée automatiquement les éléments du référentiel absents
                              upsert des techniques et difficulty_levels ; upsert des recettes
                              champ serving importé (défaut "")
                              retourne un dict de statistiques (créés/mis à jour par type)
resources/
  icons/                    Icônes SVG 24×24 pour la barre d'outils (flat, colorées)
                              db_settings, export_php, export_yaml, import_yaml, consistency
                              recipe_new, recipe_copy, recipe_delete
                              ref_categories, ref_ingredients, ref_units,
                              ref_techniques, ref_sources, ref_difficulty
  php/
    lib/.htaccess             Options -Indexes / Deny from all
    lib/config.php.tpl        template $DB_TYPE/$DB_HOST/…/$STRINGS_PHP/$SITE_TITLE/$SITE_TYPE
    lib/media.php             sert images depuis la DB (GET ?code=CODE ou ?diff=N)
                              Cache disque dans media/ : écrit le fichier au premier accès,
                              sert depuis la mémoire si le répertoire n'est pas accessible.
                              Gère PostgreSQL BYTEA retourné comme ressource de flux.
    index.php                 routage GET: RECIPE= → fiche | tech= → technique | sinon accueil
                              Mode intégration : si ../include/General_recipe.lib.php existe et
                              contient recipe_header(), appelle recipe_header/body/footer(SITE_TYPE)
                              autour du contenu au lieu du squelette HTML autonome.
    lib/db.php                PDO (sqlite/mysql/pgsql), connexion lazy statique
    lib/recipe.php            get_recipe(), get_recipes_by_category(), search_recipes(),
                              get_all_categories/ingredients/techniques()
    lib/display.php           h(), media_url(code), get_difficulty_levels(), parse_markers(),
                              render_difficulty(), render_duration(), render_recipe(),
                              render_category_listing()
                              Génère du HTML indenté (2 espaces/niveau).
                              media_url(code) → 'lib/media.php?code=CODE' (source DB directe)
                              get_difficulty_levels() : lit difficulty_levels en DB, mis en cache
                                par requête ; retourne [level => ['label'=>…, 'icon'=>…]]
                                icon = 'lib/media.php?diff=N' si data non vide, sinon ''
                              render_difficulty(level) : utilise get_difficulty_levels()
                              [IMG:CODE] → media_url() ; balise manquante : [IMG:CODE]
    lib/technique.php         get_technique(), resolve_techniques() récursif anti-boucle,
                              render_techniques_panel(techniques, label, indent='')
                              Paramètre indent : préfixe d'indentation pour l'imbrication
                              (passé à '    ' depuis render_recipe).
    lib/search.php            render_search_form(), render_search_results()
                              Génère du HTML indenté. Dropdown difficulté alimenté par
                              $DIFFICULTY_LEVELS (niveaux > 0).
    css/base.css              Variables CSS (:root), reset, body/liens, layout sticky header.
                              @media print général (couleurs, body, a). Partageable avec le site hôte.
    css/recipes.css           Formulaire de recherche, listing catégories <details>, fiche recette,
                              image héros, galerie hover, messages d'état, @media print recettes.
                              Dépend des variables :root définies dans base.css.
    js/recipe.js              Ouvre les <details> catégories au chargement.
```

## Export YAML — format

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
    data: ""                 # base64 ; vide si aucune icône
  - level: 1
    label: Facile
    mime_type: image/png
    data: "<base64>"
  # … niveaux 2 et 3 …
recipes:
  - code: GATEAU_CHOC
    name: Gâteau au chocolat
    difficulty: 2
    serving: "6 parts"       # quantité/portions ; "" si non renseigné
    prep_time: 30
    wait_time: null
    description: "<p>…</p>"
    comments: ""
    source: Larousse Gastronomique   # null si aucune
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

## Export PHP — layout target/
```
target/
  index.php
  lib/
    .htaccess    ← protège tout le répertoire lib/
    config.php   ← généré depuis config.php.tpl (inclut SITE_TYPE)
    media.php    ← sert les images depuis la DB ; cache disque dans media/
    db.php / recipe.php / display.php / technique.php / search.php
  css/base.css
  css/recipes.css
  js/recipe.js
  media/         ← cache disque (créé vide à l'export, alimenté par media.php)
```

## Affichage recette PHP
1. `<h1>` nom  +  catégories cadrées à droite
2. Card : ligne méta — quantité/portions (`serving`) + difficulté (icône bitmap + libellé depuis `$DIFFICULTY_LEVELS`) + durée totale (prép+attente)
3. Table ingrédients : prefix | qty unité (plurielle si `unit_plural` et `name_plural` renseigné) | séparateur **nom** (pluriel si `ingredient_plural` et `name_plural` renseigné) suffix
4. Section réalisation (HTML parsé)
5. Section commentaires (HTML parsé) — si non vide
6. Section techniques mentionnées (récursif, dédupliqué) — si présentes
7. Galerie d'images supplémentaires — si présentes
8. Source cadrée à droite

## Page accueil PHP
- Formulaire recherche : texte libre + select catégorie + select ingrédient + select difficulté + select technique (déclenche submit)
- Sans critère : listing `<details open>` par catégorie → liens recettes
- Avec critère : liste résultats `search_recipes()`

## URL
- Accueil : `index.php` (sans paramètre)
- Recette : `index.php?RECIPE=CODE`
- Technique standalone : `index.php?tech=CODE`
- Recherche : `index.php?q=…&cat=ID&ing=ID&diff=N`

## Makefile (cible par défaut : `help`)
`help venv venv-update install run test coverage lint format hooks designer dist clean`

## Fichiers projet
```
Makefile  environment.yml  pyproject.toml  LICENSE  CLAUDE.md  SPECS.md
src/  tests/
```

## Tests
- `tests/test_config.py`    : defaults, fallback string, roundtrip YAML
- `tests/test_sqlite_db.py` : CRUD category/recipe/technique, search
- `tests/test_html_editor.py`: tests unitaires de _clean_html() et HtmlEditor
