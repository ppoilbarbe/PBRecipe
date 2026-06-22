<?php
require_once __DIR__ . '/display.php';

/** Render the search form. */
function render_search_form(
    array $categories,
    array $ingredients,
    array $techniques,
    array $strings,
    array $sources = [],
    array $current = []
): string {
    $html  = "<form class=\"search-form\" method=\"get\" action=\"\">\n";

    // Text search
    $qval  = h($current['q'] ?? '');
    $html .= "  <input type=\"text\" name=\"q\" value=\"" . $qval . "\"\n";
    $html .= "         placeholder=\"" . h($strings['search_placeholder'] ?? 'Rechercher…') . "\">\n";

    // Categories — multi-select with Tom Select
    if (!empty($categories)) {
        $current_cats = array_map('intval', (array)($current['cats'] ?? []));
        $cat_mode     = ($current['cat_mode'] ?? 'or') === 'and' ? 'and' : 'or';
        $placeholder  = h($strings['all_categories'] ?? 'Toutes catégories');
        $lbl_or       = h($strings['mode_or']  ?? 'OU');
        $lbl_and      = h($strings['mode_and'] ?? 'ET');
        $html .= "  <div class=\"search-filter-group\">\n";
        $html .= "    <select name=\"cat[]\" id=\"ts-cat\" multiple data-placeholder=\"" . $placeholder . "\">\n";
        foreach ($categories as $c) {
            $sel   = in_array((int)$c['id'], $current_cats, true) ? ' selected' : '';
            $html .= "      <option value=\"" . (int)$c['id'] . "\"" . $sel . ">" . h($c['name']) . "</option>\n";
        }
        $html .= "    </select>\n";
        $html .= "    <div class=\"search-mode-toggle\">\n";
        $html .= "      <label><input type=\"radio\" name=\"cat_mode\" value=\"or\"" . ($cat_mode === 'or' ? ' checked' : '') . "> $lbl_or</label>\n";
        $html .= "      <label><input type=\"radio\" name=\"cat_mode\" value=\"and\"" . ($cat_mode === 'and' ? ' checked' : '') . "> $lbl_and</label>\n";
        $html .= "    </div>\n";
        $html .= "  </div>\n";
    }

    // Ingredients — multi-select with Tom Select
    if (!empty($ingredients)) {
        $current_ings = array_map('intval', (array)($current['ings'] ?? []));
        $ing_mode     = ($current['ing_mode'] ?? 'or') === 'and' ? 'and' : 'or';
        $placeholder  = h($strings['search_by_ingredient'] ?? 'Par ingrédient');
        $lbl_or       = h($strings['mode_or']  ?? 'OU');
        $lbl_and      = h($strings['mode_and'] ?? 'ET');
        $html .= "  <div class=\"search-filter-group\">\n";
        $html .= "    <select name=\"ing[]\" id=\"ts-ing\" multiple data-placeholder=\"" . $placeholder . "\">\n";
        foreach ($ingredients as $i) {
            $sel   = in_array((int)$i['id'], $current_ings, true) ? ' selected' : '';
            $html .= "      <option value=\"" . (int)$i['id'] . "\"" . $sel . ">" . h($i['name']) . "</option>\n";
        }
        $html .= "    </select>\n";
        $html .= "    <div class=\"search-mode-toggle\">\n";
        $html .= "      <label><input type=\"radio\" name=\"ing_mode\" value=\"or\"" . ($ing_mode === 'or' ? ' checked' : '') . "> $lbl_or</label>\n";
        $html .= "      <label><input type=\"radio\" name=\"ing_mode\" value=\"and\"" . ($ing_mode === 'and' ? ' checked' : '') . "> $lbl_and</label>\n";
        $html .= "    </div>\n";
        $html .= "  </div>\n";
    }

    // Difficulty — single select (inchangé)
    $diff_options = '';
    foreach (get_difficulty_levels() as $d => $info) {
        if ($d <= 0) continue;
        $sel          = ($current['diff'] ?? -1) == $d ? ' selected' : '';
        $label        = $info['label'] !== '' ? $info['label'] : "Niveau $d";
        $diff_options .= "    <option value=\"" . (int)$d . "\"" . $sel . ">" . h($label) . "</option>\n";
    }
    if ($diff_options !== '') {
        $html .= "  <select name=\"diff\">\n";
        $html .= "    <option value=\"-1\">" . h($strings['all_difficulties'] ?? 'Toutes difficultés') . "</option>\n";
        $html .= $diff_options;
        $html .= "  </select>\n";
    }

    // Sources — multi-select with Tom Select
    if (!empty($sources)) {
        $current_srcs = array_map('intval', (array)($current['srcs'] ?? []));
        $src_mode     = ($current['src_mode'] ?? 'or') === 'and' ? 'and' : 'or';
        $placeholder  = h($strings['all_sources'] ?? 'Toutes sources');
        $lbl_or       = h($strings['mode_or']  ?? 'OU');
        $lbl_and      = h($strings['mode_and'] ?? 'ET');
        $html .= "  <div class=\"search-filter-group\">\n";
        $html .= "    <select name=\"src[]\" id=\"ts-src\" multiple data-placeholder=\"" . $placeholder . "\">\n";
        foreach ($sources as $s) {
            $sel   = in_array((int)$s['id'], $current_srcs, true) ? ' selected' : '';
            $html .= "      <option value=\"" . (int)$s['id'] . "\"" . $sel . ">" . h(strip_tags($s['name'])) . "</option>\n";
        }
        $html .= "    </select>\n";
        $html .= "    <div class=\"search-mode-toggle\">\n";
        $html .= "      <label><input type=\"radio\" name=\"src_mode\" value=\"or\"" . ($src_mode === 'or' ? ' checked' : '') . "> $lbl_or</label>\n";
        $html .= "      <label><input type=\"radio\" name=\"src_mode\" value=\"and\"" . ($src_mode === 'and' ? ' checked' : '') . "> $lbl_and</label>\n";
        $html .= "    </div>\n";
        $html .= "  </div>\n";
    }

    $html .= "  <button type=\"submit\">Rechercher</button>\n";

    // Technique selector (standalone display, inchangé)
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
