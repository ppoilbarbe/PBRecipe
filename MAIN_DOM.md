# DOM — Page principale (`index.php`)

La page principale gère trois routes selon les paramètres GET reçus.
Les éléments en pointillés sont conditionnels ou optionnels.

---

## Squelette HTML (mode standalone)

> En mode intégré (`recipe_integration.lib.php` présent), `recipe_header()` / `recipe_body()` /
> `recipe_footer()` du site hôte enveloppent le contenu à la place du squelette ci-dessous.

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    html["html · lang=fr"]
    head["head"]
    body["body"]

    html --> head
    html --> body

    head --> charset["meta · charset=UTF-8"]
    head --> vp["meta · name=viewport"]
    head --> title["title · $page_title"]
    head --> css1["link · css/base.css"]
    head --> css2["link · css/recipes.css"]

    body --> header["header.site-header"]
    body --> main["main.site-main"]
    body --> footer["footer.site-footer"]
    body --> js["script · js/recipe.js"]

    header --> sitelink["a.site-title · href=?"]
    footer  --> sitename["p · SITE_TITLE"]

    main --> route{"Route"}
    route -- "?RECIPE=CODE" --> recipe["article.recipe\n→ voir RECIPE_DOM.md"]
    route -- "?tech=CODE"   --> techpanel["section.recipe-techniques\n→ voir Panneau techniques"]
    route -- "accueil"      --> home["form.search-form\n+ div.category-listing"]
    route -- "recherche"    --> search["form.search-form\n+ ul.recipe-links.search-results"]
```

---

## Route accueil — listing par catégorie

Affiché quand aucun filtre de recherche n'est actif.

```mermaid
graph TD
    main["main.site-main"]

    main --> form["form.search-form\n→ voir Formulaire de recherche"]
    main --> listing["div.category-listing"]

    listing --> details["details.category-block · open\n(1 par catégorie)"]

    details --> summary["summary.category-name"]
    details --> ul["ul.recipe-links"]

    ul --> li["li (1 par recette)"]
    li --> a["a · href=?RECIPE=CODE"]
```

---

## Route recherche — résultats

Affiché quand au moins un filtre est actif (`q`, `cat`, `ing` ou `diff`).

```mermaid
graph TD
    main["main.site-main"]

    main --> form["form.search-form\n→ voir Formulaire de recherche"]
    main --> results{"Résultats ?"}

    results -- "aucun" --> nores["p.no-results"]
    results -- "trouvés" --> ul["ul.recipe-links.search-results"]

    ul --> li["li (1 par recette)"]
    li --> a["a · href=?RECIPE=CODE"]
```

---

## Route technique — `?tech=CODE`

Affiche une technique isolée (sans fiche recette).

```mermaid
graph TD
    main["main.site-main"]

    main --> form["form.search-form\n→ voir Formulaire de recherche"]
    main --> found{"Technique trouvée ?"}

    found -- "non"  --> err["p.error"]
    found -- "oui"  --> panel["section.recipe-techniques.recipe-section"]

    panel --> h2["h2 · label Techniques"]
    panel --> tech["div.technique · id=tech-CODE\n(1 par technique, résolution récursive)"]

    tech --> h3["h3 · titre"]
    tech --> body["div.technique-body\n(HTML + marqueurs parsés)"]
```

---

## Formulaire de recherche (`form.search-form`)

Présent dans toutes les routes de la page principale.

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    form["form.search-form · method=GET"]

    form --> q["input[type=text] · name=q"]
    form --> selcat["select · name=cat"]
    form --> seling["select · name=ing"]
    form --> seldiff["select · name=diff"]
    form --> btn["button[type=submit]"]
    form --> seltech["select · name=tech\n(si techniques disponibles)"]:::opt

    selcat --> optcat0["option · valeur=0 · Toutes catégories"]
    selcat --> optcatn["option · valeur=id (1 par catégorie)"]

    seling --> opting0["option · valeur=0 · Par ingrédient"]
    seling --> optingn["option · valeur=id (1 par ingrédient)"]

    seldiff --> optdiff0["option · valeur=-1 · Toutes difficultés"]
    seldiff --> optdiffn["option · valeur=level (1 par niveau)"]

    seltech --> opttech0["option · valeur=vide · Afficher une technique"]:::opt
    seltech --> opttechn["option · valeur=code (1 par technique)"]:::opt
```
