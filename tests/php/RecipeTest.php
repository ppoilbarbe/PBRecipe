<?php
declare(strict_types=1);

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/db.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/display.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/recipe.php';

class RecipeTest extends TestCase
{
    // ── get_all_categories() ──────────────────────────────────────────────────

    public function test_get_all_categories_returns_all(): void
    {
        $cats = get_all_categories();
        $this->assertCount(2, $cats);
    }

    public function test_get_all_categories_sorted_by_name(): void
    {
        $cats = get_all_categories();
        // 'Dessert' < 'Entrée'
        $this->assertSame('Dessert', $cats[0]['name']);
        $this->assertSame('Entrée', $cats[1]['name']);
    }

    public function test_get_all_categories_has_id_field(): void
    {
        $cats = get_all_categories();
        $this->assertArrayHasKey('id', $cats[0]);
        $this->assertSame(1, (int)$cats[0]['id']);
    }

    // ── get_units_map() ───────────────────────────────────────────────────────

    public function test_get_units_map_returns_id_to_name(): void
    {
        $map = get_units_map();
        $this->assertSame('g',  $map[1]);
        $this->assertSame('ml', $map[2]);
    }

    // ── get_ingredients_map() ─────────────────────────────────────────────────

    public function test_get_ingredients_map_returns_id_to_name(): void
    {
        $map = get_ingredients_map();
        $this->assertSame('Farine', $map[1]);
        $this->assertSame('Sucre',  $map[2]);
    }

    // ── get_recipes_by_category() ─────────────────────────────────────────────

    public function test_get_recipes_by_category_groups_correctly(): void
    {
        $grouped = get_recipes_by_category();
        $this->assertArrayHasKey('Dessert', $grouped);
        $this->assertCount(1, $grouped['Dessert']);
        $this->assertSame('GATEAU', $grouped['Dessert'][0]['code']);
    }

    public function test_get_recipes_by_category_recipe_has_required_fields(): void
    {
        $grouped = get_recipes_by_category();
        $recipe  = $grouped['Dessert'][0];
        $this->assertArrayHasKey('code', $recipe);
        $this->assertArrayHasKey('name', $recipe);
        $this->assertArrayHasKey('difficulty', $recipe);
    }

    // ── get_recipe() ──────────────────────────────────────────────────────────

    public function test_get_recipe_returns_null_for_unknown_code(): void
    {
        $this->assertNull(get_recipe('CODE_INEXISTANT'));
    }

    public function test_get_recipe_basic_fields(): void
    {
        $r = get_recipe('GATEAU');
        $this->assertNotNull($r);
        $this->assertSame('Gâteau au chocolat', $r['name']);
        $this->assertSame(2,  (int)$r['difficulty']);
        $this->assertSame(30, (int)$r['prep_time']);
        $this->assertSame(45, (int)$r['wait_time']);
    }

    public function test_get_recipe_has_categories(): void
    {
        $r = get_recipe('GATEAU');
        $this->assertContains('Dessert', $r['categories']);
    }

    public function test_get_recipe_ingredients_in_order(): void
    {
        $r   = get_recipe('GATEAU');
        $ing = $r['ingredients'];
        $this->assertCount(2, $ing);
        $this->assertSame('Farine', $ing[0]['ingredient_name']);
        $this->assertSame('200',    $ing[0]['quantity']);
        $this->assertSame('g',      $ing[0]['unit_name']);
        $this->assertSame('Sucre',  $ing[1]['ingredient_name']);
    }

    public function test_get_recipe_ingredient_separator_and_suffix(): void
    {
        $r   = get_recipe('GATEAU');
        $ing = $r['ingredients'];
        $this->assertSame('de',      $ing[0]['separator']);
        $this->assertSame('vanillé', $ing[1]['suffix']);
    }

    public function test_get_recipe_resolves_source_name(): void
    {
        $r = get_recipe('GATEAU');
        $this->assertSame('Mon livre', $r['source']);
    }

    public function test_get_recipe_empty_source_when_none(): void
    {
        $r = get_recipe('TARTE');
        $this->assertSame('', $r['source']);
    }

    public function test_get_recipe_media_is_empty_when_none(): void
    {
        $r = get_recipe('GATEAU');
        $this->assertSame([], $r['media']);
    }

    // ── get_all_ingredients() ─────────────────────────────────────────────────

    public function test_get_all_ingredients_sorted_by_name(): void
    {
        $ings = get_all_ingredients();
        $this->assertCount(2, $ings);
        $this->assertSame('Farine', $ings[0]['name']);
        $this->assertSame('Sucre',  $ings[1]['name']);
    }

    // ── get_all_techniques() ──────────────────────────────────────────────────

    public function test_get_all_techniques_sorted_by_title(): void
    {
        $techs = get_all_techniques();
        $this->assertCount(2, $techs);
        // 'Brunoise' < 'Julienne'
        $this->assertSame('BRUNOISE', $techs[0]['code']);
        $this->assertSame('JULIENNE', $techs[1]['code']);
    }

    // ── search_recipes() ──────────────────────────────────────────────────────

    public function test_search_recipes_no_criteria_returns_all(): void
    {
        $this->assertCount(2, search_recipes());
    }

    public function test_search_recipes_by_name_substring(): void
    {
        $results = search_recipes(name: 'chocolat');
        $this->assertCount(1, $results);
        $this->assertSame('GATEAU', $results[0]['code']);
    }

    public function test_search_recipes_by_name_no_match(): void
    {
        $this->assertCount(0, search_recipes(name: 'inexistant'));
    }

    public function test_search_recipes_by_difficulty(): void
    {
        $results = search_recipes(difficulty: 1);
        $this->assertCount(1, $results);
        $this->assertSame('TARTE', $results[0]['code']);
    }

    public function test_search_recipes_by_category(): void
    {
        $results = search_recipes(category_id: 1);
        $this->assertCount(1, $results);
        $this->assertSame('GATEAU', $results[0]['code']);
    }

    public function test_search_recipes_by_ingredient(): void
    {
        $results = search_recipes(ingredient_id: 1); // Farine
        $this->assertCount(1, $results);
        $this->assertSame('GATEAU', $results[0]['code']);
    }

    public function test_search_recipes_combined_criteria_narrows_results(): void
    {
        // GATEAU est difficulté 2, TARTE est difficulté 1 — aucun n'est à la fois cat=1 ET diff=1
        $results = search_recipes(category_id: 1, difficulty: 1);
        $this->assertCount(0, $results);
    }

    public function test_search_recipes_result_has_required_fields(): void
    {
        $results = search_recipes(name: 'Gâteau');
        $this->assertArrayHasKey('code',       $results[0]);
        $this->assertArrayHasKey('name',       $results[0]);
        $this->assertArrayHasKey('difficulty', $results[0]);
    }

    public function test_search_recipes_results_sorted_by_name(): void
    {
        $results = search_recipes();
        // 'Gâteau' < 'Tarte' alphabétiquement
        $this->assertSame('GATEAU', $results[0]['code']);
        $this->assertSame('TARTE',  $results[1]['code']);
    }
}
