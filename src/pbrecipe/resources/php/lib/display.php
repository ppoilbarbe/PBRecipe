<?php

require_once __DIR__ . '/db.php';

/** HTML-escape a string. */
function h(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Return true if $html contains visible text (handles Qt rich-text boilerplate). */
function has_visible_text(?string $html): bool {
    if ($html === null || $html === '') return false;
    $s = preg_replace(['/<style\b[^>]*>.*?<\/style>/si', '/<!DOCTYPE[^>]*>/i'], '', $html);
    $s = html_entity_decode(strip_tags($s), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    return trim($s, " \t\n\r\0\x0B\u{00A0}") !== '';
}

/** Return the URL to serve an image by its code (via lib/media.php). */
function media_url(string $code): string {
    return 'lib/media.php?code=' . urlencode($code);
}

/**
 * Return difficulty levels as [level => ['label' => …, 'icon' => …]].
 * Uses global $DIFFICULTY_LEVELS if set (injection de tests ou index.php),
 * sinon interroge la DB et met en cache le résultat.
 */
function get_difficulty_levels(): array {
    global $DIFFICULTY_LEVELS;
    if (!empty($DIFFICULTY_LEVELS)) return $DIFFICULTY_LEVELS;
    static $cache = null;
    if ($cache !== null) return $cache;
    $cache = [];
    $stmt = db_connect()->query(
        'SELECT level, label, data FROM difficulty_levels ORDER BY level'
    );
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $d    = (int)$row['level'];
        $data = $row['data'];
        if (is_resource($data)) { $data = stream_get_contents($data); }
        $icon = ($data !== null && $data !== '')
              ? 'lib/media.php?diff=' . $d
              : '';
        $cache[$d] = ['label' => (string)$row['label'], 'icon' => $icon];
    }
    return $cache;
}

/**
 * Parse special markers in HTML recipe content:
 *   [RECIPE:CODE]   → clickable link to the recipe
 *   [IMG:CODE]      → image thumbnail with hover enlargement
 *   [TECH:CODE]     → anchor link to the technique panel
 */
/** Return code→name map for all recipes (loaded once per request). */
function recipe_name_map(): array {
    static $map = null;
    if ($map === null) {
        $map = [];
        foreach (db_connect()->query('SELECT code, name FROM recipes')->fetchAll() as $r) {
            $map[strtoupper($r['code'])] = $r['name'];
        }
    }
    return $map;
}

/** Return code→title map for all techniques (loaded once per request). */
function tech_title_map(): array {
    static $map = null;
    if ($map === null) {
        $map = [];
        foreach (db_connect()->query('SELECT code, title FROM techniques')->fetchAll() as $r) {
            $map[strtoupper($r['code'])] = $r['title'];
        }
    }
    return $map;
}

/** $url_map : ['CODE' => 'media/CODE.jpg', …] — URLs précalculées pour les médias de la recette. */
function parse_markers(string $html, array $url_map = []): string {
    // [RECIPE:CODE] — affiche le nom de la recette
    $html = preg_replace_callback(
        '/\[RECIPE:([A-Z0-9_]+)\]/i',
        function ($m) {
            $code = strtoupper($m[1]);
            $name = recipe_name_map()[$code] ?? $code;
            return '<a href="?RECIPE=' . urlencode($code) . '">' . h($name) . '</a>';
        },
        $html
    );

    // [IMG:CODE]
    $html = preg_replace_callback(
        '/\[IMG:([A-Z0-9_]+)\]/i',
        function ($m) use ($url_map) {
            $code = strtoupper($m[1]);
            $src  = $url_map[$code] ?? '';
            if ($src === '') return '<span class="img-missing">[IMG:' . h($code) . ']</span>';
            return '<span class="recipe-img-ref">'
                 . '<img src="' . h($src) . '" alt="' . h($code) . '" class="recipe-thumb" loading="lazy">'
                 . '<span class="recipe-img-preview"><img src="' . h($src) . '" alt="' . h($code) . '"></span>'
                 . '</span>';
        },
        $html
    );

    // [TECH:CODE] — affiche le titre de la technique
    $html = preg_replace_callback(
        '/\[TECH:([A-Z0-9_]+)\]/i',
        function ($m) {
            $code  = strtoupper($m[1]);
            $title = tech_title_map()[$code] ?? $code;
            return '<a href="#tech-' . h($code) . '" class="tech-link">' . h($title) . '</a>';
        },
        $html
    );

    return $html;
}

/** Render a difficulty badge from the difficulty_levels table. */
function render_difficulty(int $level): string {
    $levels = get_difficulty_levels();
    if ($level <= 0 || !isset($levels[$level])) return '';
    $info  = $levels[$level];
    $label = $info['label'] ?? '';
    $icon  = $info['icon']  ?? '';
    $html  = '<span class="difficulty" title="' . h($label) . '">';
    if ($icon !== '') {
        $html .= '<span class="diff-icon">'
               . '<img src="' . h($icon) . '" alt="' . h($label) . '" class="diff-icon-img">'
               . '</span>';
    }
    if ($label !== '') {
        $html .= '<span class="diff-label">' . h($label) . '</span>';
    }
    $html .= '</span>';
    return $html;
}

/** Render a duration in minutes as "Xh Ymin". */
function render_duration(int $minutes): string {
    if ($minutes <= 0) return '';
    $h   = intdiv($minutes, 60);
    $min = $minutes % 60;
    if ($h > 0 && $min > 0) return "{$h}h{$min}min";
    if ($h > 0)              return "{$h}h";
    return "{$min}min";
}

/** Render the full recipe page HTML (body content only). */
function render_recipe(array $recipe, array $strings): string {
    // Build code→URL map from recipe media (url is already computed in recipe.php).
    $url_map   = [];
    $hero_src  = '';
    $hero_code = '';
    $gallery   = [];
    foreach ($recipe['media'] ?? [] as $item) {
        $code = $item['code'];
        $src  = $item['url'];
        $url_map[$code] = $src;
        if ($hero_src === '') { $hero_src = $src; $hero_code = $code; }
        else                  { $gallery[] = ['code' => $code, 'src' => $src]; }
    }

    $html = "<article class=\"recipe\">\n";

    // Title
    $html .= "  <h1 class=\"recipe-title\">" . h($recipe['name']) . "</h1>\n";

    // Categories (top-right)
    if (!empty($recipe['categories'])) {
        $cats = array_map('h', $recipe['categories']);
        $html .= "  <p class=\"recipe-categories\">" . implode(', ', $cats) . "</p>\n";
    }

    $html .= "  <div class=\"recipe-card\">\n";

    // Serving
    $serving_html = '';
    if (!empty($recipe['serving'])) {
        $serving_html = '<span class="serving">'
                      . h($strings['serving_label'] ?? 'Quantité') . ' : '
                      . h($recipe['serving'])
                      . '</span>';
    }

    // Difficulty + duration row
    $diff_html = render_difficulty((int)$recipe['difficulty']);
    $total = (int)($recipe['prep_time'] ?? 0)
           + (int)($recipe['wait_time'] ?? 0)
           + (int)($recipe['cook_time'] ?? 0);
    $dur_html = '';
    if ($total > 0) {
        $dur_html = '<span class="duration">';
        $dur_html .= h($strings['duration_label'] ?? 'Durée') . ' : '
                   . render_duration($total);
        $parts = [];
        if ($recipe['prep_time']) {
            $parts[] = h($strings['prep_label'] ?? 'Prép.') . ' '
                     . render_duration((int)$recipe['prep_time']);
        }
        if ($recipe['wait_time']) {
            $parts[] = h($strings['wait_label'] ?? 'Attente') . ' '
                     . render_duration((int)$recipe['wait_time']);
        }
        if ($recipe['cook_time']) {
            $parts[] = h($strings['cook_label'] ?? 'Cuisson') . ' '
                     . render_duration((int)$recipe['cook_time']);
        }
        if (count($parts) > 1) {
            $dur_html .= ' (' . implode(' + ', $parts) . ')';
        }
        $dur_html .= '</span>';
    }
    if ($serving_html || $diff_html || $dur_html) {
        $html .= "    <div class=\"recipe-meta\">" . $serving_html . $dur_html . $diff_html . "</div>\n";
    }

    // Ingredients (with optional hero image floated left)
    if (!empty($recipe['ingredients'])) {
        if ($hero_src !== '') {
            $html .= "    <div class=\"recipe-ingredients-block recipe-section\">\n";
            $html .= "      <figure class=\"hero-item\">\n";
            $html .= "        <img src=\"" . h($hero_src) . "\" alt=\"" . h($hero_code) . "\"\n";
            $html .= "             class=\"recipe-hero-img\" loading=\"lazy\">\n";
            $html .= "        <span class=\"hero-preview\">\n";
            $html .= "          <img src=\"" . h($hero_src) . "\" alt=\"" . h($hero_code) . "\">\n";
            $html .= "        </span>\n";
            $html .= "      </figure>\n";
            $ing_indent = '      ';
        } else {
            $ing_indent = '    ';
        }
        $ing_class = $hero_src !== '' ? 'recipe-ingredients' : 'recipe-ingredients recipe-section';
        $html .= $ing_indent . "<section class=\"$ing_class\">\n";
        $html .= $ing_indent . "  <h2>" . h($strings['ingredients_label'] ?? 'Ingrédients') . "</h2>\n";
        // Premier passage : détecter si au moins un ingrédient a un préfixe
        $has_prefix = false;
        foreach ($recipe['ingredients'] as $ing) {
            if (!empty($ing['prefix'])) { $has_prefix = true; break; }
        }

        $html .= $ing_indent . "  <table class=\"ingredients-table\">\n";
        $html .= $ing_indent . "    <tbody>\n";
        foreach ($recipe['ingredients'] as $ing) {
            $sep      = (string)($ing['separator']       ?? '');
            $ing_name = (string)($ing['ingredient_name'] ?? '');

            // Colonne "reste" : séparateur + nom en gras + suffixe
            $rest_parts = [];
            if ($sep !== '') $rest_parts[] = h($sep);
            $rest = implode(' ', $rest_parts);

            if ($ing_name !== '') {
                // Pas d'espace si le séparateur se termine par une apostrophe/quote
                $last = mb_substr($sep, -1, 1, 'UTF-8');
                $glue = in_array($last, ["'", "\u{2019}", "\u{2018}", '"', "\u{201C}", "\u{201D}",
                                         "\u{201A}", "\u{201B}", "\u{2039}", "\u{203A}"], true)
                        ? '' : ' ';
                $rest .= ($rest !== '' ? $glue : '') . '<strong>' . h($ing_name) . '</strong>';
            }
            if (!empty($ing['suffix'])) {
                $rest .= ' ' . h($ing['suffix']);
            }

            $html .= $ing_indent . "      <tr>\n";
            if ($has_prefix) {
                $html .= $ing_indent . "        <td class=\"ing-prefix\">" . h((string)($ing['prefix'] ?? '')) . "</td>\n";
            }
            $qty_cell = trim(h((string)($ing['quantity'] ?? '')) . ' ' . h((string)($ing['unit_name'] ?? '')));
            $html .= $ing_indent . "        <td class=\"ing-qty\">" . $qty_cell . "</td>\n";
            $html .= $ing_indent . "        <td class=\"ing-rest\">" . $rest . "</td>\n";
            $html .= $ing_indent . "      </tr>\n";
        }
        $html .= $ing_indent . "    </tbody>\n";
        $html .= $ing_indent . "  </table>\n";
        $html .= $ing_indent . "</section>\n";
        if ($hero_src !== '') {
            $html .= "    </div>\n";
        }
    } elseif ($hero_src !== '') {
        // No ingredients — demote hero to gallery
        array_unshift($gallery, ['code' => $hero_code, 'src' => $hero_src]);
        $hero_src = '';
    }

    // Description
    if (has_visible_text($recipe['description'])) {
        $html .= "    <section class=\"recipe-description recipe-section\">\n";
        $html .= "      <h2>" . h($strings['description_label'] ?? 'Réalisation') . "</h2>\n";
        $html .= "      <div class=\"recipe-body\">" . parse_markers($recipe['description'], $url_map) . "</div>\n";
        $html .= "    </section>\n";
    }

    // Comments
    if (has_visible_text($recipe['comments'])) {
        $html .= "    <section class=\"recipe-comments recipe-section\">\n";
        $html .= "      <h2>" . h($strings['comments_label'] ?? 'Commentaires') . "</h2>\n";
        $html .= "      <div class=\"recipe-body\">" . parse_markers($recipe['comments'], $url_map) . "</div>\n";
        $html .= "    </section>\n";
    }

    // Techniques (resolved recursively)
    require_once __DIR__ . '/technique.php';
    $combined_html = ($recipe['description'] ?? '') . ($recipe['comments'] ?? '');
    $techniques    = resolve_techniques($combined_html);
    if ($techniques) {
        $html .= render_techniques_panel($techniques, $strings['techniques_label'] ?? 'Techniques', '    ');
    }

    // Gallery (remaining images, no-print)
    if (!empty($gallery)) {
        $html .= "    <div class=\"recipe-gallery no-print\">\n";
        foreach ($gallery as $item) {
            $html .= "      <figure class=\"gallery-item\">\n";
            $html .= "        <img src=\"" . h($item['src']) . "\" alt=\"" . h($item['code']) . "\"\n";
            $html .= "             class=\"gallery-thumb\" loading=\"lazy\">\n";
            $html .= "        <span class=\"gallery-preview\">\n";
            $html .= "          <img src=\"" . h($item['src']) . "\" alt=\"" . h($item['code']) . "\">\n";
            $html .= "        </span>\n";
            $html .= "      </figure>\n";
        }
        $html .= "    </div>\n";
    }

    // Source (may contain HTML)
    if (!empty($recipe['source'])) {
        $html .= "    <p class=\"recipe-source\">"
               . h($strings['source_label'] ?? 'Source') . ' : '
               . $recipe['source']
               . "</p>\n";
    }

    $html .= "  </div>\n"; // .recipe-card
    $html .= "</article>\n";
    return $html;
}

/** Render the category listing (collapsible). */
function render_category_listing(array $grouped): string {
    if (empty($grouped)) {
        return "<p>Aucune recette disponible.</p>\n";
    }
    $html = "<div class=\"category-listing\">\n";
    foreach ($grouped as $cat_name => $recipes) {
        $html .= "  <details class=\"category-block\" open>\n";
        $html .= "    <summary class=\"category-name\">" . h($cat_name) . "</summary>\n";
        $html .= "    <ul class=\"recipe-links\">\n";
        foreach ($recipes as $r) {
            $html .= "      <li>"
                   . "<a href=\"?RECIPE=" . urlencode($r['code']) . "\">" . h($r['name']) . "</a>"
                   . "</li>\n";
        }
        $html .= "    </ul>\n";
        $html .= "  </details>\n";
    }
    $html .= "</div>\n";
    return $html;
}
