DOM — Main page (``index.php``)
===============================

The main page handles three routes depending on the GET parameters received.
Dashed elements are conditional or optional.

HTML skeleton (standalone mode)
-------------------------------


.. note::

   In integration mode (``recipe_integration.lib.php`` present), the host site's ``recipe_header()`` /
   ``recipe_body()`` / ``recipe_footer()`` wrap the content instead of the skeleton below.


.. mermaid::

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
       route -- "?RECIPE=CODE" --> recipe["article.recipe<br/>→ see DOM — Recipe card"]
       route -- "?tech=CODE"   --> techpanel["section.recipe-techniques<br/>→ see Techniques panel"]
       route -- "home"         --> home["form.search-form<br/>+ div.category-listing"]
       route -- "search"       --> search["form.search-form<br/>+ ul.recipe-links.search-results"]

Home route — category listing
-----------------------------

Displayed when no search filter is active.


.. mermaid::

   graph TD
       main["main.site-main"]

       main --> form["form.search-form<br/>→ see Search form"]
       main --> listing["div.category-listing"]

       listing --> details["details.category-block · open<br/>(1 per category)"]

       details --> summary["summary.category-name"]
       details --> ul["ul.recipe-links"]

       ul --> li["li (1 per recipe)"]
       li --> a["a · href=?RECIPE=CODE"]

Search route — results
----------------------

Displayed when at least one filter is active (``q``, ``cat``, ``ing`` or ``diff``).


.. mermaid::

   graph TD
       main["main.site-main"]

       main --> form["form.search-form<br/>→ see Search form"]
       main --> results{"Results?"}

       results -- "none" --> nores["p.no-results"]
       results -- "found" --> ul["ul.recipe-links.search-results"]

       ul --> li["li (1 per recipe)"]
       li --> a["a · href=?RECIPE=CODE"]

Technique route — ``?tech=CODE``
--------------------------------

Displays a standalone technique (without a recipe card).


.. mermaid::

   graph TD
       main["main.site-main"]

       main --> form["form.search-form<br/>→ see Search form"]
       main --> found{"Technique found?"}

       found -- "no"  --> err["p.error"]
       found -- "yes" --> panel["section.recipe-techniques.recipe-section"]

       panel --> h2["h2 · Techniques label"]
       panel --> tech["div.technique · id=tech-CODE<br/>(1 per technique, recursive resolution)"]

       tech --> h3["h3 · title"]
       tech --> body["div.technique-body<br/>(HTML + parsed markers)"]

Search form (``form.search-form``)
----------------------------------

Present in all routes of the main page.


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       form["form.search-form · method=GET"]

       form --> q["input[type=text] · name=q"]
       form --> grpcat["div.search-filter-group<br/>(if categories available)"]:::opt
       form --> grping["div.search-filter-group<br/>(if ingredients available)"]:::opt
       form --> seldiff["select · name=diff<br/>(if difficulty levels > 0 defined)"]:::opt
       form --> grpsrc["div.search-filter-group<br/>(if sources available)"]:::opt
       form --> seltech["select · name=tech<br/>(if techniques available)"]:::opt
       form --> btn["button[type=submit]"]

       grpcat --> selcat["select · name=cat[] · id=ts-cat · multiple<br/>(Tom Select)"]
       grpcat --> togcat["div.search-mode-toggle<br/>(radio cat_mode=or|and)"]
       selcat --> optcatn["option · value=id (1 per category)"]

       grping --> seling["select · name=ing[] · id=ts-ing · multiple<br/>(Tom Select)"]
       grping --> toging["div.search-mode-toggle<br/>(radio ing_mode=or|and)"]
       seling --> optingn["option · value=id (1 per ingredient)"]

       seldiff --> optdiff0["option · value=-1 · Toutes difficultés"]
       seldiff --> optdiffn["option · value=level (1 per level)"]

       grpsrc --> selsrc["select · name=src[] · id=ts-src · multiple<br/>(Tom Select)"]
       grpsrc --> togsrc["div.search-mode-toggle<br/>(radio src_mode=or|and)"]
       selsrc --> optsrcn["option · value=id (1 per source)"]

       seltech --> opttech0["option · value=empty · Afficher une technique"]:::opt
       seltech --> opttechn["option · value=code (1 per technique)"]:::opt


.. note::

   The category / ingredient / source multi-selects are initialised by Tom Select
   (``js/recipe.js``). Logic: AND between dimensions; OR or AND within a dimension.
   Note: AND mode on sources always returns 0 results because ``source_id`` is a direct
   1:1 FK — a recipe can only belong to one source.
