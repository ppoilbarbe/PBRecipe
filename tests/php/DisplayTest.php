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

    public function test_parse_markers_img_missing_shows_fallback(): void
    {
        $html = parse_markers('[IMG:PHOTO1]');
        $this->assertStringContainsString('img-missing', $html);
        $this->assertStringContainsString('PHOTO1', $html);
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
