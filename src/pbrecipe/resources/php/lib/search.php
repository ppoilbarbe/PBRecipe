<?php
// SPDX-FileCopyrightText: Philippe Poilbarbe <philippe@cardolan.net>
// SPDX-License-Identifier: AGPL-3.0-or-later
require_once __DIR__ . '/display.php';

/**
 * Render one multi-select filter group (Tom Select), optionally followed by an
 * OR/AND toggle.
 *
 * $options:  value (int id) => label (plain text, escaped here)
 * $selected: currently selected values
 * $mode_name: name of the OR/AND radio pair; null for no toggle
 * $or_and:   [OR label, AND label], already HTML-escaped
 */
function render_multi_filter(
    string $name,
    string $id,
    string $placeholder,
    array $options,
    array $selected,
    ?string $mode_name = null,
    string $mode = 'or',
    array $or_and = ['OU', 'ET']
): string {
    $selected = array_map('intval', $selected);
    $html  = "  <div class=\"search-filter-group\">\n";
    $html .= "    <select name=\"{$name}[]\" id=\"$id\" multiple data-placeholder=\"" . h($placeholder) . "\">\n";
    foreach ($options as $value => $label) {
        $sel   = in_array((int)$value, $selected, true) ? ' selected' : '';
        $html .= "      <option value=\"" . (int)$value . "\"" . $sel . ">" . h((string)$label) . "</option>\n";
    }
    $html .= "    </select>\n";
    if ($mode_name !== null) {
        $mode  = $mode === 'and' ? 'and' : 'or';
        [$lbl_or, $lbl_and] = $or_and;
        $html .= "    <div class=\"search-mode-toggle\">\n";
        $html .= "      <label><input type=\"radio\" name=\"$mode_name\" value=\"or\"" . ($mode === 'or' ? ' checked' : '') . "> $lbl_or</label>\n";
        $html .= "      <label><input type=\"radio\" name=\"$mode_name\" value=\"and\"" . ($mode === 'and' ? ' checked' : '') . "> $lbl_and</label>\n";
        $html .= "    </div>\n";
    }
    $html .= "  </div>\n";
    return $html;
}

/** Render the search form. */
function render_search_form(
    array $categories,
    array $ingredients,
    array $techniques,
    array $strings,
    array $sources = [],
    array $current = [],
    array $equipment = []
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

    $or_and = [h($strings['mode_or'] ?? 'OU'), h($strings['mode_and'] ?? 'ET')];

    // Categories — multi-select with Tom Select + OR/ET toggle
    if (!empty($categories)) {
        $html .= render_multi_filter(
            'cat', 'ts-cat', $strings['all_categories'] ?? 'Par catégorie',
            array_column($categories, 'name', 'id'), $current['cats'] ?? [],
            'cat_mode', $current['cat_mode'] ?? 'or', $or_and
        );
    }

    // Ingredients — multi-select with Tom Select + OR/ET toggle
    if (!empty($ingredients)) {
        $html .= render_multi_filter(
            'ing', 'ts-ing', $strings['search_by_ingredient'] ?? 'Par ingrédient',
            array_column($ingredients, 'name', 'id'), $current['ings'] ?? [],
            'ing_mode', $current['ing_mode'] ?? 'or', $or_and
        );
    }

    // Equipment — multi-select with Tom Select + OR/ET toggle (singular names)
    if (!empty($equipment)) {
        $html .= render_multi_filter(
            'eq', 'ts-eq', $strings['search_by_equipment'] ?? 'Par matériel',
            array_column($equipment, 'name', 'id'), $current['eqs'] ?? [],
            'eq_mode', $current['eq_mode'] ?? 'or', $or_and
        );
    }

    // Difficulty — multi-select with Tom Select + OR/ET toggle
    $diff_levels = array_filter(get_difficulty_levels(), fn($d) => $d > 0, ARRAY_FILTER_USE_KEY);
    if (!empty($diff_levels)) {
        $options = [];
        foreach ($diff_levels as $d => $info) {
            $options[$d] = $info['label'] !== '' ? $info['label'] : "Niveau $d";
        }
        $html .= render_multi_filter(
            'diff', 'ts-diff', 'Par ' . ($strings['difficulty_label'] ?? 'Difficulté'),
            $options, $current['diffs'] ?? [],
            'diff_mode', $current['diff_mode'] ?? 'or', $or_and
        );
    }

    // Sources — multi-select with Tom Select (always OR)
    if (!empty($sources)) {
        $options = [];
        foreach ($sources as $s) {
            $options[$s['id']] = trim((string)($s['shortcut'] ?? '')) !== ''
                ? $s['shortcut']
                : strip_tags($s['name']);
        }
        $html .= render_multi_filter(
            'src', 'ts-src', $strings['all_sources'] ?? 'Par source',
            $options, $current['srcs'] ?? []
        );
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
