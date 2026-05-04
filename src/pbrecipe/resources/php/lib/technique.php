<?php
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/display.php';

/** Fetch one technique by code (null if not found). */
function get_technique(string $code): ?array {
    $pdo = db_connect();
    $stmt = $pdo->prepare('SELECT code, title, description FROM techniques WHERE code = ?');
    $stmt->execute([$code]);
    return $stmt->fetch() ?: null;
}

/**
 * Collect all technique codes referenced by [TECH:CODE] markers in $html.
 * Returns unique codes, in order of first appearance.
 */
function extract_technique_codes(string $html): array {
    preg_match_all('/\[TECH:([A-Z0-9_]+)\]/i', $html, $m);
    return array_unique($m[1]);
}

/**
 * Resolve all techniques referenced in $html recursively, avoiding cycles.
 * Returns an ordered list of unique technique rows ready for display.
 *
 * @param string[] $seen  Codes already being resolved (cycle guard).
 */
function resolve_techniques(string $html, array $seen = []): array {
    $codes  = extract_technique_codes($html);
    $result = [];

    foreach ($codes as $code) {
        $code = strtoupper($code);
        if (in_array($code, $seen, true)) continue;  // cycle guard

        $tech = get_technique($code);
        if ($tech === null) continue;

        // Recurse into the technique's own description
        $nested = resolve_techniques($tech['description'], array_merge($seen, [$code]));

        // Add nested techniques first (depth-first), then the current one
        foreach ($nested as $n) {
            if (!isset($result[$n['code']])) {
                $result[$n['code']] = $n;
            }
        }
        if (!isset($result[$code])) {
            $result[$code] = $tech;
        }
    }

    return $result;
}

/**
 * Render the techniques panel as HTML.
 * @param string $label   Section heading (from config strings).
 * @param string $indent  Base indentation prefix for each line.
 */
function render_techniques_panel(array $techniques, string $label, string $indent = ''): string {
    if (empty($techniques)) return '';

    $i1 = $indent . '  ';
    $i2 = $indent . '    ';

    $html  = $indent . "<section class=\"recipe-techniques recipe-section\">\n";
    $html .= $i1    . "<h2>" . h($label) . "</h2>\n";
    foreach ($techniques as $tech) {
        $html .= $i1 . "<div class=\"technique\" id=\"tech-" . h($tech['code']) . "\">\n";
        $html .= $i2 . "<h3>" . h($tech['title']) . "</h3>\n";
        $html .= $i2 . "<div class=\"technique-body\">" . parse_markers($tech['description']) . "</div>\n";
        $html .= $i1 . "</div>\n";
    }
    $html .= $indent . "</section>\n";
    return $html;
}
