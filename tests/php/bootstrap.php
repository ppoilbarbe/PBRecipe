<?php
declare(strict_types=1);

// La base de test est créée par tests/test_php_fixtures.py (make test-php).
// Son chemin est transmis via la variable d'environnement PBRECIPE_TEST_DB.

$dbPath = getenv('PBRECIPE_TEST_DB');
if ($dbPath === false || $dbPath === '') {
    fwrite(STDERR, "Erreur : PBRECIPE_TEST_DB n'est pas défini.\n");
    fwrite(STDERR, "Utiliser `make test-php` pour lancer la suite PHP.\n");
    exit(1);
}

define('DB_TYPE', 'sqlite');
define('DB_PATH', $dbPath);
define('SITE_TITLE', 'Test Recipes');

// $DIFFICULTY_LEVELS doit être défini avant que display.php ne soit chargé,
// pour que le `if (!isset($DIFFICULTY_LEVELS))` ne l'écrase pas.
$DIFFICULTY_LEVELS = [
    1 => ['label' => 'Facile',    'icon' => ''],
    2 => ['label' => 'Moyen',     'icon' => ''],
    3 => ['label' => 'Difficile', 'icon' => ''],
];
