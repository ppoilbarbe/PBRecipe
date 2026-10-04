<?php
// SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
// SPDX-License-Identifier: AGPL-3.0-or-later
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/display.php';

/** Clé de tri insensible à la casse, aux diacritiques et aux ligatures (œ→oe, æ→ae). */
function sort_key(string $s): string {
    $lower = mb_strtolower($s, 'UTF-8');
    $lower = strtr($lower, ['œ' => 'oe', 'æ' => 'ae', 'ß' => 'ss']);
    $ascii = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $lower);
    return $ascii !== false ? $ascii : $lower;
}

/**
 * Return the items of reference table $table (id, name) used by at least one
 * recipe through link table $link_table (column $fk), ordered by name.
 * Table and column names are internal constants, never user input.
 */
function get_used_references(string $table, string $link_table, string $fk): array {
    $rows = db_connect()->query(
        "SELECT DISTINCT t.id, t.name FROM $table t
         JOIN $link_table l ON l.$fk = t.id"
    )->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
}

/** Return categories used by at least one recipe, ordered by name. */
function get_all_categories(): array {
    return get_used_references('categories', 'recipe_categories', 'category_id');
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

/** Return recipes as a flat, alphabetically sorted list (no category grouping). */
function get_recipes_flat(): array {
    $pdo  = db_connect();
    $rows = $pdo->query('
        SELECT DISTINCT r.code, r.name, r.difficulty
        FROM recipes r
        JOIN recipe_categories rc ON rc.recipe_code = r.code
    ')->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
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

    // Equipment
    $eqs = $pdo->prepare('
        SELECT re.*,
               e.name AS equipment_name, e.name_plural AS equipment_name_plural
        FROM recipe_equipment re
        LEFT JOIN equipment e ON e.id = re.equipment_id
        WHERE re.recipe_code = ?
        ORDER BY re.position
    ');
    $eqs->execute([$code]);
    $r['equipment'] = $eqs->fetchAll();

    // Media — URL servie par media.php (source de vérité : la DB)
    $media = $pdo->prepare(
        'SELECT code FROM recipe_media WHERE recipe_code = ? ORDER BY position'
    );
    $media->execute([$code]);
    $r['media'] = [];
    foreach ($media->fetchAll() as $_mrow) {
        $_c = strtoupper((string)$_mrow['code']);
        $r['media'][] = ['code' => $_c, 'url' => media_url($code, $_c)];
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

/**
 * Build the WHERE clause restricting recipes to those linked (through
 * $link_table.$fk) to the given ids: any of them ('or') or all of them ('and').
 * Appends the bound values to $params.
 */
function link_filter(string $link_table, string $fk, array $ids, string $mode, array &$params): string {
    $ids = array_values(array_unique(array_map('intval', $ids)));
    $ph  = implode(',', array_fill(0, count($ids), '?'));
    $params = array_merge($params, $ids);
    $sql = "r.code IN (SELECT recipe_code FROM $link_table WHERE $fk IN ($ph)";
    if ($mode === 'and') {
        // count inlined as an int: bound as a string, SQLite never matches it
        $sql .= " GROUP BY recipe_code HAVING COUNT(DISTINCT $fk) = " . count($ids);
    }
    return $sql . ')';
}

/** Search recipes; returns a lightweight list. */
function search_recipes(
    string $name = '',
    array $category_ids = [],
    array $ingredient_ids = [],
    array $difficulty_ids = [],
    array $source_ids = [],
    string $cat_mode = 'or',
    string $ing_mode = 'or',
    string $diff_mode = 'or',
    array $equipment_ids = [],
    string $eq_mode = 'or'
): array {
    $pdo    = db_connect();
    $sql    = 'SELECT DISTINCT r.code, r.name, r.difficulty FROM recipes r';
    $where  = [];
    $params = [];

    if (!empty($category_ids)) {
        $where[] = link_filter('recipe_categories', 'category_id', $category_ids, $cat_mode, $params);
    }
    if (!empty($ingredient_ids)) {
        $where[] = link_filter('recipe_ingredients', 'ingredient_id', $ingredient_ids, $ing_mode, $params);
    }
    if (!empty($equipment_ids)) {
        $where[] = link_filter('recipe_equipment', 'equipment_id', $equipment_ids, $eq_mode, $params);
    }
    if ($name !== '') {
        $where[]  = 'r.name LIKE ?';
        $params[] = "%$name%";
    }
    if (!empty($difficulty_ids)) {
        $ids = array_values(array_unique(array_map('intval', $difficulty_ids)));
        $ph  = implode(',', array_fill(0, count($ids), '?'));
        if ($diff_mode === 'and' && count($ids) > 1) {
            $where[] = '1=0';
        } else {
            $where[]  = "r.difficulty IN ($ph)";
            $params   = array_merge($params, $ids);
        }
    }
    if (!empty($source_ids)) {
        $ids    = array_values(array_unique(array_map('intval', $source_ids)));
        $ph     = implode(',', array_fill(0, count($ids), '?'));
        $where[]  = "r.source_id IN ($ph)";
        $params   = array_merge($params, $ids);
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
    return get_used_references('ingredients', 'recipe_ingredients', 'ingredient_id');
}

/** Return equipment used by at least one recipe, ordered by name (singular only). */
function get_all_equipment(): array {
    return get_used_references('equipment', 'recipe_equipment', 'equipment_id');
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
        'SELECT DISTINCT s.id, s.name, s.shortcut FROM sources s
         JOIN recipes r ON r.source_id = s.id'
    )->fetchAll();
    usort($rows, fn($a, $b) => strcmp(sort_key($a['name']), sort_key($b['name'])));
    return $rows;
}
