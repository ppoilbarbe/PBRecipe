<?php
require_once __DIR__ . '/db.php';

/** Clé de tri insensible à la casse, aux diacritiques et aux ligatures (œ→oe, æ→ae). */
function sort_key(string $s): string {
    $lower = mb_strtolower($s, 'UTF-8');
    $lower = strtr($lower, ['œ' => 'oe', 'æ' => 'ae', 'ß' => 'ss']);
    $ascii = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $lower);
    return $ascii !== false ? $ascii : $lower;
}

/** Return categories used by at least one recipe, ordered by name. */
function get_all_categories(): array {
    $rows = db_connect()->query(
        'SELECT DISTINCT c.id, c.name FROM categories c
         JOIN recipe_categories rc ON rc.category_id = c.id'
    )->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
}

/** Return recipes grouped by category: [category_name => [recipe, …], …] */
function get_recipes_by_category(): array {
    $pdo = db_connect();
    $sql = '
        SELECT c.id AS cat_id, c.name AS cat_name,
               r.code, r.name AS recipe_name, r.difficulty
        FROM categories c
        JOIN recipe_categories rc ON rc.category_id = c.id
        JOIN recipes r ON r.code = rc.recipe_code
    ';
    $rows = $pdo->query($sql)->fetchAll();
    $grouped = [];
    foreach ($rows as $row) {
        $grouped[$row['cat_name']][] = [
            'code'       => $row['code'],
            'name'       => $row['recipe_name'],
            'difficulty' => $row['difficulty'],
        ];
    }
    uksort($grouped, fn($a, $b) => strcmp(sort_key($a), sort_key($b)));
    foreach ($grouped as &$recipes) {
        usort($recipes, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    }
    return $grouped;
}

/** Return all units as an id → name map. */
function get_units_map(): array {
    $pdo = db_connect();
    $map = [];
    foreach ($pdo->query('SELECT id, name FROM units')->fetchAll() as $r) {
        $map[$r['id']] = $r['name'];
    }
    return $map;
}

/** Return all ingredients as an id → name map. */
function get_ingredients_map(): array {
    $pdo = db_connect();
    $map = [];
    foreach ($pdo->query('SELECT id, name FROM ingredients')->fetchAll() as $r) {
        $map[$r['id']] = $r['name'];
    }
    return $map;
}

/** Fetch a single recipe by code (null if not found). */
function get_recipe(string $code): ?array {
    $pdo = db_connect();

    $recipe = $pdo->prepare('SELECT * FROM recipes WHERE code = ?');
    $recipe->execute([$code]);
    $r = $recipe->fetch();
    if (!$r) return null;

    // Categories
    $cats = $pdo->prepare('
        SELECT c.name FROM categories c
        JOIN recipe_categories rc ON rc.category_id = c.id
        WHERE rc.recipe_code = ?
        ORDER BY c.name
    ');
    $cats->execute([$code]);
    $r['categories'] = array_column($cats->fetchAll(), 'name');

    // Ingredients
    $ings = $pdo->prepare('
        SELECT ri.*,
               u.name AS unit_name, u.name_plural AS unit_name_plural,
               i.name AS ingredient_name, i.name_plural AS ingredient_name_plural
        FROM recipe_ingredients ri
        LEFT JOIN units u ON u.id = ri.unit_id
        LEFT JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_code = ?
        ORDER BY ri.position
    ');
    $ings->execute([$code]);
    $r['ingredients'] = $ings->fetchAll();

    // Media — URL servie par media.php (source de vérité : la DB)
    $media = $pdo->prepare(
        'SELECT code FROM recipe_media WHERE recipe_code = ? ORDER BY position'
    );
    $media->execute([$code]);
    $r['media'] = [];
    foreach ($media->fetchAll() as $_mrow) {
        $_c = strtoupper((string)$_mrow['code']);
        $r['media'][] = ['code' => $_c, 'url' => 'media.php?code=' . urlencode($_c)];
    }
    unset($_mrow, $_c);

    // Source
    if ($r['source_id']) {
        $src = $pdo->prepare('SELECT name FROM sources WHERE id = ?');
        $src->execute([$r['source_id']]);
        $r['source'] = ($src->fetch())['name'] ?? '';
    } else {
        $r['source'] = '';
    }

    return $r;
}

/** Search recipes; returns a lightweight list. */
function search_recipes(
    string $name = '',
    array $category_ids = [],
    array $ingredient_ids = [],
    int $difficulty = -1,
    array $source_ids = [],
    string $cat_mode = 'or',
    string $ing_mode = 'or',
    string $src_mode = 'or'
): array {
    $pdo    = db_connect();
    $sql    = 'SELECT DISTINCT r.code, r.name, r.difficulty FROM recipes r';
    $where  = [];
    $params = [];

    if (!empty($category_ids)) {
        $ids   = array_values(array_unique(array_map('intval', $category_ids)));
        $ph    = implode(',', array_fill(0, count($ids), '?'));
        if ($cat_mode === 'and') {
            $where[]  = "r.code IN (SELECT recipe_code FROM recipe_categories WHERE category_id IN ($ph) GROUP BY recipe_code HAVING COUNT(DISTINCT category_id) = ?)";
            $params   = array_merge($params, $ids, [count($ids)]);
        } else {
            $where[]  = "r.code IN (SELECT recipe_code FROM recipe_categories WHERE category_id IN ($ph))";
            $params   = array_merge($params, $ids);
        }
    }
    if (!empty($ingredient_ids)) {
        $ids   = array_values(array_unique(array_map('intval', $ingredient_ids)));
        $ph    = implode(',', array_fill(0, count($ids), '?'));
        if ($ing_mode === 'and') {
            $where[]  = "r.code IN (SELECT recipe_code FROM recipe_ingredients WHERE ingredient_id IN ($ph) GROUP BY recipe_code HAVING COUNT(DISTINCT ingredient_id) = ?)";
            $params   = array_merge($params, $ids, [count($ids)]);
        } else {
            $where[]  = "r.code IN (SELECT recipe_code FROM recipe_ingredients WHERE ingredient_id IN ($ph))";
            $params   = array_merge($params, $ids);
        }
    }
    if ($name !== '') {
        $where[]  = 'r.name LIKE ?';
        $params[] = "%$name%";
    }
    if ($difficulty >= 0) {
        $where[]  = 'r.difficulty = ?';
        $params[] = $difficulty;
    }
    if (!empty($source_ids)) {
        // source_id est une FK directe sur recipes (1 recette = 1 source).
        // Le mode ET avec 2+ sources retourne logiquement 0 résultats.
        $ids   = array_values(array_unique(array_map('intval', $source_ids)));
        $ph    = implode(',', array_fill(0, count($ids), '?'));
        if ($src_mode === 'and' && count($ids) > 1) {
            $where[]  = '1=0';
        } else {
            $where[]  = "r.source_id IN ($ph)";
            $params   = array_merge($params, $ids);
        }
    }

    if ($where) $sql .= ' WHERE ' . implode(' AND ', $where);

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $results = $stmt->fetchAll();
    usort($results, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $results;
}

/** Return ingredients used by at least one recipe, ordered by name. */
function get_all_ingredients(): array {
    $rows = db_connect()->query(
        'SELECT DISTINCT i.id, i.name FROM ingredients i
         JOIN recipe_ingredients ri ON ri.ingredient_id = i.id'
    )->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
}

/** Return all techniques ordered by title (case- and diacritic-insensitive). */
function get_all_techniques(): array {
    $rows = db_connect()->query('SELECT code, title FROM techniques')->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['title']), sort_key($b['title'])));
    return $rows;
}

/** Return all globals as a key → value map (loaded once per request). */
function get_globals_map(): array {
    static $cache = null;
    if ($cache !== null) return $cache;
    $cache = [];
    foreach (db_connect()->query('SELECT `key`, value FROM globals')->fetchAll() as $r) {
        $cache[$r['key']] = $r['value'];
    }
    return $cache;
}

/** Return sources used by at least one recipe, ordered by name. */
function get_all_sources(): array {
    $rows = db_connect()->query(
        'SELECT DISTINCT s.id, s.name FROM sources s
         JOIN recipes r ON r.source_id = s.id'
    )->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
}
