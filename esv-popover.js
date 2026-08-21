/* ESV scripture popovers (Commonplace).
 * Wraps bare Scripture references in page bodies and, on hover/tap, shows the
 * ESV text fetched from the /api/esv proxy (which holds the Crossway key).
 * Progressive enhancement: if anything fails, references stay as plain text.
 * Blockquoted verses (printed exhibits) are left untouched. */
(function () {
  "use strict";
  var BOOKS = [
    "Genesis","Gen","Exodus","Exod","Ex","Leviticus","Lev","Numbers","Num","Deuteronomy","Deut",
    "Joshua","Josh","Judges","Judg","Ruth","1 Samuel","1 Sam","2 Samuel","2 Sam","1 Kings","1 Kgs",
    "2 Kings","2 Kgs","1 Chronicles","1 Chr","2 Chronicles","2 Chr","Ezra","Nehemiah","Neh","Esther","Esth",
    "Job","Psalms","Psalm","Pss","Ps","Proverbs","Prov","Ecclesiastes","Eccl","Song of Solomon","Song",
    "Isaiah","Isa","Jeremiah","Jer","Lamentations","Lam","Ezekiel","Ezek","Daniel","Dan","Hosea","Hos",
    "Joel","Amos","Obadiah","Obad","Jonah","Micah","Mic","Nahum","Nah","Habakkuk","Hab","Zephaniah","Zeph",
    "Haggai","Hag","Zechariah","Zech","Malachi","Mal","Matthew","Matt","Mt","Mark","Mk","Luke","Lk",
    "John","Jn","Acts","Romans","Rom","1 Corinthians","1 Cor","2 Corinthians","2 Cor","Galatians","Gal",
    "Ephesians","Eph","Philippians","Phil","Colossians","Col","1 Thessalonians","1 Thess","2 Thessalonians",
    "2 Thess","1 Timothy","1 Tim","2 Timothy","2 Tim","Titus","Philemon","Phlm","Hebrews","Heb","James","Jas",
    "1 Peter","1 Pet","2 Peter","2 Pet","1 John","2 John","3 John","Jude","Revelation","Rev"
  ];
  // longest first so "Song of Solomon" beats "Song", "1 Corinthians" beats no-match
  BOOKS.sort(function (a, b) { return b.length - a.length; });
  var bookAlt = BOOKS.map(function (b) { return b.replace(/ /g, "\\s?").replace(/\./g, "\\.?"); }).join("|");
  var REF = new RegExp(
    "\\b(" + bookAlt + ")\\.?\\s+\\d+(?::\\d+[a-b]?)?" +
    "(?:\\s*[\\u2013\\u2014-]\\s*\\d+(?::\\d+)?|\\s*[,;]\\s*\\d+(?::\\d+)?)*", "g");

  var SKIP = { A: 1, BLOCKQUOTE: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, CODE: 1, PRE: 1, BUTTON: 1 };
  var CONTAINERS = ".content, .body, .prose";

  function inSkip(node) {
    for (var p = node.parentNode; p && p.nodeType === 1; p = p.parentNode) {
      if (SKIP[p.tagName] || (p.className && /esvref|esv-pop/.test(p.className))) return true;
    }
    return false;
  }

  function wrap(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var nodes = [], n;
    while ((n = walker.nextNode())) { if (n.nodeValue.length > 3 && !inSkip(n)) nodes.push(n); }
    nodes.forEach(function (node) {
      var text = node.nodeValue; REF.lastIndex = 0;
      if (!REF.test(text)) return;
      REF.lastIndex = 0;
      var frag = document.createDocumentFragment(), last = 0, m;
      while ((m = REF.exec(text))) {
        frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var span = document.createElement("span");
        span.className = "esvref"; span.setAttribute("data-ref", m[0].replace(/[\s ]+/g, " ").trim());
        span.textContent = m[0];
        frag.appendChild(span); last = m.index + m[0].length;
      }
      frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });
  }

  var cache = {}, pop, hideT;
  function popover() {
    if (pop) return pop;
    pop = document.createElement("div"); pop.className = "esv-pop"; pop.style.display = "none";
    pop.addEventListener("mouseenter", function () { clearTimeout(hideT); });
    pop.addEventListener("mouseleave", scheduleHide);
    document.body.appendChild(pop); return pop;
  }
  function scheduleHide() { hideT = setTimeout(function () { if (pop) pop.style.display = "none"; }, 180); }

  function show(ref, target) {
    clearTimeout(hideT);
    var p = popover();
    function render(body) {
      p.innerHTML = '<div class="esv-body">' + body + '</div><div class="esv-cite">ESV</div>';
      p.style.display = "block";
      var r = target.getBoundingClientRect(), pw = Math.min(360, window.innerWidth - 24);
      p.style.width = pw + "px";
      var left = Math.max(12, Math.min(r.left, window.innerWidth - pw - 12));
      var top = r.bottom + window.scrollY + 8;
      p.style.left = left + "px"; p.style.top = top + "px";
    }
    if (cache[ref]) { render(cache[ref]); return; }
    render("<em>Loading…</em>");
    fetch("/api/esv?ref=" + encodeURIComponent(ref)).then(function (r) { return r.json(); })
      .then(function (d) { var h = d && d.html ? d.html : "<em>—</em>"; cache[ref] = h; render(h); })
      .catch(function () { cache[ref] = "<em>Unavailable</em>"; render(cache[ref]); });
  }

  function init() {
    document.querySelectorAll(CONTAINERS).forEach(wrap);
    var css = document.createElement("style");
    css.textContent =
      ".esvref{border-bottom:1px dotted currentColor;cursor:help}" +
      ".esv-pop{position:absolute;z-index:9999;background:#fffdf9;color:#201e1d;border:1px solid #d7d3d3;" +
      "border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.18);padding:12px 14px 8px;font-family:'Source Serif 4',Georgia,serif;" +
      "font-size:.94rem;line-height:1.5;max-height:340px;overflow:auto}" +
      ".esv-pop .esv-body p{margin:0 0 .5em}.esv-pop .verse-num,.esv-pop b{font-weight:600;color:#7d7979;font-size:.8em;vertical-align:super}" +
      ".esv-pop .esv-cite{margin-top:6px;font-family:'Architects Daughter',cursive;font-size:.8rem;color:#9b9797;text-align:right}";
    document.head.appendChild(css);
    document.addEventListener("mouseover", function (e) {
      if (e.target && e.target.classList && e.target.classList.contains("esvref"))
        show(e.target.getAttribute("data-ref"), e.target);
    });
    document.addEventListener("mouseout", function (e) {
      if (e.target && e.target.classList && e.target.classList.contains("esvref")) scheduleHide();
    });
    document.addEventListener("click", function (e) {
      if (e.target && e.target.classList && e.target.classList.contains("esvref")) {
        e.preventDefault(); show(e.target.getAttribute("data-ref"), e.target);
      } else if (pop && !pop.contains(e.target)) { pop.style.display = "none"; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
