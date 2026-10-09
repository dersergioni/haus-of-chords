# Builds the website (dist/site/) from the same data as the book: a page for every chord with every published voicing
# and its sources, a page per root, the keys, the slash chords, how to read the diagrams and how the book was checked.
# Static HTML that works without JavaScript; site.js adds the colour theme switch, the left-handed view and the filters. Usage: python3 build_site.py [out_dir]
import os, sys, re, shutil, html, json, math, hashlib
from urllib.parse import urlparse
import data
data.require_valid()                 # before anything is made from the data
import evidence
from data import fstr, fgstr
from book import TITLE, SUBTITLE, WORDMARK, SITE, font_metrics, SLUG as BOOK_SLUG, VERSION, DATE, AUTHOR, GITHUB, REPO, PDF_NAME, HERE, PROJ, DESIGN, font_path, provenance, SP, RH, R, OPEN_DY, LABEL_K
from chords import GROUPS, GROUP_SHORT, ALL, EVERY, FILE, SLASH_CHORDS, FIRST_TWELVE, voicings, shown, frets, tag, position, find, caged
from theory import NOTES, GROUP, KEY_LABELS, DEG_NAME, spell, other_name, both_names, KEYS, NUMERALS, MINOR_KEYS, MINOR_NUMERALS, key_chords

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "dist", "site")
SLUG = ["c", "c-sharp", "d", "e-flat", "e", "f", "f-sharp", "g", "a-flat", "a", "b-flat", "b"]
FINGER = {"I":"index","M":"middle","R":"ring","L":"little"}
esc = lambda s: html.escape(str(s), quote=True)
CUR = ' aria-current="page"'                      # marks the current page in a menu or picker

def chord_url(r, q): return f"chords/{SLUG[r]}/{FILE[q]}/"
def root_url(r): return f"chords/{SLUG[r]}/"

# ---------- diagrams (same geometry and colours as the book)
def dot(x, y, deg, r=R, lk=LABEL_K):
    k = GROUP[deg]; fs = r * (lk[1] if len(deg) > 1 else lk[0])
    if k == "d1": shape = f'<rect class="d1" x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" rx="{r * .28:.2f}"/>'
    else: shape = f'<circle class="{k}" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'
    return shape + f'<text class="deg {k}t" x="{x:.1f}" y="{y + fs * .36:.1f}" font-size="{fs:.2f}" text-anchor="middle">{esc(deg)}</text>'

def describe(name, t, base):
    """The text alternative of a diagram: the chord, its shape and position, then every string."""
    return f"{name}, {tag(t)}, {position(t, base)}: " + strings_text(t, base)

def strings_text(t, base):
    """Every string from the 6th, with its fret, degree and finger."""
    fr, fg = frets(t, base), t["fing"]
    parts = []
    for i, v in enumerate(t["n"]):
        s = {0: "6th string", 1: "5th string", 2: "4th string", 3: "3rd string", 4: "2nd string", 5: "1st string"}[i]
        if v is None: parts.append(f"{s} not played"); continue
        where = "open" if fr[i] == 0 else f"fret {fr[i]}"
        parts.append(f"{s} {where}, {DEG_NAME[v[1]]}" + (f", {FINGER[fg[i]]} finger" if fg[i] else ""))
    return "; ".join(parts)

def diagram(t, base, label=None):
    offs = [v[0] for v in t["n"] if v]
    rows = max(4, max(offs) + (1 if base > 0 else 0))
    x0, top = 20, 18; bottom = top + rows * RH; w = x0 + 5 * SP + x0; h = bottom + 14   # the same margin on both sides: the grid sits in the middle, the fret number in the left margin
    xs = [x0 + i * SP for i in range(6)]
    row_y = lambda o: top + ((o + 1 if base > 0 else o) - .5) * RH
    fr, fg = frets(t, base), t["fing"]
    alt = f'role="img" aria-label="{esc(label)}"' if label else 'aria-hidden="true"'      # without a label: the link around it names it
    s = [f'<svg class="dg" viewBox="0 0 {w} {h}" {alt} data-frets="{esc(fstr(fr))}" '
         f'data-fingers="{esc(fgstr(fg))}" data-degrees="{esc(" ".join(v[1] if v else "x" for v in t["n"]))}">']
    s += [f'<line class="str" x1="{x}" y1="{top}" x2="{x}" y2="{bottom}"/>' for x in xs]
    s += [f'<line class="fret" x1="{xs[0]}" y1="{top + k * RH}" x2="{xs[5]}" y2="{top + k * RH}"/>' for k in range(1, rows + 1)]
    if base > 0: s.append(f'<text class="fn" x="{xs[0] - R - 2.5}" y="{top + RH / 2 + 2.5}" text-anchor="end">{base}</text>')
    s += [f'<rect class="barre" x="{xs[a] - R - 1.2}" y="{row_y(o) - R - 1.2}" width="{xs[z] - xs[a] + 2 * R + 2.4}" height="{2 * R + 2.4}" rx="{R + 1.2}"/>'
          for a, z, o in t["bars"]]                # a finger lying flat
    s.append(f'<line class="{"nut" if base <= 1 else "top"}" x1="{xs[0] - .5}" y1="{top}" x2="{xs[5] + .5}" y2="{top}"/>')
    oy = top - OPEN_DY
    for i, v in enumerate(t["n"]):
        if v is None: s.append(f'<text class="mute" x="{xs[i]}" y="{oy + 2.8}" text-anchor="middle">×</text>'); continue
        s.append(dot(xs[i], oy if base == 0 and v[0] == 0 else row_y(v[0]), v[1]))
    s += [f'<text class="fg" x="{xs[i]}" y="{bottom + 10}" text-anchor="middle">{f}</text>' for i, f in enumerate(fg) if f]
    return "".join(s) + "</svg>"

# ---------- sources of a voicing
def same_page(u):
    """A URL without its scheme, www. and trailing slash: two citations of one page compare equal."""
    return re.sub(r"^https?://(www\.)?", "", u).rstrip("/").lower()

def sources_html(q, t, base):
    fr, fg = frets(t, base), t["fing"]
    v, f, cites = evidence.support(q, fr, fg)
    by = {}
    for c, cl in zip(cites, evidence.assign(cites)): by.setdefault(cl, []).append(c)
    items = []
    for cl in sorted(by, key=lambda c: (not evidence.confirms(c), evidence.names({c})[0].lower())):
        groups = {}                                   # the same publisher and chord name on several pages: one entry, the pages numbered
        for c in by[cl][:3]:
            what = c.get("chord") or ""
            if re.search(r"\.(png|jpe?g|svg|gif|webp)$", what, re.I): what = ""
            urls = groups.setdefault((data.SOURCES[c["by"]]["name"], what), [])
            if same_page(c["url"]) not in map(same_page, urls): urls.append(c["url"])      # two charts on one page: one link
        links = []
        for (who, what), urls in groups.items():
            more = ", ".join(f'<a href="{esc(u)}" rel="noopener" aria-label="{esc(who)}, page {k}">page&nbsp;{k}</a>' for k, u in enumerate(urls[1:], 2))
            links.append(f'<a href="{esc(urls[0])}" rel="noopener">{esc(who)}</a>' + (f' <span class="muted">{esc(what)}</span>' if what else "") + (f" ({more})" if more else ""))
        note = "" if evidence.confirms(cl) else ' <span class="muted">(cited, not counted)</span>'
        items.append(f"<li>{' · '.join(links)}{note}</li>")
    word = "source" if len(v) == 1 else "sources"
    fing = f'<p class="muted">The fingering shown is given by {len(f)} of them.</p>' if f else ""
    return f'<details class="src"><summary>{len(v)} {word}</summary>{fing}<ul>{"".join(items)}</ul></details>'

def kind_of(t, base):
    """What the voicing filters on a chord page sort by: open, barre or neither; the string of the bass (6, 5 or 4)."""
    fr = frets(t, base)
    return ("open" if 0 in fr else "barre" if t["bar"] else "closed"), str(6 - next(i for i in range(6) if fr[i] is not None))

def card(q, name, t, base):
    kind, bass = kind_of(t, base)
    long = len(tag(t)) + len(position(t, base)) > 28          # "E shape, 4 strings barre, fret 10": smaller, on one line
    nb = lambda x: esc(x).replace(" ", "&nbsp;")                    # the label breaks only between the shape and the position
    label = f'<div class="vlabel{" long" if long else ""}"><b>{nb(tag(t))}</b> <span>{nb(position(t, base))}</span></div>'
    return (f'<figure class="vcard" data-kind="{kind}" data-bass="{bass}">{label}{diagram(t, base, describe(name, t, base))}'
            f'<figcaption>{sources_html(q, t, base)}</figcaption></figure>')

# ---------- page frame
NAV = [("", "Home"), ("chords/", "All chords"), ("keys/", "Keys"), ("slash-chords/", "Slash chords"), ("how-to-read/", "How to read"), ("about/", "How it was checked")]
def url_text(u):
    """An address as link text that breaks only after a slash, never inside "haus-of-chords"."""
    return "/<wbr>".join(f'<span class="nw">{esc(part)}</span>' for part in u.split("/"))

def logo(style=""):
    """The logo, 32 × 32: root, third and fifth across the middle of a 3 × 3 grid. The site's CSS colours it; the browser
    tab's icon carries its own colours in `style`."""
    grid = "".join(f"M{v} 2.5v27M2.5 {v}h27" for v in (2.5, 11.5, 20.5, 29.5))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="logo" aria-hidden="true">{style}'
            f'<path class="lg" fill="none" stroke-width="1" d="{grid}"/><rect class="l1" x="3.7" y="12.7" width="6.6" height="6.6" rx="0.92"/>'
            f'<circle class="l3" cx="16" cy="16" r="3.3"/><circle class="l5" cx="25" cy="16" r="3.3"/></svg>')

_rays = "".join(f"M{9 + 5.6 * c:.2f} {9 + 5.6 * s:.2f}L{9 + 7.6 * c:.2f} {9 + 7.6 * s:.2f}" for c, s in
                ((math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)) for k in range(8)))
THEME_ICONS = ('<svg class="i-auto" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="6.6" fill="none" stroke="currentColor" stroke-width="1.6"/>'
               '<path d="M9 2.4a6.6 6.6 0 0 0 0 13.2z" fill="currentColor"/></svg>'
               f'<svg class="i-light" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="3.4" fill="currentColor"/>'
               f'<path d="{_rays}" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'
               '<svg class="i-dark" viewBox="0 0 18 18" aria-hidden="true"><path d="M8.22 2.55A6.5 6.5 0 1 0 15.29 10.63A5.4 5.4 0 0 1 8.22 2.55z" fill="currentColor"/></svg>')
def icon_svg():
    """The browser tab's icon: the logo with its own colours, light and dark as the system."""
    st = lambda c: f".lg{{stroke:{c['logo_grid']}}}.l1{{fill:{c['degrees']['d1'][0]}}}.l3{{fill:{c['degrees']['d3'][0]}}}.l5{{fill:{c['degrees']['d5'][0]}}}"
    return logo(f"<style>{st(DESIGN['colors'])}@media (prefers-color-scheme: dark){{{st(DESIGN['dark'])}}}</style>")
V = {}                               # a hash of each asset, in its URL, so a changed file is never taken from a browser's cache (filled by assets())
# the chosen theme is set before the page is drawn, so a forced light or dark page never flashes in the other one
THEME_EARLY = ('<script>var e=document.documentElement;e.classList.add("js");try{var t=localStorage.getItem("hoc-theme");if(t==="light"||t==="dark")e.dataset.theme=t;'
               'if(localStorage.getItem("hoc-lefty")==="1")e.classList.add("lefty")}catch(x){}</script>')   # and the left-handed view; "js": the phone menu folds
WRITTEN = []                         # the pages written, for the sitemap

def page(path, title, body, desc, here=None, file=None, pre=None):
    """A page of the site at path/index.html (or at `file`, with `pre` as the way back to the root: the 404 page, which
    GitHub Pages serves at any depth)."""
    pre = pre if pre is not None else "../" * (len(path.split("/")) if path else 0)
    url = SITE + (path + "/" if path else "")
    share = (f'<meta property="og:image" content="{SITE}assets/share.png?v={V["share.png"]}">\n<meta property="og:image:width" content="1200">'
             f'<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n') if "share.png" in V else ""
    head = (f'<link rel="canonical" href="{url}">\n<meta property="og:url" content="{url}">\n' if file is None else '<meta name="robots" content="noindex">\n') + share
    fonts = "".join(f'<link rel="preload" href="{pre}assets/fonts/{f}?v={V[f"fonts/{f}"]}" as="font" type="font/woff2" crossorigin>\n'
                    for f in ("text-regular.woff2", "text-bold.woff2") if f"fonts/{f}" in V)
    nav = "".join(f'<a href="{pre}{u}"{CUR if u == here else ""}>{esc(t)}</a>' for u, t in NAV)
    built = f' · built from <a href="{esc(GITHUB)}">{url_text(REPO)}</a>' if GITHUB else ""
    fix = f'<p>Corrections: <a href="{esc(GITHUB)}/issues">{url_text(REPO + "/issues")}</a></p>' if GITHUB else ""
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(WORDMARK)}">
{head}<link rel="icon" href="{pre}assets/icon.svg?v={V['icon.svg']}" type="image/svg+xml">
<link rel="apple-touch-icon" href="{pre}assets/apple-touch-icon.png?v={V.get('apple-touch-icon.png', '')}">
{fonts}
{THEME_EARLY}
<link rel="stylesheet" href="{pre}assets/site.css?v={V['site.css']}">
<script src="{pre}assets/site.js?v={V['site.js']}" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to the content</a>
<header class="top"><a class="brand" href="{pre}">{logo()}<span>{esc(WORDMARK)}<span class="stop"></span></span></a>
<button type="button" class="menu-btn" aria-expanded="false" aria-controls="menu"><span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>Menu</button>
<div class="menu" id="menu"><nav aria-label="Sections">{nav}</nav>
<div class="tools"><a class="pdf" href="{pre}downloads/{PDF_NAME.replace(' ', '%20')}">Download PDF</a>
<button type="button" class="theme-toggle" data-mode="auto" aria-label="Colour theme" hidden>{THEME_ICONS}</button>
<button type="button" class="lefty-toggle" aria-pressed="false" hidden>Left-handed</button></div></div></header>
<main id="main">
{body}
</main>
<footer>
<p><b>Version {VERSION} · {DATE}</b>{built}</p>
<p>Book, site and chord data: <a href="https://creativecommons.org/licenses/by/4.0/">CC&nbsp;BY&nbsp;4.0</a>, free to use, share and adapt with credit to the author. Code: MIT.</p>
{fix}
</footer>
</body>
</html>
"""
    full = os.path.join(OUT, file) if file else os.path.join(OUT, path, "index.html") if path else os.path.join(OUT, "index.html")
    if file is None: WRITTEN.append(url)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf8").write(doc)

def legend(fold=False):
    """The key to the diagrams, shown above them: the numbers are degrees of the chord, the letters are fingers. fold: on a
    phone it is folded behind the "?" button (key_button()), and site.js opens it."""
    items = KEY_LABELS
    li = "".join(f'<li><svg class="dg key" viewBox="0 0 14 14" aria-hidden="true">{dot(7, 7, d, 6, (1.2, 1.05))}</svg>{esc(t)}</li>' for d, t in items)
    attrs = ' class="legend fold" id="key"' if fold else ' class="legend"'
    return (f'<div{attrs}><p><b>Numbers</b> in the dots are degrees of the chord, not fingers:</p>'
            f'<ul>{li}</ul><p><b>Letters</b> under the strings are fingers: <b>I</b>&nbsp;index, <b>M</b>&nbsp;middle, <b>R</b>&nbsp;ring, <b>L</b>&nbsp;little</p></div>')

KEY_BUTTON = ('<button type="button" class="key-btn" aria-expanded="false" aria-controls="key" aria-label="What the numbers and letters mean" '
              'title="What the numbers and letters mean">?</button>')   # shown on a phone only

def chord_name(r, q): return NOTES[r] + q

def more_voicings(r, q, book):
    """The published voicings the book has no room for: all that at least two independent sources list,
    near-duplicates included (only the book, short of room, keeps one of two voicings that differ by one muted string)."""
    return [(t, b) for t, b in voicings(r, EVERY[q], near=False) if tuple(frets(t, b)) not in book and t["nsrc"] >= 2]

# ---------- chord pages
def chord_page(r, q, qname, formula, about, book_temps):
    name = chord_name(r, q)
    alias = other_name(r)
    book_vs = shown(r, book_temps)
    keys_ = {tuple(frets(t, b)) for t, b in book_vs}
    more = more_voicings(r, q, keys_)
    degs = formula.split()
    form = "".join(f'<div><b>{esc(d)}</b><span>{esc(spell(r, d))}</span></div>' for d in degs)
    roots = "".join(f'<a href="../../{SLUG[k]}/{FILE[q]}/"{CUR if k == r else ""}>{esc(NOTES[k])}</a>' for k in range(12))
    types = "".join(f'<div><p class="sub">{esc(short)}</p><div class="pick" role="group" aria-label="{esc(title)}">'   # grouped as the pages of each root in the book
                    + "".join(f'<a href="../{FILE[qq]}/"{CUR if qq == q else ""}>{esc(qq or "major")}</a>' for qq, *_x in rows) + "</div></div>"
                    for (title, rows), short in zip(GROUPS, GROUP_SHORT))
    kinds = [kind_of(t, b) for t, b in more]                                 # a filter is offered only when it shows some cards, not all
    useful = [(k, t) for k, t in [("open", "open"), ("barre", "barre"), ("6", "root on 6th"), ("5", "root on 5th"), ("4", "root on 4th")]
              if 0 < sum(k in kb for kb in kinds) < len(kinds)]
    filt = ('<div class="filters" hidden><span>Show:</span>' + "".join(f'<button type="button" data-filter="{k}" aria-pressed="{"true" if k == "all" else "false"}">{t}</button>'
            for k, t in [("all", "all")] + useful) + "</div>") if useful else ""
    body = f"""<div class="layout">
<aside class="side"><nav class="chooser" aria-label="Choose a chord"><div><p class="sub">Root</p><div class="pick roots" role="group" aria-label="Root">{roots}</div></div><div class="types">{types}</div></nav>{legend()}</aside>
<article class="chord">
<header class="cinfo"><div><h1>{esc(name)}{f'<span class="alias">= {esc(alias + q)}</span>' if alias else ""}</h1>
<p>{esc(qname)} · <span class="muted">{esc(about)}</span></p></div><div class="formula">{form}</div>{KEY_BUTTON}</header>
{legend(fold=True)}
<section><h2>In the book</h2><div class="voicings book">{"".join(card(q, name, t, b) for t, b in book_vs)}</div></section>
{f'<section><h2>More published voicings</h2>{filt}<div class="voicings more">{"".join(card(q, name, t, b) for t, b in more)}</div></section>' if more else ""}
</article></div>"""
    plain = qname.replace(" (", ", ").removesuffix(")") if " (" in qname else qname     # "diminished 7th, °7": no brackets in brackets
    page(chord_url(r, q).rstrip("/"), f"{name} chord ({plain}) – {WORDMARK}",
         body, f"{name} ({plain}) guitar chord: {len(book_vs) + len(more)} published voicings with scale degrees, note names, fingers and sources.")
    return len(book_vs), len(more)

def root_page(r):
    secs = []
    for title, rows in GROUPS:
        cards = []
        for q, qname, formula, about, temps in rows:
            vs = shown(r, temps)
            cards.append(f'<a class="mini" href="{FILE[q]}/"><h3>{esc(chord_name(r, q))}</h3><span class="muted">{esc(qname)}</span>'
                         f'<div class="minis">{"".join(diagram(t, b) for t, b in vs)}</div></a>')
        secs.append(f'<section><h2>{esc(title)}</h2><div class="minigrid">{"".join(cards)}</div></section>')
    body = f'<div class="head-key"><h1>{esc(both_names(r))} chords</h1>{KEY_BUTTON}</div>{legend(fold=True)}{"".join(secs)}'
    page(root_url(r).rstrip("/"), f"{both_names(r)} guitar chords – {WORDMARK}", body,
         f"Every {both_names(r)} chord in {TITLE}: {len(ALL)} chord types with scale degrees and fingers.")

def wordmark_svg():
    """The name as on the book's cover, in grid cells of 100 units: one letter per cell (the monospaced advance is one
    cell), the baselines on lines 2, 4 and 6; the root square, as the full stop, sits on the last baseline in a cell of its own."""
    upm, _xh, gl = font_metrics("bold"); F = 100 * upm / gl["h"][0]; words = WORDMARK.split(" ")
    texts = "".join(f'<text x="0" y="{200 * (k + 1)}">{esc(w)}</text>' for k, w in enumerate(words))
    s = 0.2 * F; yb = 200 * len(words); n = len(words[-1])
    return (f'<svg viewBox="0 0 {100 * (n + 1)} {yb}" style="width: calc(var(--c) * {n + 1}); height: calc(var(--c) * {yb // 100})" role="img" '
            f'aria-label="{esc(WORDMARK)}"><g font-size="{F:.1f}">{texts}</g><rect x="{100 * n + (100 - s) / 2:.1f}" y="{yb - s:.1f}" '
            f'width="{s:.1f}" height="{s:.1f}" rx="{0.028 * F:.1f}"/></svg>')

def tables(kind, corner, heads, rows, cuts):
    """A table, whole for a wide screen and cut into narrower ones (cuts: CSS class -> columns per table) that site.css
    shows on smaller screens instead, so that no table runs past the page. rows: a group title, or (row head, cells)."""
    def one(cols):
        body = "".join(f'<tr><th colspan="{len(cols) + 1}" class="group">{r}</th></tr>' if isinstance(r, str)
                       else f"<tr>{r[0]}" + "".join(r[1][i] for i in cols) + "</tr>" for r in rows)
        return f'<div class="scroll"><table class="{kind}"><tr>{corner}{"".join(heads[i] for i in cols)}</tr>{body}</table></div>'
    n = len(heads)
    return (f'<div class="tables t-{kind}"><div class="whole">{one(range(n))}</div>'
            + "".join(f'<div class="cut {c}">' + "".join(one(range(a, min(a + k, n))) for a in range(0, n, k)) + "</div>" for c, k in cuts.items())
            + "</div>")

def index_pages():
    roots = "".join(f'<a class="rootcard" href="{root_url(r)}"><b>{esc(both_names(r))}</b></a>' for r in range(12))
    steps = "".join(f'<svg class="dg" viewBox="0 0 14 14" aria-hidden="true">{dot(7, 7, d, 6, (1.2, 1.05))}</svg>' for d in ("1", "3", "5", "7", "9", "11", "13"))
    first = "".join(f'<a class="mini" href="{chord_url(r, q)}"><h3>{esc(chord_name(r, q))}</h3>{diagram(*find(r, q, want))}</a>' for r, q, want in FIRST_TWELVE)
    body = f"""<section class="cover"><h1 class="wordmark">{wordmark_svg()}</h1>
<div class="about"><p class="subtitle">{esc(SUBTITLE.lower())}</p><div class="steps">{steps}</div>
<p><a class="button ghost" href="how-to-read/">How to read the diagrams</a></p></div></section>
<section><h2>Common chords</h2><div class="twelve">{first}</div></section>
<section><h2>Chords by root</h2><div class="rootgrid">{roots}</div></section>"""
    page("", WORDMARK, body, "A free guitar chord reference: every note shows its role in the chord, with fingers and published sources for every voicing.", "")
    heads = [f'<th scope="col">{esc(n)}</th>' for n in NOTES]
    rows = []
    for title, grp in GROUPS:
        rows.append(esc(title))
        for q, qname, *_x in grp:
            rows.append((f'<th scope="row">{esc(q or "major")}</th>', [f'<td><a href="{SLUG[r]}/{FILE[q]}/">{esc(chord_name(r, q))}</a></td>' for r in range(12)]))
    page("chords", f"All chords – {WORDMARK}", f'<h1>All chords</h1>{tables("grid", "<td></td>", heads, rows, {"by6": 6, "by3": 3})}',
         f"Every chord in {TITLE}, by type and root.", "chords/")

def keys_page_html():
    def table(keys, numerals, minor):
        rows = [(f'<th scope="row">{esc(k + ("m" if minor else ""))}</th>',
                 [f'<td><a href="../{chord_url(pc, tq)}">{esc(root + tq)}</a><a class="sev" href="../{chord_url(pc, sq)}">{esc(root + sq)}</a></td>'
                  for num, root, pc, tq, sq in key_chords(k, minor)]) for k in keys]
        return tables("keys", '<th scope="col">Key</th>', [f'<th scope="col">{esc(n)}</th>' for n in numerals], rows, {"by4": 4})
    body = f"""<h1>Chords in each key</h1>
<h2>Chords in major keys</h2>
<p>Every major key uses the same pattern of chords: major, minor, minor, major, major, minor, diminished. Each cell shows the triad and, below it, the seventh chord.</p>
{table(KEYS, NUMERALS, False)}
<p class="muted">The vi chord is the relative minor. C♯ major is written as D♭ major. In F♯ major the vii chord is spelled E♯dim, the same sound as Fdim. The V chord is often played as a 7th chord (G7 in C).</p>
<h2>Chords in minor keys</h2>
<p>Every natural minor key uses the pattern minor, diminished, major, minor, minor, major, major. In practice the v chord is usually played major, often as a 7th chord (E or E7 in A minor, instead of Em), because a major V leads more strongly back to i. This comes from the harmonic minor scale, which raises the 7th note (G♯ in A minor).</p>
{table(MINOR_KEYS, MINOR_NUMERALS, True)}"""
    page("keys", f"Chords in each key – {WORDMARK}", body, "The chords of every major and natural minor key, linked to their voicings.", "keys/")

def slash_page_html():
    cards = []
    for s in SLASH_CHORDS:
        t, b = s["t"], s["base"]
        cards.append(f'<figure class="vcard"><div class="vlabel"><b><a href="../{chord_url(s["r"], s["q"])}">{esc(s["name"])}</a></b> <span>{esc(s["bass"])}</span></div>'
                     f'{diagram(t, b, s["name"] + ": " + strings_text(t, b))}<figcaption>{sources_html("slash", t, b)}</figcaption></figure>')
    body = f"""<div class="head-key"><h1>Slash chords</h1>{KEY_BUTTON}</div>
<p>C/E means a C chord with E as the lowest note. The bass is usually another note of the chord, which smooths the bass line between chords. When the bass is not in the chord (C/B), it is a passing note in a falling or rising bass line. Degrees are counted from the chord root, so the bass of D/F♯ shows 3.</p>
{legend(fold=True)}
<div class="voicings">{"".join(cards)}</div>"""
    page("slash-chords", f"Slash chords – {WORDMARK}", body, "Common slash chords with scale degrees, fingers and published sources.", "slash-chords/")

def howto_page_html():
    roots = {"C": "5th", "A": "5th", "G": "6th", "E": "6th", "D": "4th"}       # the string of the lowest root
    cards = "".join(f'<figure class="vcard"><div class="vlabel"><b>{k} shape</b></div>{diagram(t, 0, k + " shape: " + strings_text(t, 0))}<figcaption class="muted cap">lowest root on the {roots[k]}&nbsp;string</figcaption></figure>'
                    for k, t in zip("CAGED", caged()))
    body = f"""<h1>How to read the diagrams</h1>
<ul class="read">
<li>Strings go left to right from the 6th (thick, low E) to the 1st (thin, high E). Horizontal lines are frets.</li>
<li>A thick line at the top is the nut (open position). A number beside the first row gives its fret.</li>
<li>A dot above the nut is an open string (a square when it is the root). × means the string is not played. The blue bar is a barre: one finger lying flat across several strings.</li>
<li>Every note shows its degree in the chord, in the colour of its step of the scale. Roots are dark squares and fifths the lightest dots; in black and white the other notes share one grey and their numbers tell them apart.</li>
<li>The label names the CAGED shape the voicing comes from (E&nbsp;shape, A&nbsp;shape…) and where it sits on the neck. “E shape, 4 strings” is the E shape on the four thinnest strings (like F = xx3211). Voicings outside the five shapes are named by the string that carries the lowest root: Root on 6th, 5th or 4th.</li>
<li>Letters under the strings are the left-hand fingers: I&nbsp;index, M&nbsp;middle, R&nbsp;ring, L&nbsp;little. The same letter on several strings means one finger lies flat across them. Left-handed players can mirror every diagram with the “Left-handed” button at the top.</li>
<li>Every voicing lists its sources: the chord libraries, lessons and books that publish it.</li>
</ul>
{legend()}
<h2>The five CAGED shapes</h2>
<p>Almost any chord can be played with one of five shapes, named after the open chords C, A, G, E and D. Slide an open shape up the neck, replace the nut with a barre or your index finger, and you get the same chord type on a new root. Along the neck the shapes link up in the order C → A → G → E → D and then repeat. For example, C major: open C shape, A shape at fret 3, G shape around frets 5–8, E shape at fret 8, D shape at fret 10, and the C shape again at fret&nbsp;12.</p>
<div class="voicings">{cards}</div>"""
    page("how-to-read", f"How to read the diagrams – {WORDMARK}", body, "How to read the chord diagrams: degrees, fingers, CAGED shapes.", "how-to-read/")

def about_page_html():
    n, ncites, _names, _short = provenance()
    src = "".join(f'<li><a href="{esc(s["site"])}">{esc(s["name"])}</a>' + (f' <span class="muted">({esc(s["note"])})</span>' if s.get("note") else "") + "</li>"
                  for k, s in sorted(data.SOURCES.items(), key=lambda kv: kv[1]["name"].lower()))
    body = f"""<h1>How this reference was checked</h1>
<ul class="read">
<li>Every voicing in this reference comes from published sources. The book shows a voicing only if at least two independent sources list it: chord libraries, lessons and books by guitar teachers and publishers. Sites that copy one another, or share a publisher, count as one source. The open-source database <span class="nw">chords-db</span>, and the sites that reproduce it, are cited but never counted as confirmation.</li>
<li>Every finger letter is the fingering most of those sources give. Where they are evenly split, JustinGuitar’s fingering is used, then Fender’s, then the one an earlier draft of this book printed, then the one <span class="nw">chords-db</span> gives.</li>
<li>Every voicing in the book was also checked by computer: each degree number matches the interval from the root, the root is the lowest note (in slash chords, the named bass), there are no wrong notes, the required notes are present, and the fingering can be played. The note sets were checked independently with the open-source library pychord.</li>
<li>The book’s {n:,} diagrams rest on {ncites:,} citations. Every chord page of this site lists the sources of each voicing, with links, and also shows the further voicings that at least two independent sources publish but the book has no room for.</li>
</ul>
<h2>Sources</h2><ul class="links">{src}</ul>
<h2>Downloads</h2><ul class="links"><li><a href="../downloads/{PDF_NAME.replace(' ', '%20')}">The book</a> <span class="muted">(PDF, A4)</span></li><li><a href="../downloads/data/">The chord data</a> <span class="muted">(TOML, with every citation)</span></li><li><a href="../downloads/{BOOK_SLUG}.chordpro">ChordPro chord definitions</a> <span class="muted">(one voicing per chord, for songbook programs)</span></li><li><a href="../downloads/chords-db.json">The book’s voicings in the chords-db JSON format</a></li></ul>"""
    page("about", f"How this reference was checked – {WORDMARK}", body, f"How every voicing and fingering in {TITLE} was checked against published sources.", "about/")

# ---------- downloads
def downloads():
    d = os.path.join(OUT, "downloads"); os.makedirs(d, exist_ok=True)
    pdf = os.path.join(PROJ, "dist", PDF_NAME)
    if os.path.exists(pdf): shutil.copy(pdf, os.path.join(d, PDF_NAME))
    shutil.copytree(os.path.join(PROJ, "data"), os.path.join(d, "data"), dirs_exist_ok=True)
    files = sorted(os.path.relpath(os.path.join(root, f), os.path.join(d, "data")) for root, _dirs, fs in os.walk(os.path.join(d, "data")) for f in fs)
    items = "".join(f'<li><a href="{esc(rel)}">{esc(rel)}</a></li>' for rel in files)
    page("downloads/data", f"Chord data – {WORDMARK}", f'<h1>Chord data (TOML)</h1><p>The chord data as plain text: every chord type, voicing and citation, including candidates that only one independent source publishes so far (neither the book nor this site shows those). The format: <a href="README.md">README.md</a>.</p><ul class="links">{items}</ul>',
         "The chord data of the book: every chord type, voicing and citation, in TOML.")
    # ChordPro: one definition per chord, the first voicing the book shows
    cp = [f"# {TITLE} {VERSION} by {AUTHOR} ({REPO}), CC BY 4.0." + " One {define} per chord: the first voicing of the book.\n"]
    FN = {None: "0", "I": "1", "M": "2", "R": "3", "L": "4"}
    def base_fret(fr):          # where a ChordPro or chords-db chart starts: fret 1 when the voicing fits in four frets, else its lowest fret
        return 1 if max(f for f in fr if f is not None) <= 4 else min(f for f in fr if f)
    for q, *_x, temps in ALL:
        for r in range(12):
            t, b = shown(r, temps)[0]
            fr, fg = frets(t, b), t["fing"]; base = base_fret(fr)
            rel = " ".join("x" if f is None else str(f if f == 0 else f - base + 1) for f in fr)
            cp.append(f"{{define: {chord_name(r, q).replace('♯', '#').replace('♭', 'b')} base-fret {base} frets {rel} fingers {' '.join(FN[x] for x in fg)}}}\n")
    open(os.path.join(d, f"{BOOK_SLUG}.chordpro"), "w", encoding="utf8").write("".join(cp))
    # chords-db format: the book's voicings
    DBK = ["C", "Csharp", "D", "Eb", "E", "F", "Fsharp", "G", "Ab", "A", "Bb", "B"]
    out = {"main": {"strings": 6, "fretsOnChord": 4, "name": "guitar"}, "tunings": {"standard": ["E2", "A2", "D3", "G3", "B3", "E4"]},
           "source": f"{TITLE} {VERSION}, {AUTHOR} ({REPO}), CC BY 4.0", "chords": {k: [] for k in DBK}}
    for q, *_x, temps in ALL:
        for r in range(12):
            pos = []
            for t, b in shown(r, temps):
                fr, fg = frets(t, b), t["fing"]; base = base_fret(fr)
                pos.append({"frets": [-1 if f is None else (0 if f == 0 else f - base + 1) for f in fr],
                            "fingers": [int(FN[x]) for x in fg], "baseFret": base,
                            "barres": sorted({fr[a] - base + 1 for a, _z, _o in t["bars"]})})
            out["chords"][DBK[r]].append({"key": DBK[r], "suffix": q or "major", "positions": pos})
    json.dump(out, open(os.path.join(d, "chords-db.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)

def assets():
    """CSS (colours and fonts from src/design.toml, then the layout), the script, the icon, and the fonts as small woff2 subsets."""
    a = os.path.join(OUT, "assets"); os.makedirs(os.path.join(a, "fonts"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "site", "site.js"), os.path.join(a, "site.js"))
    open(os.path.join(a, "icon.svg"), "w", encoding="utf8").write(icon_svg())
    text = "U+0020-007E, U+00A0-00FF, U+2013-2014, U+2018-201D, U+2026, U+2190-2193, U+266D-266F"   # the characters the site uses (audit_site.py checks)
    faces = [("HoC Text", 400, "regular", text, "text-regular", ""),
             ("HoC Text", 700, "bold", text, "text-bold", "")]
    faces += [("HoC Music", 400, "music", f"U+{ord(ch):X}", "music", f"; size-adjust: {k * 100:.0f}%") for ch, k in DESIGN["music"].items()]
    css = []
    from fontTools import subset        # with brotli, for woff2 (requirements.txt)
    import logging; logging.getLogger("fontTools").setLevel(logging.ERROR)
    files = {}
    for _f, _w, k, ranges, out, _x in faces: files.setdefault((k, out), []).extend(ranges.split(", "))
    for (k, out), ranges in files.items():
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]; opts.name_IDs = ["*"]; opts.notdef_outline = True
        f = subset.load_font(font_path(k), opts)
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=[cp for r in ranges for cp in _range(r)]); sub.subset(f)
        subset.save_font(f, os.path.join(a, "fonts", out + ".woff2"), opts)
        V[f"fonts/{out}.woff2"] = hashlib.sha1(open(os.path.join(a, "fonts", out + ".woff2"), "rb").read()).hexdigest()[:8]
    for family, weight, k, ranges, out, extra in faces:
        css.append(f'@font-face {{ font-family: "{family}"; src: url("fonts/{out}.woff2?v={V["fonts/" + out + ".woff2"]}") format("woff2"); font-weight: {weight}; font-display: swap; unicode-range: {ranges}{extra} }}')
    for lic in ("LICENSE-JetBrainsMono.txt", "LICENSE-NotoMusic.txt"):
        shutil.copy(os.path.join(PROJ, "licenses", lic), os.path.join(a, "fonts", lic))
    def theme(c):
        v = [f"--{k}: {c[k]}" for k in ("bg", "ink", "muted", "line", "grid", "barre", "link")] + [f"--card: {c['paper']}"]   # site cards are paper on the tinted page
        v += [f"--sel: {c['ink']}", f"--sel-ink: {c['bg']}", f"--logo-grid: {c['logo_grid']}", f"--cover-grid: {c['cover_grid']}"]
        for d, (fill, ink) in c["degrees"].items(): v += [f"--{d}: {fill}", f"--{d}i: {ink}"]
        return "; ".join(v)
    css.append(f':root {{ {theme(DESIGN["colors"])};\n  --font: "HoC Text", "HoC Music", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif }}')
    dark = theme(DESIGN["dark"])      # the system's theme, unless the reader chose one with the switch (data-theme on <html>)
    css.append(f'@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ {dark}; color-scheme: dark }} }}')
    css.append(f':root[data-theme="dark"] {{ {dark}; color-scheme: dark }} :root[data-theme="light"] {{ color-scheme: light }}')
    css.append(" ".join(f".dg .{d} {{ fill: var(--{d}) }} .dg .{d}t {{ fill: var(--{d}i) }}" for d in DESIGN["colors"]["degrees"]))   # one colour per step of the scale
    open(os.path.join(a, "site.css"), "w", encoding="utf8").write("\n".join(css) + "\n" + open(os.path.join(HERE, "site", "site.css"), encoding="utf8").read())
    for f in ("share.png", "apple-touch-icon.png"):                # drawn by build_en.py next to the PDF
        if os.path.exists(os.path.join(PROJ, "dist", f)): shutil.copy(os.path.join(PROJ, "dist", f), os.path.join(a, f))
    for f in ("icon.svg", "site.css", "site.js", "share.png", "apple-touch-icon.png"):
        if os.path.exists(os.path.join(a, f)): V[f] = hashlib.sha1(open(os.path.join(a, f), "rb").read()).hexdigest()[:8]

def _range(r):
    """'U+2190-21FF' -> its code points."""
    lo, _, hi = r.replace("U+", "").partition("-")
    return range(int(lo, 16), int(hi or lo, 16) + 1)

if __name__ == "__main__":
    if os.path.isdir(OUT):            # only a previous build (or an empty folder) is replaced, never anything else
        if os.listdir(OUT) and not os.path.exists(os.path.join(OUT, "assets", "site.css")): sys.exit(f"{OUT} is not a built site; not deleting it")
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    assets()
    n_shown = n_more = 0
    for q, qname, formula, about, temps in ALL:
        for r in range(12):
            a, m = chord_page(r, q, qname, formula, about, temps); n_shown += a; n_more += m
    for r in range(12): root_page(r)
    index_pages(); keys_page_html(); slash_page_html(); howto_page_html(); about_page_html(); downloads()
    page("", f"Not found – {WORDMARK}", f'<h1>Not found</h1><p>There is no page at this address. Start from <a href="{urlparse(SITE).path}">the home page</a> or <a href="{urlparse(SITE).path}chords/">all&nbsp;chords</a>.</p>',
         "Page not found.", file="404.html", pre=urlparse(SITE).path)
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf8").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{esc(u)}</loc></url>\n" for u in WRITTEN) + "</urlset>\n")
    pages = sum(len([f for f in fs if f == "index.html"]) for _r, _d, fs in os.walk(OUT))
    print("ok", OUT, pages, "pages,", n_shown, "book voicings,", n_more, "more voicings on chord pages")
