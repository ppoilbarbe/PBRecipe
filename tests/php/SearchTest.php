<?php
declare(strict_types=1);

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/display.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/search.php';

class SearchTest extends TestCase
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

    private array $strings = [
        'search_placeholder'   => 'Rechercher…',
        'all_categories'       => 'Toutes catégories',
        'search_by_ingredient' => 'Par ingrédient',
        'all_difficulties'     => 'Toutes difficultés',
        'show_techniques'      => 'Afficher une technique',
        'no_results'           => 'Aucune recette trouvée.',
    ];

    // ── render_search_results() ───────────────────────────────────────────────

    public function test_render_search_results_empty_shows_no_results_message(): void
    {
        $html = render_search_results([], 'Aucune recette trouvée.');
        $this->assertStringContainsString('no-results', $html);
        $this->assertStringContainsString('Aucune recette trouvée.', $html);
    }

    public function test_render_search_results_shows_recipe_link(): void
    {
        $results = [
            ['code' => 'GATEAU', 'name' => 'Gâteau au chocolat', 'difficulty' => 2],
        ];
        $html = render_search_results($results, '');
        $this->assertStringContainsString('?RECIPE=GATEAU', $html);
        $this->assertStringContainsString('Gâteau au chocolat', $html);
    }

    public function test_render_search_results_multiple_recipes(): void
    {
        $results = [
            ['code' => 'R1', 'name' => 'Recette A', 'difficulty' => 1],
            ['code' => 'R2', 'name' => 'Recette B', 'difficulty' => 2],
        ];
        $html = render_search_results($results, '');
        $this->assertStringContainsString('?RECIPE=R1', $html);
        $this->assertStringContainsString('?RECIPE=R2', $html);
    }

    public function test_render_search_results_escapes_name(): void
    {
        $results = [['code' => 'X', 'name' => '<script>alert(1)</script>', 'difficulty' => 0]];
        $html = render_search_results($results, '');
        $this->assertStringNotContainsString('<script>', $html);
    }

    // ── render_search_form() ──────────────────────────────────────────────────

    public function test_render_search_form_contains_text_input(): void
    {
        $html = render_search_form([], [], [], $this->strings);
        $this->assertStringContainsString('<form', $html);
        $this->assertStringContainsString('name="q"', $html);
    }

    public function test_render_search_form_contains_selects(): void
    {
        $html = render_search_form([], [], [], $this->strings);
        $this->assertStringContainsString('name="cat"', $html);
        $this->assertStringContainsString('name="ing"', $html);
        $this->assertStringContainsString('name="diff"', $html);
    }

    public function test_render_search_form_populates_categories(): void
    {
        $cats = [['id' => 1, 'name' => 'Dessert'], ['id' => 2, 'name' => 'Entrée']];
        $html = render_search_form($cats, [], [], $this->strings);
        $this->assertStringContainsString('Dessert', $html);
        $this->assertStringContainsString('Entrée', $html);
    }

    public function test_render_search_form_marks_selected_category(): void
    {
        $cats = [['id' => 1, 'name' => 'Dessert']];
        $html = render_search_form($cats, [], [], $this->strings, ['cat' => 1]);
        $this->assertMatchesRegularExpression('/value="1"\s+selected/', $html);
    }

    public function test_render_search_form_preserves_search_text(): void
    {
        $html = render_search_form([], [], [], $this->strings, ['q' => 'chocolat']);
        $this->assertStringContainsString('value="chocolat"', $html);
    }

    public function test_render_search_form_no_technique_select_when_empty(): void
    {
        $html = render_search_form([], [], [], $this->strings);
        $this->assertStringNotContainsString('name="tech"', $html);
    }

    public function test_render_search_form_shows_technique_select_when_present(): void
    {
        $techs = [['code' => 'BRUNOISE', 'title' => 'Brunoise']];
        $html  = render_search_form([], [], $techs, $this->strings);
        $this->assertStringContainsString('name="tech"', $html);
        $this->assertStringContainsString('BRUNOISE', $html);
        $this->assertStringContainsString('Brunoise', $html);
    }

    public function test_render_search_form_marks_selected_technique(): void
    {
        $techs = [['code' => 'BRUNOISE', 'title' => 'Brunoise']];
        $html  = render_search_form([], [], $techs, $this->strings, ['tech' => 'BRUNOISE']);
        $this->assertMatchesRegularExpression('/value="BRUNOISE"\s+selected/', $html);
    }

    public function test_render_search_form_escapes_placeholder(): void
    {
        $strings = array_merge($this->strings, ['search_placeholder' => '<b>Chercher</b>']);
        $html    = render_search_form([], [], [], $strings);
        $this->assertStringNotContainsString('<b>Chercher</b>', $html);
        $this->assertStringContainsString('&lt;b&gt;Chercher', $html);
    }
}
