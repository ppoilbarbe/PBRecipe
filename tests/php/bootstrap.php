<?php
declare(strict_types=1);

// Crée une base SQLite temporaire avec le schéma complet et des fixtures de test.
// La connexion statique dans db.php sera initialisée à la première utilisation.

$dbPath = sys_get_temp_dir() . '/pbrecipe_test_' . getmypid() . '.db';

if (file_exists($dbPath)) {
    unlink($dbPath);
}

define('DB_TYPE', 'sqlite');
define('DB_PATH', $dbPath);
define('SITE_TITLE', 'Test Recipes');

$bootstrap_pdo = new PDO('sqlite:' . $dbPath);
$bootstrap_pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$bootstrap_pdo->exec('PRAGMA foreign_keys = ON');

$bootstrap_pdo->exec('CREATE TABLE categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)');
$bootstrap_pdo->exec('CREATE TABLE units (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT \'\'
)');
$bootstrap_pdo->exec('CREATE TABLE ingredients (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)');
$bootstrap_pdo->exec('CREATE TABLE sources (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)');
$bootstrap_pdo->exec('CREATE TABLE techniques (
    code        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT \'\'
)');
$bootstrap_pdo->exec('CREATE TABLE recipes (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    difficulty  INTEGER NOT NULL DEFAULT 0,
    prep_time   INTEGER,
    wait_time   INTEGER,
    description TEXT NOT NULL DEFAULT \'\',
    comments    TEXT NOT NULL DEFAULT \'\',
    source_id   INTEGER REFERENCES sources(id)
)');
$bootstrap_pdo->exec('CREATE TABLE recipe_categories (
    recipe_code TEXT    REFERENCES recipes(code) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_code, category_id)
)');
$bootstrap_pdo->exec('CREATE TABLE recipe_ingredients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_code   TEXT    NOT NULL REFERENCES recipes(code) ON DELETE CASCADE,
    position      INTEGER NOT NULL DEFAULT 0,
    prefix        TEXT    NOT NULL DEFAULT \'\',
    quantity      TEXT    NOT NULL DEFAULT \'1\',
    unit_id       INTEGER REFERENCES units(id),
    separator     TEXT    NOT NULL DEFAULT \'\',
    ingredient_id INTEGER REFERENCES ingredients(id),
    suffix        TEXT    NOT NULL DEFAULT \'\'
)');
$bootstrap_pdo->exec('CREATE TABLE recipe_media (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_code TEXT    NOT NULL REFERENCES recipes(code) ON DELETE CASCADE,
    position    INTEGER NOT NULL DEFAULT 0,
    code        TEXT    NOT NULL,
    mime_type   TEXT    NOT NULL DEFAULT \'image/jpeg\',
    data        BLOB    NOT NULL
)');
$bootstrap_pdo->exec('CREATE TABLE difficulty_levels (
    level     INTEGER PRIMARY KEY,
    label     TEXT NOT NULL DEFAULT \'\',
    mime_type TEXT NOT NULL DEFAULT \'image/jpeg\',
    data      BLOB
)');

// Fixtures
$bootstrap_pdo->exec("INSERT INTO categories VALUES (1, 'Dessert'), (2, 'Entrée')");
$bootstrap_pdo->exec("INSERT INTO units VALUES (1, 'g'), (2, 'ml')");
$bootstrap_pdo->exec("INSERT INTO ingredients VALUES (1, 'Farine'), (2, 'Sucre')");
$bootstrap_pdo->exec("INSERT INTO sources VALUES (1, 'Mon livre')");
$bootstrap_pdo->exec("INSERT INTO techniques VALUES
    ('BRUNOISE', 'Brunoise', '<p>Couper en petits dés.</p>'),
    ('JULIENNE', 'Julienne', '<p>Couper en fines lamelles. [TECH:BRUNOISE]</p>')
");
$bootstrap_pdo->exec("INSERT INTO difficulty_levels VALUES
    (1, 'Facile',    'image/jpeg', NULL),
    (2, 'Moyen',     'image/jpeg', NULL),
    (3, 'Difficile', 'image/jpeg', NULL)
");
$bootstrap_pdo->exec("INSERT INTO recipes VALUES
    ('GATEAU', 'Gâteau au chocolat', 2, 30, 45,
     '<p>Mélanger les ingrédients. [TECH:BRUNOISE]</p>',
     '<p>Excellent avec de la crème. [RECIPE:TARTE]</p>', 1),
    ('TARTE', 'Tarte aux pommes', 1, 20, 40,
     '<p>Préparer la pâte brisée.</p>', '', NULL)
");
$bootstrap_pdo->exec("INSERT INTO recipe_categories VALUES ('GATEAU', 1), ('TARTE', 2)");
$bootstrap_pdo->exec("INSERT INTO recipe_ingredients
    (recipe_code, position, prefix, quantity, unit_id, separator, ingredient_id, suffix) VALUES
    ('GATEAU', 0, '', '200', 1, 'de', 1, ''),
    ('GATEAU', 1, '', '100', 2, 'de', 2, 'vanillé')
");

unset($bootstrap_pdo);

// $DIFFICULTY_LEVELS doit être défini avant que display.php ne soit chargé,
// pour que le `if (!isset($DIFFICULTY_LEVELS))` ne l'écrase pas.
$DIFFICULTY_LEVELS = [
    1 => ['label' => 'Facile',    'icon' => ''],
    2 => ['label' => 'Moyen',     'icon' => ''],
    3 => ['label' => 'Difficile', 'icon' => ''],
];
