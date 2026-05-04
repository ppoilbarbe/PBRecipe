<?php
/**
 * Database connection — returns a PDO instance.
 * Reads constants defined in config.php.
 */

function db_connect(): PDO {
    static $pdo = null;
    if ($pdo !== null) return $pdo;

    $type = DB_TYPE;
    try {
        if ($type === 'sqlite') {
            $pdo = new PDO('sqlite:' . DB_PATH);
        } elseif ($type === 'mysql') {
            $dsn = sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
                DB_HOST, DB_PORT, DB_NAME);
            $pdo = new PDO($dsn, DB_USER, DB_PASS);
        } elseif ($type === 'pgsql') {
            $dsn = sprintf('pgsql:host=%s;port=%d;dbname=%s',
                DB_HOST, DB_PORT, DB_NAME);
            $pdo = new PDO($dsn, DB_USER, DB_PASS);
        } else {
            throw new RuntimeException("Unsupported DB_TYPE: $type");
        }
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        die('Database connection failed: ' . $e->getMessage());
    }
    return $pdo;
}
