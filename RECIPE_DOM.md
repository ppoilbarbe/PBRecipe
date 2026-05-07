# DOM — Fiche recette (`?RECIPE=CODE`)

Structure HTML produite par `render_recipe()` dans `lib/display.php`.
Les éléments en pointillés sont conditionnels (absents si la donnée est vide).

---

## Structure générale

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    article["article.recipe"]

    article --> h1["h1.recipe-title"]
    article --> cats["p.recipe-categories\n(noms séparés par virgules)"]:::opt
    article --> card["div.recipe-card"]

    card --> meta["div.recipe-meta"]:::opt
    card --> ingblock["div.recipe-ingredients-block.recipe-section\n(avec image héro — voir détail)"]:::opt
    card --> ingsect["section.recipe-ingredients.recipe-section\n(sans image héro — voir détail)"]:::opt
    card --> desc["section.recipe-description.recipe-section"]:::opt
    card --> comm["section.recipe-comments.recipe-section"]:::opt
    card --> tech["section.recipe-techniques.recipe-section"]:::opt
    card --> gallery["div.recipe-gallery.no-print"]:::opt
    card --> source["p.recipe-source"]:::opt

    meta --> serving["span.serving"]:::opt
    meta --> duration["span.duration"]:::opt
    meta --> diff["span.difficulty\n→ voir Badge difficulté"]:::opt

    desc --> h2desc["h2 · label Réalisation"]
    desc --> bdesc["div.recipe-body\n(HTML + marqueurs parsés)"]

    comm --> h2comm["h2 · label Commentaires"]
    comm --> bcomm["div.recipe-body\n(HTML + marqueurs parsés)"]

    tech --> h2tech["h2 · label Techniques"]
    tech --> techitem["div.technique · id=tech-CODE\n(1 par technique, ordre récursif)"]

    techitem --> h3["h3 · titre"]
    techitem --> tbody["div.technique-body\n(HTML + marqueurs parsés)"]
```

---

## Bloc ingrédients avec image héro

Rendu quand la recette a au moins un ingrédient **et** au moins une image.
L'image héro est la première image déclarée dans les médias de la recette.

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    block["div.recipe-ingredients-block.recipe-section"]

    block --> fig["figure.hero-item"]
    block --> sect["section.recipe-ingredients"]

    fig --> heroimg["img.recipe-hero-img · loading=lazy"]
    fig --> preview["span.hero-preview"]
    preview --> previewimg["img (agrandissement)"]

    sect --> h2["h2 · label Ingrédients"]
    sect --> table["table.ingredients-table\n→ voir Tableau des ingrédients"]
```

---

## Tableau des ingrédients

Rendu identiquement que l'image héro soit présente ou non.
La colonne `ing-prefix` n'est incluse que si au moins un ingrédient porte un préfixe.

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    table["table.ingredients-table"]
    tbody["tbody"]
    tr["tr (1 par ingrédient)"]
    tdp["td.ing-prefix"]:::opt
    tdq["td.ing-qty\n(quantité · unité)"]
    tdr["td.ing-rest"]

    table --> tbody --> tr
    tr --> tdp
    tr --> tdq
    tr --> tdr

    tdr --> sep["texte : séparateur"]:::opt
    tdr --> strong["strong · nom de l'ingrédient"]
    tdr --> suffix["texte : suffixe"]:::opt
```

---

## Badge difficulté (`span.difficulty`)

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    diff["span.difficulty · title=label"]

    diff --> icon["span.diff-icon"]:::opt
    diff --> label["span.diff-label"]:::opt

    icon --> img["img.diff-icon-img\n(src=lib/media.php?diff=N)"]
```

---

## Galerie d'images (`div.recipe-gallery`)

Images restantes après l'image héro. Non imprimée (`no-print`).

```mermaid
graph TD
    gallery["div.recipe-gallery.no-print"]
    fig["figure.gallery-item (1 par image)"]
    thumb["img.gallery-thumb · loading=lazy"]
    prev["span.gallery-preview"]
    previmg["img (agrandissement)"]

    gallery --> fig --> thumb
    fig --> prev --> previmg
```

---

## Marqueurs parsés dans `recipe-body` / `technique-body`

`parse_markers()` transforme trois types de marqueurs présents dans le HTML riche.

```mermaid
graph TD
    classDef opt stroke-dasharray:5 5

    body["div.recipe-body\nou div.technique-body"]

    body --> recipelink["a · href=?RECIPE=CODE\n(issu de [RECIPE:CODE])"]
    body --> imgref["span.recipe-img-ref\n(issu de [IMG:CODE])"]
    body --> techlink["a.tech-link · href=#tech-CODE\n(issu de [TECH:CODE])"]
    body --> imgmiss["span.img-missing\n(image introuvable)"]:::opt

    imgref --> thumb["img.recipe-thumb · loading=lazy"]
    imgref --> imgprev["span.recipe-img-preview"]
    imgprev --> imgfull["img (agrandissement)"]
```
