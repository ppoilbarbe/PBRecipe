<?php
/**
 * Sert les images directement depuis la base de données.
 *
 * GET ?code=CODE  → recipe_media  (code en majuscules)
 * GET ?diff=N     → difficulty_levels (icône du niveau N)
 *
 * Cache disque optionnel dans ../media/ : évite de relire le BLOB à chaque
 * requête. Si le répertoire n'est pas accessible en écriture, l'image est
 * servie directement depuis la mémoire sans erreur.
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/db.php';

$_mime_ext = [
    'image/jpeg' => '.jpg',
    'image/png'  => '.png',
    'image/gif'  => '.gif',
    'image/webp' => '.webp',
    'image/bmp'  => '.bmp',
];

$_code = isset($_GET['code']) ? strtoupper(trim((string)$_GET['code'])) : null;
$_diff = isset($_GET['diff'])  ? (int)$_GET['diff']                      : null;

if ($_code !== null && $_code !== '') {
    $_cache_key = 'img_' . preg_replace('/[^A-Z0-9_]/', '_', $_code);
    $_stmt = db_connect()->prepare(
        'SELECT mime_type, data FROM recipe_media WHERE UPPER(code) = ? LIMIT 1'
    );
    $_stmt->execute([$_code]);
} elseif ($_diff !== null) {
    $_cache_key = 'diff_' . $_diff;
    $_stmt = db_connect()->prepare(
        'SELECT mime_type, data FROM difficulty_levels WHERE level = ? LIMIT 1'
    );
    $_stmt->execute([$_diff]);
} else {
    http_response_code(400);
    exit;
}

$_row = $_stmt->fetch(PDO::FETCH_ASSOC);
if (!$_row) {
    http_response_code(404);
    exit;
}

$_mime = (string)($_row['mime_type'] ?: 'application/octet-stream');
$_data = $_row['data'];
// PostgreSQL PDO peut retourner un BYTEA comme ressource de flux
if (is_resource($_data)) {
    $_data = stream_get_contents($_data);
}
$_data = (string)$_data;

if ($_data === '') {
    http_response_code(404);
    exit;
}

// Cache disque optionnel
$_cache_dir  = dirname(__DIR__) . '/media';
$_ext        = $_mime_ext[$_mime] ?? '.bin';
$_cache_file = $_cache_dir . '/' . $_cache_key . $_ext;

if (!is_file($_cache_file) || (time() - filemtime($_cache_file) > 7200)) {
    if (!is_dir($_cache_dir)) {
        @mkdir($_cache_dir, 0755, true);
    }
    @file_put_contents($_cache_file, $_data);
}

header('Content-Type: ' . $_mime);
header('Cache-Control: public, max-age=86400');
header('Content-Length: ' . strlen($_data));
echo $_data;
