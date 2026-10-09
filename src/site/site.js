// The colour theme switch, left-handed (mirrored) diagrams, the phone menu, the folded key and the voicing filters. Every page works without this script.
(() => {
  const root = document.documentElement, KEY = "hoc-lefty";
  let lefty = false;
  try { lefty = localStorage.getItem(KEY) === "1"; } catch (e) {}
  if (lefty) root.classList.add("lefty");
  const apply = () => {
    root.classList.toggle("lefty", lefty);
    document.querySelectorAll(".lefty-toggle").forEach(b => b.setAttribute("aria-pressed", String(lefty)));
  };
  // colour theme: automatic (the system's), light or dark; the page's <head> applies a stored choice before drawing
  const TKEY = "hoc-theme", MODES = ["auto", "light", "dark"], SAYS = { auto: "automatic, as the system", light: "light", dark: "dark" };
  let mode = "auto";
  try { mode = localStorage.getItem(TKEY) || "auto"; } catch (e) {}
  if (!MODES.includes(mode)) mode = "auto";
  const setTheme = () => {
    if (mode === "auto") delete root.dataset.theme; else root.dataset.theme = mode;
    document.querySelectorAll(".theme-toggle").forEach(b => {
      const t = `Colour theme: ${SAYS[mode]}. Click for ${SAYS[MODES[(MODES.indexOf(mode) + 1) % 3]]}.`;
      b.dataset.mode = mode; b.title = t; b.setAttribute("aria-label", t);
    });
  };
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".theme-toggle").forEach(b => {
      b.hidden = false;
      b.addEventListener("click", () => {
        mode = MODES[(MODES.indexOf(mode) + 1) % 3];
        try { if (mode === "auto") localStorage.removeItem(TKEY); else localStorage.setItem(TKEY, mode); } catch (e) {}
        setTheme();
      });
    });
    setTheme();
    // the Menu button on a phone opens and closes the sections and the tools; Escape closes them
    document.querySelectorAll(".menu-btn").forEach(b => {
      const h = b.closest("header"), set = o => { h.classList.toggle("open", o); b.setAttribute("aria-expanded", String(o)); };
      b.addEventListener("click", () => set(!h.classList.contains("open")));
      document.addEventListener("keydown", e => { if (e.key === "Escape" && h.classList.contains("open")) { set(false); b.focus(); } });
    });
    // the key to the diagrams, folded behind the "?" button on a phone
    document.querySelectorAll(".key-btn").forEach(b => {
      const k = document.getElementById(b.getAttribute("aria-controls"));
      if (k) b.addEventListener("click", () => b.setAttribute("aria-expanded", String(k.classList.toggle("open"))));
    });
    // thin rules separate the menu's items; an item that wraps to a new line starts it without one
    const rules = () => document.querySelectorAll("header.top nav").forEach(row => {
      let top = null;
      for (const el of row.children) { el.classList.remove("line-start"); if (top !== null && el.offsetTop > top + 2) el.classList.add("line-start"); top = el.offsetTop; }
    });
    rules(); let pending = false;
    if (document.fonts) document.fonts.ready.then(rules);       // the web fonts change the widths once they arrive
    window.addEventListener("resize", () => { if (!pending) { pending = true; requestAnimationFrame(() => { pending = false; rules(); }); } });
    document.querySelectorAll(".lefty-toggle").forEach(b => {
      b.hidden = false;
      b.addEventListener("click", () => {
        lefty = !lefty;
        try { localStorage.setItem(KEY, lefty ? "1" : "0"); } catch (e) {}
        apply();
      });
    });
    apply();
    document.querySelectorAll(".filters").forEach(f => {
      f.hidden = false;
      const cards = f.parentElement.querySelectorAll(".vcard");
      f.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
        const k = b.dataset.filter;
        f.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
        cards.forEach(c => { c.hidden = !(k === "all" || c.dataset.kind === k || c.dataset.bass === k); });
      }));
    });
  });
})();
