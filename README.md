# PBRecipe

Gestionnaire de recettes (cuisine, cocktails…) avec export vers un site PHP
autonome ou en inclusion dans un site PHP plus large.

Les recettes sont stockées dans une base de données locale (SQLite) ou partagée
(MariaDB, PostgreSQL). L'application génère un site PHP complet prêt à déployer
sur un hébergement web standard.

## Fonctionnalités

- Saisie des recettes avec description HTML enrichie (titres, listes, liens, images).
- Filtre instantané de la liste des recettes, insensible à la casse et aux accents.
- Vérification orthographique et grammaticale (Grammalecte ou LanguageTool, F7).
- Gestion des référentiels : catégories, ingrédients, unités, sources, techniques,
  niveaux de difficulté (avec icône).
- Marqueurs dynamiques dans les textes : `[RECIPE:code]`, `[IMG:code]`, `[TECH:code]`.
- Import / export YAML (sauvegarde portable de toute la base).
- Export PHP : génère un site statique + dynamique déployable sur Apache/Nginx + PHP + PDO.
- Interface en français.

## Installation

### Depuis les exécutables précompilés (recommandé)

Téléchargez l'exécutable correspondant à votre système depuis la page
[Releases](https://github.com/ppoilbarbe/PBRecipe/releases) :

| Système       | Fichier                  |
|---------------|--------------------------|
| Linux (x86-64)| `pbrecipe`               |
| Windows       | `pbrecipe.exe`           |
| macOS         | `PBRecipe.app.zip`       |

**Linux / macOS**
```bash
chmod +x pbrecipe
./pbrecipe
```

**Windows** : double-cliquez sur `pbrecipe.exe`.

**macOS** : décompressez l'archive et déplacez `PBRecipe.app` dans `/Applications`.
Lors du premier lancement, autorisez l'application dans
*Réglages système → Confidentialité et sécurité*.

> Les exécutables sont autonomes — aucun Python ni bibliothèque tierce à installer.

### Depuis les sources (développeurs)

Prérequis : [Conda](https://docs.conda.io/) (Miniforge recommandé).

```bash
git clone https://github.com/ppoilbarbe/PBRecipe.git
cd PBRecipe
make venv      # crée l'environnement conda 'pbrecipe'
make install   # installe le paquet en mode éditable + git hooks
make run       # lance l'application
```

## Utilisation

```
pbrecipe [FICHIER] [OPTIONS]
```

| Argument / Option          | Description                                              |
|----------------------------|----------------------------------------------------------|
| `FICHIER`                  | Fichier de configuration `.yaml` à ouvrir au démarrage  |
| `--export-php [RÉPERTOIRE]`| Export PHP sans interface graphique                      |
| `--debug` / `--quiet`      | Niveau de journalisation (DEBUG / WARNING)               |

Au premier lancement, créez une nouvelle base via **Fichier → Nouvelle base…**.

## Schéma de la base de données

```mermaid
erDiagram
    categories {
        int     id   PK
        string  name
    }
    units {
        int     id   PK
        string  name
    }
    ingredients {
        int     id   PK
        string  name
    }
    sources {
        int     id   PK
        text    name
    }
    techniques {
        string  code        PK
        string  title
        text    description
    }
    difficulty_levels {
        int     level     PK
        string  label
        string  mime_type
        blob    data
    }
    recipes {
        string  code        PK
        string  name
        int     difficulty
        string  serving
        int     prep_time
        int     wait_time
        int     cook_time
        text    description
        text    comments
        int     source_id   FK
    }
    recipe_categories {
        string  recipe_code   FK
        int     category_id   FK
    }
    recipe_ingredients {
        int     id            PK
        string  recipe_code   FK
        int     position
        string  prefix
        string  quantity
        int     unit_id       FK
        string  separator
        int     ingredient_id FK
        string  suffix
    }
    recipe_media {
        int     id          PK
        string  recipe_code FK
        int     position
        string  code
        string  mime_type
        blob    data
    }

    recipes           }o--o|  sources            : "source_id"
    recipes           ||--o{  recipe_categories  : "recipe_code"
    categories        ||--o{  recipe_categories  : "category_id"
    recipes           ||--o{  recipe_ingredients : "recipe_code"
    units             |o--o{  recipe_ingredients : "unit_id"
    ingredients       |o--o{  recipe_ingredients : "ingredient_id"
    recipes           ||--o{  recipe_media       : "recipe_code"
```

## Développement

### Prérequis système

En plus de Conda, les outils suivants doivent être installés au niveau système :

```bash
# Couverture PHP (Xdebug pour le PHP système)
sudo apt install php-xdebug php-xml php-sqlite3   # Ubuntu/Debian
```

> **Pourquoi au niveau système ?** Le PHP embarqué dans l'environnement conda
> (`conda-forge`, actuellement 8.5) n'est pas encore supporté par Xdebug ni PCOV.
> `make coverage` bascule automatiquement sur le PHP système (8.3) quand le PHP
> conda n'a pas de driver de couverture. Sans ces paquets, la couverture PHP est
> ignorée (les tests s'exécutent quand même ; c'est le comportement normal en CI).
>
> `php-sqlite3` est requis car les tests PHP utilisent une base SQLite ; sans ce
> paquet, PHPUnit est tué par un `die()` dans `db.php` avant d'écrire le rapport.

### Couverture de code

```bash
make coverage   # rapport Python → htmlcov/index.html
                # rapport PHP    → htmlcov/php/index.html (si Xdebug disponible)
```

La cible détecte automatiquement le driver de couverture PHP disponible :

| Situation | Comportement |
|---|---|
| PHP conda + Xdebug/PCOV | Couverture via conda (optimal) |
| PHP système + Xdebug | Couverture via PHP système (fallback actuel) |
| Aucun driver | Tests PHP exécutés sans couverture + avertissement |

### Migration future — Xdebug/PCOV dans conda

Quand Xdebug ou PCOV supporteront PHP 8.5 et seront disponibles dans conda-forge,
installer le paquet dans l'environnement et simplifier la cible `coverage` du
Makefile : supprimer les branches `elif`/`else` et ne garder que l'invocation
`$(CONDA_RUN) ./vendor/bin/phpunit --coverage-html htmlcov/php`. Le commentaire
dans le Makefile rappelle exactement ce point.

## Licence

GNU GPL v3 — voir [LICENSE](LICENSE).
Licences des composants tiers : voir [LICENSES](LICENSES).
