/* Isaiah study diagrams — click-to-enlarge lightbox with zoom + pan.
   Progressive enhancement: figures still read fine with JS off. */
(function () {
  "use strict";
  var figs = document.querySelectorAll(".izfig");
  if (!figs.length || !document.body) return;

  var lb, stage, hold, capEl;
  var scale = 1, minScale = 1, tx = 0, ty = 0;
  var dragging = false, sx = 0, sy = 0, moved = false, activePointer = null;

  var EXPAND = '<svg viewBox="0 0 24 24" aria-hidden="true">' +
    '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>';

  function capText(fig) {
    var t = fig.querySelector("svg title");
    return t ? t.textContent.trim() : "Diagram";
  }

  function apply() {
    hold.style.transform = "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
  }

  function clamp() {
    // keep at least a sliver of the figure on screen
    var st = stage.getBoundingClientRect();
    var w = hold.offsetWidth * scale, h = hold.offsetHeight * scale;
    var m = 80;
    tx = Math.min(st.width - m, Math.max(m - w, tx));
    ty = Math.min(st.height - m, Math.max(m - h, ty));
  }

  function zoomAt(factor, cx, cy) {
    var ns = Math.min(8, Math.max(minScale, scale * factor));
    factor = ns / scale;
    tx = cx - (cx - tx) * factor;
    ty = cy - (cy - ty) * factor;
    scale = ns;
    clamp();
    apply();
  }

  function centerFit() {
    hold.style.transform = "none";
    var st = stage.getBoundingClientRect();
    var w0 = hold.offsetWidth, h0 = hold.offsetHeight;
    var fit = Math.min((st.width - 32) / w0, (st.height - 32) / h0, 1);
    if (!isFinite(fit) || fit <= 0) fit = 1;
    minScale = fit;
    scale = fit;
    tx = (st.width - w0 * fit) / 2;
    ty = (st.height - h0 * fit) / 2;
    apply();
  }

  function build() {
    lb = document.createElement("div");
    lb.className = "izlb";
    lb.hidden = true;
    lb.setAttribute("role", "dialog");
    lb.setAttribute("aria-modal", "true");
    lb.setAttribute("aria-label", "Enlarged diagram");
    lb.innerHTML =
      '<div class="izlb-bar">' +
        '<span class="izlb-cap"></span>' +
        '<button class="izlb-btn" type="button" data-a="out" aria-label="Zoom out">−</button>' +
        '<button class="izlb-btn" type="button" data-a="in" aria-label="Zoom in">+</button>' +
        '<button class="izlb-btn" type="button" data-a="reset">Reset</button>' +
        '<button class="izlb-btn" type="button" data-a="close" aria-label="Close">Close ×</button>' +
      '</div>' +
      '<div class="izlb-stage"><div class="izlb-hold"></div></div>';
    document.body.appendChild(lb);
    stage = lb.querySelector(".izlb-stage");
    hold = lb.querySelector(".izlb-hold");
    capEl = lb.querySelector(".izlb-cap");

    lb.addEventListener("click", function (e) {
      var a = e.target.closest("[data-a]");
      if (a) {
        var k = a.getAttribute("data-a");
        if (k === "close") close();
        else if (k === "in") zoomAt(1.3, stage.clientWidth / 2, stage.clientHeight / 2);
        else if (k === "out") zoomAt(1 / 1.3, stage.clientWidth / 2, stage.clientHeight / 2);
        else if (k === "reset") centerFit();
        return;
      }
      if (e.target === stage && !moved) close();
    });

    stage.addEventListener("wheel", function (e) {
      e.preventDefault();
      var r = stage.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });

    stage.addEventListener("pointerdown", function (e) {
      dragging = true; moved = false; activePointer = e.pointerId;
      sx = e.clientX; sy = e.clientY;
      stage.classList.add("dragging");
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener("pointermove", function (e) {
      if (!dragging || e.pointerId !== activePointer) return;
      var dx = e.clientX - sx, dy = e.clientY - sy;
      if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
      sx = e.clientX; sy = e.clientY;
      tx += dx; ty += dy; clamp(); apply();
    });
    function endDrag(e) {
      if (e.pointerId !== activePointer) return;
      dragging = false; activePointer = null;
      stage.classList.remove("dragging");
    }
    stage.addEventListener("pointerup", endDrag);
    stage.addEventListener("pointercancel", endDrag);

    document.addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "Escape") close();
      else if (e.key === "+" || e.key === "=") zoomAt(1.3, stage.clientWidth / 2, stage.clientHeight / 2);
      else if (e.key === "-") zoomAt(1 / 1.3, stage.clientWidth / 2, stage.clientHeight / 2);
      else if (e.key === "0") centerFit();
    });
  }

  var lastFocus = null;
  function open(fig) {
    if (!lb) build();
    var svg = fig.querySelector('svg[role="img"]');
    if (!svg) return;
    lastFocus = document.activeElement;
    var clone = svg.cloneNode(true);
    clone.removeAttribute("style");
    hold.innerHTML = "";
    hold.appendChild(clone);
    capEl.textContent = capText(fig);
    lb.hidden = false;
    document.documentElement.style.overflow = "hidden";
    // measure after layout
    requestAnimationFrame(function () {
      centerFit();
      var cb = lb.querySelector('[data-a="close"]');
      if (cb) cb.focus();
    });
  }

  function close() {
    if (!lb || lb.hidden) return;
    lb.hidden = true;
    hold.innerHTML = "";
    document.documentElement.style.overflow = "";
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  Array.prototype.forEach.call(figs, function (fig) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "izfig-zoom";
    btn.setAttribute("aria-label", "Enlarge diagram");
    btn.innerHTML = EXPAND + "Enlarge";
    fig.appendChild(btn);
    // whole figure is clickable; the button's activation bubbles here too
    fig.addEventListener("click", function () { open(fig); });
  });
})();
