# Mode

`mixed-en` — Code in English, everything else in French.

# Cohérence PHP

Toute modification du schéma de base de données (`schema.py`) ou des paramètres de configuration
(`recipe_config.py` — `_DEFAULT_STRINGS`, `DbConfig`, `RecipeConfig`) doit être répercutée dans
les fichiers PHP statiques (`resources/php/`) et dans le générateur d'export (`php_export.py`) :
- Nouvelle table ou colonne → vérifier `db.php`, `recipe.php`, `display.php`, `search.php`
- Nouveau fichier généré → l'ajouter dans `_write_*` et le charger dans `index.php`
- Suppression ou renommage de clé string → vérifier tous les `$strings[…]` dans les PHP
