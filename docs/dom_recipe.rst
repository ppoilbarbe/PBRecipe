DOM — Recipe card (``?RECIPE=CODE``)
====================================

HTML structure produced by ``render_recipe()`` in ``lib/display.php``.
Dashed elements are conditional (absent when the data is empty).

General structure
-----------------


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       article["article.recipe"]

       article --> h1["h1.recipe-title"]
       article --> cats["p.recipe-categories<br/>(names separated by commas)"]:::opt
       article --> card["div.recipe-card"]

       card --> meta["div.recipe-meta"]:::opt
       card --> ingblock["div.recipe-ingredients-block.recipe-section<br/>(hero image / ingredients / equipment — see detail)"]:::opt
       card --> desc["section.recipe-description.recipe-section"]:::opt
       card --> comm["section.recipe-comments.recipe-section"]:::opt
       card --> tech["section.recipe-techniques.recipe-section"]:::opt
       card --> gallery["div.recipe-gallery.no-print"]:::opt
       card --> source["p.recipe-source"]:::opt

       meta --> serving["span.serving"]:::opt
       meta --> duration["span.duration"]:::opt
       meta --> diff["span.difficulty<br/>→ see Difficulty badge"]:::opt

       desc --> h2desc["h2 · Réalisation label"]
       desc --> bdesc["div.recipe-body<br/>(HTML + parsed markers)"]

       comm --> h2comm["h2 · Commentaires label"]
       comm --> bcomm["div.recipe-body<br/>(HTML + parsed markers)"]

       tech --> h2tech["h2 · Techniques label"]
       tech --> techitem["div.technique · id=tech-CODE<br/>(1 per technique, recursive order)"]

       techitem --> h3["h3 · title"]
       techitem --> tbody["div.technique-body<br/>(HTML + parsed markers)"]

Ingredients row (hero image, ingredients, equipment)
----------------------------------------------------

Rendered when the recipe has at least one ingredient **or** at least one piece
of equipment.  The row holds 1 to 3 columns, each present only if it has
content.  The hero image is the first image declared in the recipe media; when
the recipe has neither ingredients nor equipment, it is moved to the gallery.


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       block["div.recipe-ingredients-block.recipe-section"]

       block --> fig["figure.hero-item"]:::opt
       block --> sect["section.recipe-ingredients"]:::opt
       block --> eqsect["section.recipe-equipment"]:::opt

       fig --> heroimg["img.recipe-hero-img · loading=lazy"]
       fig --> preview["span.hero-preview"]
       preview --> previewimg["img (enlarged)"]

       sect --> h2["h2 · Ingrédients label"]
       sect --> table["table.ingredients-table<br/>→ see Ingredient table"]

       eqsect --> h2eq["h2 · Matériel label"]
       eqsect --> ul["ul.equipment-list"]
       ul --> li["li (1 per equipment row, recipe order)"]
       li --> eqtxt["prefix · strong (singular/plural name) · suffix"]

Ingredient table
----------------

Rendered identically whatever the other columns of the row.
The ``ing-prefix`` column is only included when at least one ingredient has a prefix.


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       table["table.ingredients-table"]
       tbody["tbody"]
       tr["tr (1 per ingredient)"]
       tdp["td.ing-prefix"]:::opt
       tdq["td.ing-qty<br/>(quantity · unit)"]
       tdr["td.ing-rest"]

       table --> tbody --> tr
       tr --> tdp
       tr --> tdq
       tr --> tdr

       tdr --> sep["text: separator"]:::opt
       tdr --> strong["strong · ingredient name"]
       tdr --> suffix["text: suffix"]:::opt

Difficulty badge (``span.difficulty``)
--------------------------------------


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       diff["span.difficulty · title=label<br/>(tooltip = label, always present)"]

       diff --> icon["span.diff-icon<br/>(if icon defined)"]:::opt
       diff --> label["span.diff-label<br/>(if label ≠ '' AND hide_label=false)"]:::opt

       icon --> img["img.diff-icon-img<br/>(src=media.php?diff=N)"]


.. note::

   ``hide_label=true``: only the icon is displayed; the label remains accessible via the
   ``title`` attribute of ``span.difficulty`` (tooltip on hover). If ``hide_label=false``, both
   label and icon are displayed.

Image gallery (``div.recipe-gallery``)
--------------------------------------

Remaining images after the hero image. Not printed (``no-print``).


.. mermaid::

   graph TD
       gallery["div.recipe-gallery.no-print"]
       fig["figure.gallery-item (1 per image)"]
       thumb["img.gallery-thumb · loading=lazy"]
       prev["span.gallery-preview"]
       previmg["img (enlarged)"]

       gallery --> fig --> thumb
       fig --> prev --> previmg

Parsed markers in ``recipe-body`` / ``technique-body``
------------------------------------------------------

``parse_markers()`` transforms three types of markers present in the rich HTML.


.. mermaid::

   graph TD
       classDef opt stroke-dasharray:5 5

       body["div.recipe-body<br/>or div.technique-body"]

       body --> recipelink["a · href=?RECIPE=CODE<br/>(from [RECIPE:CODE])"]
       body --> imgref["span.recipe-img-ref<br/>(from [IMG:CODE])"]
       body --> techlink["a.tech-link · href=#tech-CODE<br/>(from [TECH:CODE])"]
       body --> imgmiss["span.img-missing<br/>(image not found)"]:::opt

       imgref --> thumb["img.recipe-thumb · loading=lazy"]
       imgref --> imgprev["span.recipe-img-preview"]
       imgprev --> imgfull["img (enlarged)"]
