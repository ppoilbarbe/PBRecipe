<?php
declare(strict_types=1);

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/db.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/display.php';

class DisplayTest extends TestCase
{
    protected function setUp(): void
    {
        global $DIFFICULTY_LEVELS;
        $DIFFICULTY_LEVELS = [
            1 => ['label' => 'Facile',    'icon' => ''],
            2 => ['label' => 'Moyen',     'icon' => ''],
            3 => ['label' => 'Difficile', 'icon' => ''],
        ];
    }

    // ── render_recipe() — ligne photo / ingrédients / matériel ───────────────

    private function recipe(array $overrides = []): array
    {
        return $overrides + [
            'name' => 'R', 'categories' => [], 'serving' => '', 'difficulty' => 0,
            'prep_time' => null, 'wait_time' => null, 'cook_time' => null,
            'description' => '', 'comments' => '', 'source' => '',
            'ingredients' => [], 'equipment' => [], 'media' => [],
        ];
    }

    private function ingredient(): array
    {
        return ['prefix' => '', 'quantity' => '200', 'unit_name' => 'g', 'separator' => 'de',
                'ingredient_name' => 'Farine', 'suffix' => ''];
    }

    public function test_render_recipe_three_columns(): void
    {
        $html = render_recipe($this->recipe([
            'ingredients' => [$this->ingredient()],
            'equipment'   => [
                ['prefix' => '', 'equipment_name' => 'Fouet', 'suffix' => ''],
                ['prefix' => '2', 'equipment_name' => 'Moule <rond>',
                 'equipment_name_plural' => 'Moules <ronds>', 'equipment_plural' => 1,
                 'suffix' => 'de <i>24</i> cm'],
            ],
            'media'       => [['code' => 'IMG1', 'url' => 'media.php?x']],
        ]), ['equipment_label' => 'Matos']);
        $this->assertSame(1, substr_count($html, 'recipe-ingredients-block recipe-section'));
        $hero = strpos($html, 'hero-item');
        $ing  = strpos($html, 'class="recipe-ingredients"');
        $eq   = strpos($html, 'class="recipe-equipment"');
        $this->assertTrue($hero < $ing && $ing < $eq, 'ordre : photo, ingrédients, matériel');
        $this->assertStringContainsString('<h2>Matos</h2>', $html);
        $this->assertStringContainsString('<li><strong>Fouet</strong></li>', $html);
        $this->assertStringContainsString(
            '<li>2 <strong>Moules &lt;ronds&gt;</strong> de <i>24</i> cm</li>', $html);
    }

    public function test_render_recipe_equipment_only(): void
    {
        $html = render_recipe($this->recipe([
            'equipment' => [['prefix' => '', 'equipment_name' => 'Fouet', 'suffix' => '']],
        ]), []);
        $this->assertStringContainsString('recipe-ingredients-block recipe-section', $html);
        $this->assertStringContainsString('<h2>Matériel</h2>', $html);
        $this->assertStringNotContainsString('class="recipe-ingredients"', $html);
        $this->assertStringNotContainsString('hero-item', $html);
    }

    public function test_render_recipe_ingredients_without_equipment(): void
    {
        $html = render_recipe($this->recipe(['ingredients' => [$this->ingredient()]]), []);
        $this->assertStringContainsString('class="recipe-ingredients"', $html);
        $this->assertStringNotContainsString('recipe-equipment', $html);
    }

    public function test_render_recipe_no_ingredients_nor_equipment_moves_hero_to_gallery(): void
    {
        $html = render_recipe($this->recipe([
            'media' => [['code' => 'IMG1', 'url' => 'media.php?x']],
        ]), []);
        $this->assertStringNotContainsString('recipe-ingredients-block', $html);
        $this->assertStringNotContainsString('hero-item', $html);
        $this->assertStringContainsString('gallery-item', $html);
    }

    // ── render_db_error() ────────────────────────────────────────────────────

    private function captureErrorLog(callable $fn): array
    {
        $log  = tempnam(sys_get_temp_dir(), 'pbr');
        $prev = ini_set('error_log', $log);
        try {
            $html = $fn();
        } finally {
            ini_set('error_log', $prev === false ? '' : $prev);
        }
        $logged = (string)file_get_contents($log);
        unlink($log);
        return [$html, $logged];
    }

    public function test_render_db_error_query_failure_hints_version_mismatch(): void
    {
        $e = new PDOException('SQLSTATE[HY000]: General error: 1 no such table: recipe_equipment');
        [$html, $logged] = $this->captureErrorLog(fn() => render_db_error($e));
        $this->assertStringContainsString('class="db-error error"', $html);
        $this->assertStringContainsString('pas à la même version', $html);
        $this->assertStringContainsString('réexportez le site PHP', $html);
        // Détail technique : journal du serveur seulement (SITE_DEBUG non défini)
        $this->assertFalse(defined('SITE_DEBUG'));
        $this->assertStringNotContainsString('recipe_equipment', $html);
        $this->assertStringContainsString('no such table: recipe_equipment', $logged);
    }

    public function test_render_db_error_connection_failure(): void
    {
        $e = new DbConnectionError('SQLSTATE[HY000] [2002] Connection refused');
        [$html, $logged] = $this->captureErrorLog(fn() => render_db_error($e));
        $this->assertStringContainsString('Connexion à la base de données impossible', $html);
        $this->assertStringNotContainsString('même version', $html);
        $this->assertStringContainsString('Connection refused', $logged);
    }

    // ── pick_name() / render_named_item() ────────────────────────────────────

    public function test_pick_name_singular_plural_and_missing(): void
    {
        $row = ['equipment_name' => 'Fouet', 'equipment_name_plural' => 'Fouets'];
        $this->assertSame('Fouet',  pick_name($row, 'equipment'));
        $this->assertSame('Fouets', pick_name($row + ['equipment_plural' => 1], 'equipment'));
        // Pluriel demandé mais forme plurielle vide : singulier
        $this->assertSame('Sel', pick_name(['ingredient_name' => 'Sel', 'ingredient_name_plural' => '',
                                            'ingredient_plural' => 1], 'ingredient'));
        $this->assertSame('', pick_name([], 'unit'));
    }

    public function test_render_named_item_apostrophe_glue(): void
    {
        $this->assertSame('d&#039;<strong>huile</strong>', render_named_item("d'", 'huile', ''));
        $this->assertSame('de <strong>farine</strong> tamisée',
                          render_named_item('de', 'farine', 'tamisée'));
    }

    public function test_render_named_item_without_name(): void
    {
        $this->assertSame('papier &lt;x&gt; <b>sulfurisé</b>',
                          render_named_item('papier <x>', '', '<b>sulfurisé</b>'));
    }

    // ── h() ──────────────────────────────────────────────────────────────────

    public function test_h_escapes_angle_brackets(): void
    {
        $this->assertSame('&lt;b&gt;', h('<b>'));
    }

    public function test_h_escapes_ampersand(): void
    {
        $this->assertSame('&amp;', h('&'));
    }

    public function test_h_escapes_double_quote(): void
    {
        $this->assertSame('&quot;', h('"'));
    }

    public function test_h_escapes_single_quote(): void
    {
        $this->assertSame('&#039;', h("'"));
    }

    public function test_h_leaves_plain_text_unchanged(): void
    {
        $this->assertSame('Hello world', h('Hello world'));
    }

    public function test_h_handles_utf8(): void
    {
        $this->assertSame('Gâteau', h('Gâteau'));
    }

    // ── h_tags() ─────────────────────────────────────────────────────────────

    public function test_h_tags_allows_bold(): void
    {
        $this->assertSame('<b>gras</b>', h_tags('<b>gras</b>'));
    }

    public function test_h_tags_allows_italic_and_underline(): void
    {
        $this->assertSame('<i>a</i> <u>b</u>', h_tags('<i>a</i> <u>b</u>'));
    }

    public function test_h_tags_is_case_insensitive(): void
    {
        $this->assertSame('<b>gras</b>', h_tags('<B>gras</B>'));
    }

    public function test_h_tags_escapes_other_tags(): void
    {
        $this->assertSame('&lt;script&gt;', h_tags('<script>'));
    }

    public function test_h_tags_strips_attributes_from_allowed_tags(): void
    {
        $this->assertSame(
            '&lt;b onmouseover=alert(1)&gt;x</b>',
            h_tags('<b onmouseover=alert(1)>x</b>')
        );
    }

    public function test_h_tags_escapes_ampersand_and_quotes(): void
    {
        $this->assertSame('&amp; &quot; &#039;', h_tags('& " \''));
    }

    // ── has_visible_text() ────────────────────────────────────────────────────

    public function test_has_visible_text_null_returns_false(): void
    {
        $this->assertFalse(has_visible_text(null));
    }

    public function test_has_visible_text_empty_string_returns_false(): void
    {
        $this->assertFalse(has_visible_text(''));
    }

    public function test_has_visible_text_whitespace_only_returns_false(): void
    {
        $this->assertFalse(has_visible_text("   \t\n"));
    }

    public function test_has_visible_text_tags_with_spaces_returns_false(): void
    {
        $this->assertFalse(has_visible_text('<p>   </p>'));
    }

    public function test_has_visible_text_with_real_text_returns_true(): void
    {
        $this->assertTrue(has_visible_text('<p>Bonjour</p>'));
    }

    public function test_has_visible_text_qt_boilerplate_without_content_returns_false(): void
    {
        $qt = '<!DOCTYPE HTML PUBLIC><html><head><style>p { color: red; }</style></head>'
            . '<body>   </body></html>';
        $this->assertFalse(has_visible_text($qt));
    }

    public function test_has_visible_text_qt_boilerplate_with_content_returns_true(): void
    {
        $qt = '<!DOCTYPE HTML PUBLIC><html><head><style>p { color: red; }</style></head>'
            . '<body><p>Texte réel</p></body></html>';
        $this->assertTrue(has_visible_text($qt));
    }

    // ── render_duration() ─────────────────────────────────────────────────────

    public function test_render_duration_zero_returns_empty(): void
    {
        $this->assertSame('', render_duration(0));
    }

    public function test_render_duration_negative_returns_empty(): void
    {
        $this->assertSame('', render_duration(-5));
    }

    public function test_render_duration_minutes_only(): void
    {
        $this->assertSame('45min', render_duration(45));
    }

    public function test_render_duration_exact_hour(): void
    {
        $this->assertSame('1h', render_duration(60));
    }

    public function test_render_duration_hours_and_minutes(): void
    {
        $this->assertSame('1h30min', render_duration(90));
    }

    public function test_render_duration_multiple_hours(): void
    {
        $this->assertSame('2h15min', render_duration(135));
    }

    // ── render_difficulty() ───────────────────────────────────────────────────

    public function test_render_difficulty_zero_returns_empty(): void
    {
        $this->assertSame('', render_difficulty(0));
    }

    public function test_render_difficulty_unknown_level_returns_empty(): void
    {
        $this->assertSame('', render_difficulty(99));
    }

    public function test_render_difficulty_known_level_contains_label(): void
    {
        $html = render_difficulty(1);
        $this->assertStringContainsString('Facile', $html);
        $this->assertStringContainsString('class="difficulty"', $html);
    }

    public function test_render_difficulty_escapes_label(): void
    {
        global $DIFFICULTY_LEVELS;
        $saved = $DIFFICULTY_LEVELS;
        $DIFFICULTY_LEVELS[9] = ['label' => '<XSS>', 'icon' => ''];
        $html = render_difficulty(9);
        $this->assertStringNotContainsString('<XSS>', $html);
        $this->assertStringContainsString('&lt;XSS&gt;', $html);
        $DIFFICULTY_LEVELS = $saved;
    }

    // ── render_category_listing() ─────────────────────────────────────────────

    public function test_render_category_listing_empty_shows_message(): void
    {
        $html = render_category_listing([]);
        $this->assertStringContainsString('Aucune recette', $html);
    }

    public function test_render_category_listing_shows_category_name(): void
    {
        $grouped = [
            'Dessert' => [['code' => 'GATEAU', 'name' => 'Gâteau', 'difficulty' => 2]],
        ];
        $html = render_category_listing($grouped);
        $this->assertStringContainsString('Dessert', $html);
    }

    public function test_render_category_listing_links_to_recipe(): void
    {
        $grouped = [
            'Dessert' => [['code' => 'GATEAU', 'name' => 'Gâteau', 'difficulty' => 2]],
        ];
        $html = render_category_listing($grouped);
        $this->assertStringContainsString('?RECIPE=GATEAU', $html);
        $this->assertStringContainsString('Gâteau', $html);
    }

    public function test_render_category_listing_escapes_names(): void
    {
        $grouped = [
            '<Cat>' => [['code' => 'X', 'name' => '<Recipe>', 'difficulty' => 0]],
        ];
        $html = render_category_listing($grouped);
        $this->assertStringNotContainsString('<Cat>', $html);
        $this->assertStringContainsString('&lt;Cat&gt;', $html);
        $this->assertStringNotContainsString('<Recipe>', $html);
    }

    // ── parse_markers() ───────────────────────────────────────────────────────

    public function test_parse_markers_recipe_link_with_name(): void
    {
        $html = parse_markers('[RECIPE:GATEAU]');
        $this->assertStringContainsString('?RECIPE=GATEAU', $html);
        $this->assertStringContainsString('Gâteau au chocolat', $html);
    }

    public function test_parse_markers_unknown_recipe_uses_code_as_label(): void
    {
        $html = parse_markers('[RECIPE:INCONNU]');
        $this->assertStringContainsString('?RECIPE=INCONNU', $html);
        $this->assertStringContainsString('INCONNU', $html);
    }

    public function test_parse_markers_img_with_recipe_code(): void
    {
        $html = parse_markers('[IMG:GATEAU:PHOTO1]');
        $this->assertStringContainsString('recipe-img-ref', $html);
        $this->assertStringContainsString('media.php?recipe=GATEAU&amp;code=PHOTO1', $html);
    }

    public function test_parse_markers_tech_link(): void
    {
        $html = parse_markers('[TECH:BRUNOISE]');
        $this->assertStringContainsString('#tech-BRUNOISE', $html);
        $this->assertStringContainsString('Brunoise', $html);
    }

    public function test_parse_markers_case_insensitive(): void
    {
        $html = parse_markers('[recipe:GATEAU]');
        $this->assertStringContainsString('?RECIPE=GATEAU', $html);
    }

    public function test_parse_markers_multiple_markers_in_one_string(): void
    {
        $html = parse_markers('Voir [RECIPE:GATEAU] et [TECH:BRUNOISE].');
        $this->assertStringContainsString('?RECIPE=GATEAU', $html);
        $this->assertStringContainsString('#tech-BRUNOISE', $html);
    }
}
