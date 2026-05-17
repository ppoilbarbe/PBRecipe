<?php
declare(strict_types=1);

require_once __DIR__ . '/lib/config.php';

if (SITE_DEBUG) {
    ini_set('display_errors', 1);
    ini_set('display_startup_errors', 1);
    error_reporting(E_ALL);
}
require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/recipe.php';
require_once __DIR__ . '/lib/display.php';
require_once __DIR__ . '/lib/search.php';
require_once __DIR__ . '/lib/technique.php';

// ── Globals depuis la base de données ────────────────────────────────────────
$_globals = get_globals_map();
$STRINGS  = array_merge([
    'site_title'           => 'Mes Recettes',
    'serving_label'        => 'Quantité',
    'duration_label'       => 'Durée',
    'prep_label'           => 'Préparation',
    'wait_label'           => 'Attente',
    'cook_label'           => 'Cuisson',
    'ingredients_label'    => 'Ingrédients',
    'description_label'    => 'Réalisation',
    'comments_label'       => 'Commentaires',
    'source_label'         => 'Source',
    'techniques_label'     => 'Techniques',
    'search_placeholder'   => 'Rechercher une recette...',
    'all_categories'       => 'Toutes catégories',
    'all_difficulties'     => 'Toutes difficultés',
    'all_sources'          => 'Toutes sources',
    'search_by_ingredient' => 'Par ingrédient',
    'show_techniques'      => 'Afficher une technique',
    'no_results'           => 'Aucune recette trouvée.',
], array_filter($_globals, fn($v) => $v !== ''));
$SITE_TITLE        = $STRINGS['site_title'];
$SITE_PRESENTATION = $_globals['presentation'] ?? '';

// ── Routing ──────────────────────────────────────────────────────────────────

$recipe_code = isset($_GET['RECIPE']) ? trim($_GET['RECIPE']) : '';
$tech_code   = isset($_GET['tech'])   ? trim($_GET['tech'])   : '';
$q           = isset($_GET['q'])      ? trim($_GET['q'])      : '';
$cat_id      = isset($_GET['cat'])    ? (int)$_GET['cat']     : 0;
$ing_id      = isset($_GET['ing'])    ? (int)$_GET['ing']     : 0;
$diff        = isset($_GET['diff'])   ? (int)$_GET['diff']    : -1;
$src_id      = isset($_GET['src'])    ? (int)$_GET['src']     : 0;

$is_search = ($q !== '' || $cat_id > 0 || $ing_id > 0 || $diff >= 0 || $src_id > 0);

// ── Page content ─────────────────────────────────────────────────────────────

$page_title = $SITE_TITLE;
$body       = '';

if ($recipe_code !== '') {
    // ── Recipe detail ────────────────────────────────────────────────────────
    $recipe = get_recipe($recipe_code);
    if ($recipe === null) {
        $body = '<p class="error">Recette introuvable : ' . h($recipe_code) . '</p>';
    } else {
        $page_title = h($recipe['name']) . ' — ' . $SITE_TITLE;
        $body       = render_recipe($recipe, $STRINGS);
    }

} elseif ($tech_code !== '') {
    // ── Single technique display ─────────────────────────────────────────────
    require_once __DIR__ . '/lib/technique.php';
    $tech = get_technique($tech_code);
    if ($tech === null) {
        $body = '<p class="error">Technique introuvable : ' . h($tech_code) . '</p>';
    } else {
        $resolved = resolve_techniques($tech['description'], []);
        $body  = render_techniques_panel([$tech_code => $tech] + $resolved,
                                         $STRINGS['techniques_label'] ?? 'Techniques');
    }

} else {
    // ── Home: search + category listing ─────────────────────────────────────
    $categories  = get_all_categories();
    $ingredients = get_all_ingredients();
    $techniques  = get_all_techniques();
    $sources     = get_all_sources();

    if ($SITE_PRESENTATION !== '') {
        $body .= "<div class=\"site-presentation\">" . parse_markers($SITE_PRESENTATION, true) . "</div>\n";
    }

    $body .= render_search_form(
        $categories, $ingredients, $techniques, $STRINGS, $sources,
        ['q' => $q, 'cat' => $cat_id, 'ing' => $ing_id, 'diff' => $diff, 'src' => $src_id, 'tech' => $tech_code]
    );

    if ($is_search) {
        $results = search_recipes($q, $cat_id, $ing_id, $diff, $src_id);
        $body .= render_search_results($results, $STRINGS['no_results'] ?? 'Aucune recette trouvée.');
    } else {
        $grouped = get_recipes_by_category();
        $body   .= render_category_listing($grouped);
    }
}

// ── HTML skeleton ────────────────────────────────────────────────────────────

$_site_lib = __DIR__ . '/../include/recipe_integration.lib.php';
if (file_exists($_site_lib)) {
    require_once $_site_lib;
}
$_integrated = function_exists('recipe_header');

if ($_integrated):
    recipe_header(SITE_TYPE);
?>
<body>
<?php recipe_body(SITE_TYPE) ?>
  <?= $body ?>
  <script src="js/recipe.js"></script>
<?php
    recipe_footer(SITE_TYPE);
?>
</body>
</html>
<?php else: ?>
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= $page_title ?></title>
  <link rel="stylesheet" href="css/base.css">
  <link rel="stylesheet" href="css/recipes.css">
</head>
<body>
  <header class="site-header">
    <a href="?" class="site-title"><?= h($SITE_TITLE) ?></a>
  </header>

  <main class="site-main">
    <?= $body ?>
  </main>

  <footer class="site-footer">
    <p><?= h($SITE_TITLE) ?></p>
  </footer>

  <script src="js/recipe.js"></script>
</body>
</html>
<?php endif;
