<?php
declare(strict_types=1);

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/db.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/display.php';
require_once __DIR__ . '/../../src/pbrecipe/resources/php/lib/technique.php';

class TechniqueTest extends TestCase
{
    // ── extract_technique_codes() ─────────────────────────────────────────────

    public function test_extract_technique_codes_empty_string(): void
    {
        $this->assertSame([], extract_technique_codes(''));
    }

    public function test_extract_technique_codes_no_markers(): void
    {
        $this->assertSame([], extract_technique_codes('<p>Texte normal sans marqueur.</p>'));
    }

    public function test_extract_technique_codes_single_marker(): void
    {
        $codes = extract_technique_codes('Voir [TECH:BRUNOISE] pour les détails.');
        $this->assertSame(['BRUNOISE'], $codes);
    }

    public function test_extract_technique_codes_multiple_markers(): void
    {
        $codes = extract_technique_codes('[TECH:BRUNOISE] et [TECH:JULIENNE]');
        $this->assertSame(['BRUNOISE', 'JULIENNE'], $codes);
    }

    public function test_extract_technique_codes_deduplicates(): void
    {
        $codes = extract_technique_codes('[TECH:BRUNOISE] et encore [TECH:BRUNOISE]');
        $this->assertSame(['BRUNOISE'], $codes);
    }

    public function test_extract_technique_codes_case_insensitive_marker(): void
    {
        $codes = extract_technique_codes('[tech:BRUNOISE]');
        $this->assertSame(['BRUNOISE'], $codes);
    }

    public function test_extract_technique_codes_with_numbers_in_code(): void
    {
        $codes = extract_technique_codes('[TECH:STEP_42]');
        $this->assertSame(['STEP_42'], $codes);
    }

    // ── resolve_techniques() ──────────────────────────────────────────────────

    public function test_resolve_techniques_no_markers_returns_empty(): void
    {
        $result = resolve_techniques('Texte sans marqueur.');
        $this->assertSame([], $result);
    }

    public function test_resolve_techniques_unknown_code_returns_empty(): void
    {
        $result = resolve_techniques('[TECH:INCONNU]');
        $this->assertSame([], $result);
    }

    public function test_resolve_techniques_known_code(): void
    {
        $result = resolve_techniques('[TECH:BRUNOISE]');
        $this->assertArrayHasKey('BRUNOISE', $result);
        $this->assertSame('Brunoise', $result['BRUNOISE']['title']);
    }

    public function test_resolve_techniques_nested_includes_dependency_first(): void
    {
        // JULIENNE référence [TECH:BRUNOISE] dans sa description
        $result = resolve_techniques('[TECH:JULIENNE]');
        $this->assertArrayHasKey('JULIENNE', $result);
        $this->assertArrayHasKey('BRUNOISE', $result);
        $keys = array_keys($result);
        // BRUNOISE (dépendance) doit apparaître avant JULIENNE
        $this->assertLessThan(
            array_search('JULIENNE', $keys),
            array_search('BRUNOISE', $keys)
        );
    }

    public function test_resolve_techniques_cycle_guard_prevents_infinite_loop(): void
    {
        // BRUNOISE est déjà dans $seen → ne doit pas être résolu
        $result = resolve_techniques('[TECH:BRUNOISE]', ['BRUNOISE']);
        $this->assertSame([], $result);
    }

    // ── render_techniques_panel() ─────────────────────────────────────────────

    public function test_render_techniques_panel_empty_returns_empty_string(): void
    {
        $this->assertSame('', render_techniques_panel([], 'Techniques'));
    }

    public function test_render_techniques_panel_contains_section_heading(): void
    {
        $techs = [
            'BRUNOISE' => ['code' => 'BRUNOISE', 'title' => 'Brunoise', 'description' => '<p>Couper.</p>'],
        ];
        $html = render_techniques_panel($techs, 'Techniques culinaires');
        $this->assertStringContainsString('<h2>Techniques culinaires</h2>', $html);
    }

    public function test_render_techniques_panel_renders_each_technique(): void
    {
        $techs = [
            'BRUNOISE' => ['code' => 'BRUNOISE', 'title' => 'Brunoise', 'description' => ''],
            'JULIENNE' => ['code' => 'JULIENNE', 'title' => 'Julienne', 'description' => ''],
        ];
        $html = render_techniques_panel($techs, 'T');
        $this->assertStringContainsString('id="tech-BRUNOISE"', $html);
        $this->assertStringContainsString('id="tech-JULIENNE"', $html);
        $this->assertStringContainsString('Brunoise', $html);
        $this->assertStringContainsString('Julienne', $html);
    }

    public function test_render_techniques_panel_escapes_title(): void
    {
        $techs = ['X' => ['code' => 'X', 'title' => '<script>xss</script>', 'description' => '']];
        $html  = render_techniques_panel($techs, 'T');
        $this->assertStringNotContainsString('<script>', $html);
        $this->assertStringContainsString('&lt;script&gt;', $html);
    }

    public function test_render_techniques_panel_wraps_in_section(): void
    {
        $techs = ['X' => ['code' => 'X', 'title' => 'X', 'description' => '']];
        $html  = render_techniques_panel($techs, 'T');
        $this->assertStringContainsString('class="recipe-techniques"', $html);
    }
}
