<?php
require_once __DIR__ . '/display.php';

/** Render the search form. */
function render_search_form(
    array $categories,
    array $ingredients,
    array $techniques,
    array $strings,
    array $current = []
): string {
    $html  = "<form class=\"search-form\" method=\"get\" action=\"\">\n";

    // Text search
    $qval  = h($current['q'] ?? '');
    $html .= "  <input type=\"text\" name=\"q\" value=\"" . $qval . "\"\n";
    $html .= "         placeholder=\"" . h($strings['search_placeholder'] ?? 'Rechercher…') . "\">\n";

    // Category
    $html .= "  <select name=\"cat\">\n";
    $html .= "    <option value=\"0\">" . h($strings['all_categories'] ?? 'Toutes catégories') . "</option>\n";
    foreach ($categories as $c) {
        $sel   = ($current['cat'] ?? 0) == $c['id'] ? ' selected' : '';
        $html .= "    <option value=\"" . (int)$c['id'] . "\"" . $sel . ">" . h($c['name']) . "</option>\n";
    }
    $html .= "  </select>\n";

    // Ingredient
    $html .= "  <select name=\"ing\">\n";
    $html .= "    <option value=\"0\">" . h($strings['search_by_ingredient'] ?? 'Par ingrédient') . "</option>\n";
    foreach ($ingredients as $i) {
        $sel   = ($current['ing'] ?? 0) == $i['id'] ? ' selected' : '';
        $html .= "    <option value=\"" . (int)$i['id'] . "\"" . $sel . ">" . h($i['name']) . "</option>\n";
    }
    $html .= "  </select>\n";

    // Difficulty
    $html .= "  <select name=\"diff\">\n";
    $html .= "    <option value=\"-1\">" . h($strings['all_difficulties'] ?? 'Toutes difficultés') . "</option>\n";
    foreach (get_difficulty_levels() as $d => $info) {
        if ($d <= 0) continue;
        $sel   = ($current['diff'] ?? -1) == $d ? ' selected' : '';
        $label = $info['label'] !== '' ? $info['label'] : "Niveau $d";
        $html .= "    <option value=\"" . (int)$d . "\"" . $sel . ">" . h($label) . "</option>\n";
    }
    $html .= "  </select>\n";

    $html .= "  <button type=\"submit\">Rechercher</button>\n";

    // Technique selector (standalone display)
    if (!empty($techniques)) {
        $html .= "  <select name=\"tech\" onchange=\"this.form.submit()\">\n";
        $html .= "    <option value=\"\">" . h($strings['show_techniques'] ?? 'Afficher une technique') . "</option>\n";
        foreach ($techniques as $t) {
            $sel   = ($current['tech'] ?? '') === $t['code'] ? ' selected' : '';
            $html .= "    <option value=\"" . h($t['code']) . "\"" . $sel . ">" . h($t['title']) . "</option>\n";
        }
        $html .= "  </select>\n";
    }

    $html .= "</form>\n";
    return $html;
}

/** Render a search-results list. */
function render_search_results(array $results, string $no_results_msg): string {
    if (empty($results)) {
        return "<p class=\"no-results\">" . h($no_results_msg) . "</p>\n";
    }
    $html = "<ul class=\"recipe-links search-results\">\n";
    foreach ($results as $r) {
        $html .= "  <li>"
               . "<a href=\"?RECIPE=" . urlencode($r['code']) . "\">" . h($r['name']) . "</a>"
               . "</li>\n";
    }
    $html .= "</ul>\n";
    return $html;
}
