# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au versionnement **AAAA.x** (année civile + séquence).

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

[2026.1]: https://github.com/ppoilbarbe/PBRecipe/releases/tag/2026.1
