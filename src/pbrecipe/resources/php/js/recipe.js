/* PBRecipe — minimal JS for interactive behaviours */

// ── Tom Select — filtres de recherche multi-sélection ─────────────────────────
['ts-cat', 'ts-ing', 'ts-eq', 'ts-diff', 'ts-src'].forEach(function(id) {
  var el = document.getElementById(id);
  if (el && typeof TomSelect !== 'undefined') {
    new TomSelect(el, {
      plugins: ['remove_button'],
      maxOptions: null,
      placeholder: el.dataset.placeholder || '',
    });
  }
});

// Ensure all <details> category blocks start open (already set in PHP via `open`,
// but keep this for any dynamically inserted content).
document.querySelectorAll('details.category-block').forEach(el => {
  el.open = true;
});

// ── Images manquantes ─────────────────────────────────────────────────────────
// Si l'image héros ne se charge pas, on retire sa colonne du bloc flex :
// ingrédients et matériel récupèrent alors toute la largeur.
document.querySelectorAll('.recipe-hero-img').forEach(img => {
  const fix = () => {
    const figure = img.closest('.hero-item');
    if (figure) figure.remove();
    else img.style.display = 'none';
  };
  if (img.complete && img.naturalWidth === 0) fix();
  else img.addEventListener('error', fix);
});

// Si une vignette de galerie ne se charge pas, on supprime son gallery-item.
// Si la galerie est alors vide, on la supprime également.
document.querySelectorAll('.gallery-item').forEach(item => {
  const img = item.querySelector('.gallery-thumb');
  if (!img) return;
  const remove = () => {
    item.remove();
    const gallery = document.querySelector('.recipe-gallery');
    if (gallery && gallery.querySelector('.gallery-item') === null)
      gallery.remove();
  };
  if (img.complete && img.naturalWidth === 0) remove();
  else img.addEventListener('error', remove);
});
