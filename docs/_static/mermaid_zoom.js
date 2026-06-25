(function () {
    'use strict';

    /* --- Build overlay DOM (once) ---------------------------------------- */

    var overlay = document.createElement('div');
    overlay.id = 'mermaid-overlay';

    var box = document.createElement('div');
    box.id = 'mermaid-overlay-box';

    /* Toolbar: − / 1:1 / + / × */
    var toolbar = document.createElement('div');
    toolbar.id = 'mermaid-overlay-toolbar';

    function makeBtn(label, title) {
        var btn = document.createElement('button');
        btn.textContent = label;
        btn.title = title;
        toolbar.appendChild(btn);
        return btn;
    }

    var btnOut   = makeBtn('−', 'Zoom arrière  (−25 %)');
    var btnReset = makeBtn('1:1', 'Taille initiale');
    var btnIn    = makeBtn('+', 'Zoom avant  (+25 %)');
    var btnClose = makeBtn('×', 'Fermer  (Échap)');
    btnClose.id = 'mermaid-overlay-close';

    overlay.appendChild(toolbar);
    overlay.appendChild(box);

    /* --- Scale state -------------------------------------------------------- */

    var vbW = 0, vbH = 0, initScale = 1, currentScale = 1;
    var activeSvg = null;

    function applyScale(scale) {
        if (!activeSvg) { return; }
        currentScale = Math.max(0.25, Math.min(scale, 16));
        activeSvg.setAttribute('width',  Math.round(vbW * currentScale));
        activeSvg.setAttribute('height', Math.round(vbH * currentScale));
    }

    btnIn.addEventListener('click',    function (e) { e.stopPropagation(); applyScale(currentScale * 1.25); });
    btnOut.addEventListener('click',   function (e) { e.stopPropagation(); applyScale(currentScale / 1.25); });
    btnReset.addEventListener('click', function (e) { e.stopPropagation(); applyScale(initScale); });

    /* --- Open / close ------------------------------------------------------ */

    function open(svg) {
        var clone = svg.cloneNode(true);

        /* Strip Mermaid's inline size constraints */
        clone.removeAttribute('style');
        clone.removeAttribute('width');
        clone.removeAttribute('height');

        /* Compute initial scale: 2.5× natural size or 85 % of viewport width,
         * whichever is larger */
        var vb = svg.viewBox && svg.viewBox.baseVal;
        vbW = vb && vb.width  > 0 ? vb.width  : svg.getBoundingClientRect().width  || 800;
        vbH = vb && vb.height > 0 ? vb.height : svg.getBoundingClientRect().height || 600;

        initScale    = Math.max(2.5, (window.innerWidth * 0.85) / vbW);
        currentScale = initScale;

        clone.setAttribute('width',  Math.round(vbW * currentScale));
        clone.setAttribute('height', Math.round(vbH * currentScale));

        activeSvg = clone;
        box.innerHTML = '';
        box.appendChild(clone);
        overlay.classList.add('visible');
        box.scrollTop  = 0;
        box.scrollLeft = 0;
    }

    function close() {
        overlay.classList.remove('visible');
        box.innerHTML = '';
        activeSvg = null;
    }

    btnClose.addEventListener('click', function (e) { e.stopPropagation(); close(); });
    overlay.addEventListener('click',  function (e) { if (e.target === overlay) { close(); } });
    document.addEventListener('keydown', function (e) {
        if (!overlay.classList.contains('visible')) { return; }
        if (e.key === 'Escape')    { close(); }
        if (e.key === '+' || e.key === '=') { applyScale(currentScale * 1.25); }
        if (e.key === '-')                  { applyScale(currentScale / 1.25); }
        if (e.key === '0')                  { applyScale(initScale); }
    });

    /* --- Attach click handler to one .mermaid wrapper --------------------- */

    function attach(wrapper) {
        if (wrapper.dataset.zoomReady) { return; }
        wrapper.dataset.zoomReady = '1';
        wrapper.addEventListener('click', function () {
            var svg = wrapper.querySelector('svg');
            if (svg) { open(svg); }
        });
    }

    /* --- Watch for Mermaid's async SVG rendering (Mermaid 10+) ------------ */

    var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            m.addedNodes.forEach(function (node) {
                if (node.nodeType !== 1) { return; }
                if (node.classList && node.classList.contains('mermaid')) { attach(node); }
                if (node.tagName === 'svg') {
                    var p = node.parentElement;
                    if (p && p.classList.contains('mermaid')) { attach(p); }
                }
                if (node.querySelectorAll) {
                    node.querySelectorAll('.mermaid').forEach(attach);
                }
            });
        });
    });

    /* --- Bootstrap --------------------------------------------------------- */

    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(overlay);
        document.querySelectorAll('.mermaid').forEach(attach);
        observer.observe(document.body, { childList: true, subtree: true });
    });
}());
