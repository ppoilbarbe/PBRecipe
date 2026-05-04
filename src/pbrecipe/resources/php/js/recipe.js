/* PBRecipe — minimal JS for interactive behaviours */

// Ensure all <details> category blocks start open (already set in PHP via `open`,
// but keep this for any dynamically inserted content).
document.querySelectorAll('details.category-block').forEach(el => {
  el.open = true;
});

// ── Images manquantes ─────────────────────────────────────────────────────────
// Si l'image héros ne se charge pas, on démonte le bloc flex :
// la section ingrédients remplace le bloc et reçoit la classe recipe-section,
// de sorte qu'aucun espace n'est réservé à gauche des ingrédients.
document.querySelectorAll('.recipe-hero-img').forEach(img => {
  const fix = () => {
    const block = img.closest('.recipe-ingredients-block');
    if (!block) { img.style.display = 'none'; return; }
    const section = block.querySelector('.recipe-ingredients');
    if (section) {
      section.classList.add('recipe-section');
      block.replaceWith(section);
    } else {
      block.remove();
    }
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
