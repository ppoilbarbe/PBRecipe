<?php
// SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
// SPDX-License-Identifier: AGPL-3.0-or-later
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

    // Text search + no-group toggle (flat alphabetical listing instead of category groups)
    $qval     = h($current['q'] ?? '');
    $no_group = !empty($current['no_group']);
    $html .= "  <div class=\"search-filter-group search-text-group\">\n";
    $html .= "    <input type=\"text\" name=\"q\" value=\"" . $qval . "\"\n";
    $html .= "           placeholder=\"" . h($strings['search_placeholder'] ?? 'Rechercher…') . "\">\n";
    $html .= "    <div class=\"search-mode-toggle\">\n";
    $html .= "      <label><input type=\"checkbox\" name=\"no_group\" value=\"1\""
           . ($no_group ? ' checked' : '') . "> " . h($strings['no_group_label'] ?? 'Ne pas grouper') . "</label>\n";
    $html .= "    </div>\n";
    $html .= "  </div>\n";

    // Categories — multi-select with Tom Select
    if (!empty($categories)) {
        $current_cats = array_map('intval', (array)($current['cats'] ?? []));
        $cat_mode     = ($current['cat_mode'] ?? 'or') === 'and' ? 'and' : 'or';
        $placeholder  = h($strings['all_categories'] ?? 'Par catégorie');
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

    // Difficulty — multi-select with Tom Select + OR/ET toggle
    $diff_levels = array_filter(get_difficulty_levels(), fn($d) => $d > 0, ARRAY_FILTER_USE_KEY);
    if (!empty($diff_levels)) {
        $current_diffs = array_map('intval', (array)($current['diffs'] ?? []));
        $diff_mode     = ($current['diff_mode'] ?? 'or') === 'and' ? 'and' : 'or';
        $placeholder   = 'Par ' . h($strings['difficulty_label'] ?? 'Difficulté');
        $lbl_or        = h($strings['mode_or']  ?? 'OU');
        $lbl_and       = h($strings['mode_and'] ?? 'ET');
        $html .= "  <div class=\"search-filter-group\">\n";
        $html .= "    <select name=\"diff[]\" id=\"ts-diff\" multiple data-placeholder=\"" . $placeholder . "\">\n";
        foreach ($diff_levels as $d => $info) {
            $label = $info['label'] !== '' ? $info['label'] : "Niveau $d";
            $sel   = in_array((int)$d, $current_diffs, true) ? ' selected' : '';
            $html .= "      <option value=\"" . (int)$d . "\"" . $sel . ">" . h($label) . "</option>\n";
        }
        $html .= "    </select>\n";
        $html .= "    <div class=\"search-mode-toggle\">\n";
        $html .= "      <label><input type=\"radio\" name=\"diff_mode\" value=\"or\"" . ($diff_mode === 'or' ? ' checked' : '') . "> $lbl_or</label>\n";
        $html .= "      <label><input type=\"radio\" name=\"diff_mode\" value=\"and\"" . ($diff_mode === 'and' ? ' checked' : '') . "> $lbl_and</label>\n";
        $html .= "    </div>\n";
        $html .= "  </div>\n";
    }

    // Sources — multi-select with Tom Select (always OR)
    if (!empty($sources)) {
        $current_srcs = array_map('intval', (array)($current['srcs'] ?? []));
        $placeholder  = h($strings['all_sources'] ?? 'Par source');
        $html .= "  <div class=\"search-filter-group\">\n";
        $html .= "    <select name=\"src[]\" id=\"ts-src\" multiple data-placeholder=\"" . $placeholder . "\">\n";
        foreach ($sources as $s) {
            $sel   = in_array((int)$s['id'], $current_srcs, true) ? ' selected' : '';
            $label = trim((string)($s['shortcut'] ?? '')) !== ''
                ? $s['shortcut']
                : strip_tags($s['name']);
            $html .= "      <option value=\"" . (int)$s['id'] . "\"" . $sel . ">" . h($label) . "</option>\n";
        }
        $html .= "    </select>\n";
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
