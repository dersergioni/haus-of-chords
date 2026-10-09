# Audit of the built website (dist/site/): every page's head, every internal link, every diagram against the data,
# the page width at phone size (headless Chrome), colours, fonts and words that must not be published.
# Usage: python3 audit_site.py [site_dir]
import os, sys, re, html, shutil, subprocess, tempfile
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
import data
data.require_valid()
from data import parse as dparse, fstr as fstr_, fgstr
from book import PROJ, DESIGN, SITE as SITE_URL
from chords import ALL, FILE, shown, frets
from theory import NOTES, OPEN, SEMI
from build_site import SLUG, more_voicings

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "dist", "site")
P = []

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.decl = ""; self.lang = None; self.charset = False; self.viewport = False; self.title = ""
        self.links, self.ids, self.svgs = [], set(), []
        self._in_title = False; self._svg = None; self._text = None
    def handle_decl(self, decl): self.decl = decl
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.add(a["id"])
        if tag == "html": self.lang = a.get("lang")
        if tag == "meta" and (a.get("charset") or "").lower() == "utf-8": self.charset = True
        if tag == "meta" and a.get("name") == "viewport": self.viewport = True
        if tag == "title": self._in_title = True
        for k in ("href", "src"):
            if k in a: self.links.append(a[k])
        if tag == "svg" and "dg" in (a.get("class") or "").split() and a.get("data-frets"):   # a chord diagram (not a legend key)
            self._svg = dict(frets=a.get("data-frets"), fingers=a.get("data-fingers"), degrees=a.get("data-degrees"),
                             label=a.get("aria-label") or "", deg=[], fg=[])
        if tag == "text" and self._svg is not None:
            cls = (a.get("class") or "").split()
            self._text = "deg" if "deg" in cls else "fg" if "fg" in cls else None
    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        if tag == "text": self._text = None
        if tag == "svg" and self._svg is not None: self.svgs.append(self._svg); self._svg = None
    def handle_data(self, d):
        if self._in_title: self.title += d
        if self._svg is not None and self._text: self._svg[self._text].append(d.strip())

pages = {}
for root, _dirs, files in os.walk(SITE):
    for f in files:
        if f.endswith(".html"):
            path = os.path.join(root, f); p = Page(); p.feed(open(path, encoding="utf8").read()); pages[path] = p
print(f"1. pages: {len(pages)}")
# heads
for path, p in pages.items():
    rel = os.path.relpath(path, SITE)
    if p.decl.lower() != "doctype html": P.append(f"{rel}: no <!doctype html>")
    if p.lang != "en": P.append(f"{rel}: <html lang> is {p.lang!r}")
    if not p.charset: P.append(f"{rel}: no <meta charset=utf-8>")
    if not p.viewport: P.append(f"{rel}: no viewport meta")
    if not p.title.strip(): P.append(f"{rel}: no <title>")
print("   heads: doctype, lang, charset, viewport, title checked")
# links
nint = next_ = 0
for path, p in pages.items():
    for href in p.links:
        if re.match(r"^https?:", href): next_ += 1; continue
        target, _, frag = href.partition("#")
        target = target.partition("?")[0]      # a query (the icon's ?v=) names the same file
        if not target:
            if frag and frag not in p.ids: P.append(f"{os.path.relpath(path, SITE)}: anchor #{frag} missing")
            continue
        nint += 1
        base_path = urlparse(SITE_URL).path                       # the 404 page links from the site's root (/haus-of-chords/…)
        if target.startswith(base_path): dest = os.path.normpath(os.path.join(SITE, unquote(target[len(base_path):])))
        else: dest = os.path.normpath(os.path.join(os.path.dirname(path), unquote(target)))
        if target.endswith("/") or os.path.isdir(dest): dest = os.path.join(dest, "index.html")
        if not os.path.exists(dest): P.append(f"{os.path.relpath(path, SITE)}: broken link {href}")
print(f"2. links: {nint} internal links resolve, {next_} external")
# diagrams against the data
nd = 0
for q, qname, formula, about, temps in ALL:
    for r in range(12):
        path = os.path.join(SITE, "chords", SLUG[r], FILE[q], "index.html")
        p = pages.get(path)
        if p is None: P.append(f"missing page for {NOTES[r]}{q}"); continue
        book_vs = shown(r, temps)
        keys_ = {tuple(frets(t, b)) for t, b in book_vs}
        more = more_voicings(r, q, keys_)
        want = [(fstr_(frets(t, b)), fgstr(t["fing"])) for t, b in book_vs + more]
        got = [(s["frets"], s["fingers"]) for s in p.svgs]
        if got != want: P.append(f"{NOTES[r]}{q}: diagrams {got[:4]}... differ from the data {want[:4]}...")
        for s in p.svgs:
            nd += 1
            fr = dparse(s["frets"])
            degs = s["degrees"].split()
            for i, d in enumerate(degs):
                if d == "x": continue
                if (OPEN[i] + fr[i] - r) % 12 != SEMI[d]: P.append(f"{NOTES[r]}{q} {s['frets']}: string {6 - i} shows {d}, sounds {(OPEN[i] + fr[i] - r) % 12} semitones")
            if s["deg"] != [d for d in degs if d != "x"]: P.append(f"{NOTES[r]}{q} {s['frets']}: dots {s['deg']} vs degrees {degs}")
            if s["fg"] != [f for f in s["fingers"] if f != "-"]: P.append(f"{NOTES[r]}{q} {s['frets']}: finger letters {s['fg']} vs {s['fingers']}")
            if not s["label"]: P.append(f"{NOTES[r]}{q} {s['frets']}: diagram without a text alternative")
print(f"3. diagrams: {nd} on chord pages checked against the data (frets, fingers, degrees, dots, letters)")
# phone width: each page opened in a 360 px wide frame (a desktop browser window cannot be that narrow), served locally
CHROME = (os.environ.get("CHROME") or next(filter(None, map(shutil.which, ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"))), None)
          or next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",) if os.path.exists(p)), None))
sample = ["index.html", "chords/index.html", "keys/index.html", "slash-chords/index.html", "how-to-read/index.html", "about/index.html",
          f"chords/{SLUG[0]}/index.html", f"chords/{SLUG[4]}/{FILE['m7']}/index.html", f"chords/{SLUG[1]}/{FILE['13']}/index.html"]
if CHROME:
    import threading, functools, http.server
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=SITE))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    probe = os.path.join(SITE, "_width_probe.html")
    prof = tempfile.mkdtemp(prefix="hoc-audit-")              # a fresh browser profile, removed afterwards
    wide = []
    try:
        for rel in sample:
            open(probe, "w", encoding="utf8").write(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>probe</title></head><body>
    <iframe id="f" src="{rel}" style="width:360px;height:800px;border:0"></iframe>
    <script>document.getElementById("f").addEventListener("load", () => setTimeout(() => {{
      const d = document.getElementById("f").contentDocument.documentElement;
      document.body.dataset.result = d.scrollWidth + "/" + d.clientWidth; }}, 300));</script></body></html>""")
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--window-size=800,900"]
                                 + (["--no-sandbox"] if os.environ.get("CI") else []) + [      # a CI runner may not allow Chrome's sandbox
                                  "--virtual-time-budget=4000", "--dump-dom", base + "_width_probe.html"], capture_output=True, text=True, timeout=90).stdout
            m = re.search(r'data-result="(\d+)/(\d+)"', out)
            if not m: P.append(f"{rel}: the width check did not run"); continue
            sw, cw = int(m.group(1)), int(m.group(2))
            if sw > cw: wide.append(f"{rel} ({sw} px)"); P.append(f"{rel}: {sw} px wide in a {cw} px phone screen")
    finally:                                                  # also after a Chrome that hangs
        if os.path.exists(probe): os.remove(probe)
        srv.shutdown(); shutil.rmtree(prof, ignore_errors=True)
    print(f"4. phone width (360 px frame, headless Chrome): {len(sample)} pages, too wide: {wide or 'none'}")
else:
    print("4. phone width: skipped (no Chrome or Chromium found; set CHROME to its path)")
    if os.environ.get("CI"): P.append("no Chrome on the build machine: the phone-width check could not run")
# colours (src/design.toml): WCAG contrast of text, and degrees that a black-and-white print can tell apart
def _lum(h):
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)); return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
def _cr(a, b):
    x, y = sorted((_lum(a), _lum(b)), reverse=True); return (x + 0.05) / (y + 0.05)
def _lstar(h):
    y = _lum(h); return 116 * (y ** (1 / 3) if y > 0.008856 else 7.787 * y + 16 / 116) - 16
ncol = 0
for theme in ("colors", "dark"):
    c = DESIGN[theme]
    pairs = [(c[f], c[b], f"{f} on {b}") for f, b in (("ink", "bg"), ("muted", "bg"), ("link", "bg"), ("ink", "paper"), ("muted", "paper"))]
    pairs += [(ink, fill, f"{d} label") for d, (fill, ink) in c["degrees"].items()]
    for fg, bg, what in pairs:
        ncol += 1
        if _cr(fg, bg) < 4.5: P.append(f"{theme}: {what} contrast {_cr(fg, bg):.2f} < 4.5")
fills = {d: _lstar(v[0]) for d, v in DESIGN["colors"]["degrees"].items()}   # in black and white: the root darkest, the fifth lightest, the rest one grey
# seven colours cannot all differ in black-and-white print; there the digit in every dot tells the degrees apart, so this is shown, not required
print(f"5. colours: {ncol} text contrasts (WCAG 4.5) in both themes; filled degree circles in greyscale L* {', '.join(f'{k} {v:.0f}' for k, v in fills.items())}")
# words that must never be published, listed in the local file .audit-forbidden: every text file of the site and its downloads
_fb = os.path.join(PROJ, ".audit-forbidden")
words = [w.strip() for w in open(_fb, encoding="utf8") if w.strip()] if os.path.exists(_fb) else []
words += [w.strip() for w in os.environ.get("AUDIT_FORBIDDEN", "").split(",") if w.strip()]   # on GitHub: a repository secret
cut = lambda w: (w[:2] if len(w) > 4 else w[:1]) + "…"          # cut short: a CI log is public
nfiles = 0
for root, _dirs, files in os.walk(SITE):
    for f in files:
        if not f.endswith((".html", ".css", ".js", ".toml", ".md", ".json", ".chordpro", ".txt", ".svg")): continue
        nfiles += 1
        text = open(os.path.join(root, f), encoding="utf8", errors="replace").read().lower()
        for w in words:
            if w.lower() in text: P.append(f"{os.path.relpath(os.path.join(root, f), SITE)}: contains a forbidden word ({cut(w)})")
        if f.endswith(".html") and "thumb" in text: P.append(f"{os.path.relpath(os.path.join(root, f), SITE)}: says \"thumb\" (fingers are I M R L; the data files may quote it)")
print(f"6. forbidden words: {len(words)} checked in {nfiles} text files, and \"thumb\" in the pages")
# fonts: every character a page shows is in the subset web fonts (else a system font would stand in)
css = open(os.path.join(SITE, "assets", "site.css"), encoding="utf8").read()
cover = set()
for ranges in re.findall(r"unicode-range: ([^;}]+)", css):
    for r in ranges.split(","):
        lo, _, hi = r.strip().replace("U+", "").partition("-"); cover |= set(range(int(lo, 16), int(hi or lo, 16) + 1))
missing = {}
for path in pages:
    doc = open(path, encoding="utf8").read()
    shown_text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style|title|head)[\s\S]*?</\1>", " ", doc)))
    for ch in set(shown_text):
        if not ch.isspace() and ord(ch) not in cover: missing.setdefault(ch, os.path.relpath(path, SITE))
P += [f"{p}: '{ch}' (U+{ord(ch):04X}) is not in the web fonts" for ch, p in missing.items()]
print(f"7. fonts: every character shown on {len(pages)} pages is in the subset fonts" + (f", except {sorted(missing)}" if missing else ""))
print("\nPROBLEMS:", len(P)); print("\n".join(P[:40]))
raise SystemExit(1 if P else 0)          # a problem fails the build: make audit, and the publishing workflow
