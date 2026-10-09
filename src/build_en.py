# Builds the book, "<title>.pdf" (data/book.toml). Usage: python3 build_en.py [output.pdf]
import os, sys
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import ttfonts
_to_unicode = ttfonts.makeToUnicodeCMap
def _to_unicode_utf16(name, subset):
    """reportlab's text map, with characters beyond U+FFFF (𝄪 𝄫) written as UTF-16 pairs, so they copy and search as themselves."""
    s = _to_unicode(name, subset)
    for v in subset:
        if v > 0xFFFF: s = s.replace("<%04X>" % v, "<%s>" % chr(v).encode("utf-16-be").hex().upper())
    return s
ttfonts.makeToUnicodeCMap = _to_unicode_utf16
from reportlab.lib.colors import HexColor, white
import data
data.require_valid()                 # before anything is made from the data
from book import TITLE, SUBTITLE, WORDMARK, SITE, font_metrics, VERSION, DATE, AUTHOR, GITHUB, REPO, PDF_NAME, PROJ, DESIGN, font_path, provenance, SP, RH, R, OPEN_DY, LABEL_K
from chords import GROUPS, GROUP_SHORT, SLASH_CHORDS, FIRST_TWELVE, shown, tag, position, find, caged
from theory import NOTES, GROUP, KEY_LABELS, spell, other_name, both_names, KEYS, NUMERALS, MINOR_KEYS, MINOR_NUMERALS, key_chords

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "dist", PDF_NAME)

# ---- fonts and colours (src/design.toml)
for name, k in (("Sans", "regular"), ("SansB", "bold"), ("Music", "music")):
    pdfmetrics.registerFont(TTFont(name, font_path(k)))
_C = DESIGN["colors"]
INK, MUTED, LINE, GRID = HexColor(_C["ink"]), HexColor(_C["muted"]), HexColor(_C["line"]), HexColor(_C["grid"])
BARRE, CARD, LINK = HexColor(_C["barre"]), HexColor(_C["card"]), HexColor(_C["link"])
COVER_GRID = HexColor(_C["cover_grid"])
COL = {k: (HexColor(f), HexColor(i)) for k, (f, i) in _C["degrees"].items()}

# ---- characters the text font lacks (𝄪 𝄫) are drawn from the music font
FALLBACK = {"Sans": "Music", "SansB": "Music"}
_has = lambda font, ch: ord(ch) in pdfmetrics.getFont(font).face.charToGlyph
_sw = pdfmetrics.stringWidth
def runs(text, font):
    """[(font, piece)]: the text split where a character has to come from another font."""
    out = []
    for ch in text:
        f = font if font not in FALLBACK or _has(font, ch) else FALLBACK[font]
        if out and out[-1][0] == f: out[-1][1] += ch
        else: out.append([f, ch])
    return out
def _string_width(text, font, size, encoding="utf8"):
    return sum(_sw(p, f, size) for f, p in runs(text, font)) if font in FALLBACK else _sw(text, font, size)
pdfmetrics.stringWidth = _string_width        # every measurement, line wrapping included, sees the fallbacks

class Canvas(canvas.Canvas):
    def drawString(self, x, y, text, *a, **k):
        font, size = self._fontname, self._fontsize
        if font not in FALLBACK: return super().drawString(x, y, text, *a, **k)
        for f, piece in runs(text, font):
            self.setFont(f, size); super().drawString(x, y, piece); x += _sw(piece, f, size)
        self.setFont(font, size)
    def drawRightString(self, x, y, text, *a, **k):
        self.drawString(x - _string_width(text, self._fontname, self._fontsize), y, text)
    def drawCentredString(self, x, y, text, *a, **k):
        self.drawString(x - _string_width(text, self._fontname, self._fontsize) / 2, y, text)
W, H = A4; M = 36

# ---- page map
GI = {q: gi for gi, (_t, g) in enumerate(GROUPS) for q, *_r in g}
NG = len(GROUPS)                     # pages per root (data/book.toml)
FRONT = ["cover", "contents", "start", "howto", "types", "keys", "minorkeys", "slash", "index"]   # the pages before the chords, in order
PAGE = {k: i + 1 for i, k in enumerate(FRONT)}; PAGE["caged"] = PAGE["howto"]
def ROOT_PAGE(r, gi): return len(FRONT) + 1 + NG * r + gi
ABOUT_PAGE = len(FRONT) + 1 + 12 * NG

# ---- drawing primitives
def dot(c, x, y, r, deg, lk=(1.2, 1.05)):
    """Root = square, everything else = filled circle, in the colour of its step of the scale; the degree is printed inside,
    lk times the radius high (one character, two)."""
    k = GROUP[deg]; fill, ink = COL[k]
    if k == "d1":
        c.setFillColor(fill); c.roundRect(x - r, y - r, 2 * r, 2 * r, r * 0.28, stroke=0, fill=1)
    else:
        c.setFillColor(fill); c.circle(x, y, r, stroke=0, fill=1)
    fs = r * (lk[1] if len(deg) > 1 else lk[0])
    c.setFillColor(ink); c.setFont("SansB", fs); c.drawCentredString(x, y - fs * 0.36, deg)

FING_SIZE = 6.8                      # the finger letters under a diagram
def diagram(c, x0, top, t, base, s=1.0, fingers=True):
    sp, rh, r = SP * s, RH * s, R * s
    maxoff = max(v[0] for v in t["n"] if v)
    rows = max(4, maxoff + (1 if base > 0 else 0))
    xs = [x0 + i * sp for i in range(6)]
    bottom = top - rows * rh
    row_y = lambda o: top - ((o + 1 if base > 0 else o) - 0.5) * rh
    c.setLineWidth(0.6 * s); c.setStrokeColor(GRID)
    for x in xs: c.line(x, top, x, bottom)
    for k in range(1, rows + 1): c.line(xs[0], top - k * rh, xs[5], top - k * rh)       # frets as dark as strings
    if base > 0:
        c.setFillColor(MUTED); c.setFont("SansB", 7 * s)
        c.drawRightString(xs[0] - r - 2.5 * s, top - rh / 2 - 2.5 * s, str(base))
    c.setFillColor(BARRE)
    for a, z, o in t["bars"]:                    # a finger lying flat
        c.roundRect(xs[a] - r - 1.2 * s, row_y(o) - r - 1.2 * s, xs[z] - xs[a] + 2 * r + 2.4 * s, 2 * r + 2.4 * s, r + 1.2 * s, stroke=0, fill=1)
    if base <= 1: c.setStrokeColor(INK); c.setLineWidth(2.6 * s)
    else: c.setStrokeColor(LINE); c.setLineWidth(0.6 * s)
    c.line(xs[0] - 0.5, top, xs[5] + 0.5, top)
    oy = top + OPEN_DY * s
    for i, v in enumerate(t["n"]):
        if v is None:
            c.setFillColor(MUTED); c.setFont("Sans", 8 * s); c.drawCentredString(xs[i], oy - 2.8 * s, "×"); continue
        o, d = v
        dot(c, xs[i], oy if (base == 0 and o == 0) else row_y(o), r, d, LABEL_K)
    fy = bottom - 8.5 * s
    if fingers:
        c.setFillColor(INK); c.setFont("SansB", FING_SIZE * s)
        for i, f in enumerate(t["fing"]):
            if f: c.drawCentredString(xs[i], fy, f)
    return dict(xs=xs, top=top, bottom=bottom, rh=rh, r=r, row_y=row_y, oy=oy, fy=fy)

def legend(c, x, y, size=5.4, fs=7.5, right=None):
    """The key to the degrees ("Numbers = degrees:", then each colour); wraps onto a second line when it runs out of width.
    Returns the last line's y."""
    right = right or (W - M)
    lead = "Numbers = degrees:"
    c.setFillColor(INK); c.setFont("SansB", fs); c.drawString(x, y, lead)
    items = KEY_LABELS
    x0 = x; x += pdfmetrics.stringWidth(lead, "SansB", fs) + 10
    for d, label in items:
        w = 2 * size + 4 + pdfmetrics.stringWidth(label, "Sans", fs)
        if x + w > right and x > x0:
            x = x0; y -= fs + 6
        dot(c, x + size, y + size * 0.3, size, d)
        c.setFillColor(MUTED); c.setFont("Sans", fs); c.drawString(x + 2 * size + 4, y, label)
        x += w + 14
    return y

def wrap(text, font, size, width, widows=False):
    """The lines of a paragraph at most width wide, broken at spaces only: a non-breaking space keeps its words together.
    With widows=False a last line of one word takes the previous line's last word with it."""
    out, line = [], ""
    for word in text.split(" "):
        cand = word if not line else line + " " + word
        if not line or pdfmetrics.stringWidth(cand.replace("\u00a0", " "), font, size) <= width: line = cand
        else: out.append(line); line = word
    out = out + [line] if line else out
    if not widows and len(out) > 1 and " " not in out[-1] and out[-2].count(" ") >= 2:
        head, last = out[-2].rsplit(" ", 1)
        if pdfmetrics.stringWidth((last + " " + out[-1]).replace("\u00a0", " "), font, size) <= width: out[-2:] = [head, last + " " + out[-1]]
    return out

def para(c, text, x, y, font="Sans", size=9.5, color=MUTED, width=W - 2 * M, lead=None):
    lead = lead or size * 1.38
    c.setFillColor(color); c.setFont(font, size)
    for ln in wrap(text, font, size, width, widows=width < 200): c.drawString(x, y, ln.replace("\u00a0", " ")); y -= lead
    return y

def bullets(c, items, y, size=9.5, gap=2):
    for ln in items: y = para(c, ln, M, y, size=size) - gap
    return y

def link(c, key, x1, y1, x2, y2):
    c.linkRect("", key, (x1, y1, x2, y2), relative=0, thickness=0)

def label_size(t, base, size=7.5, width=None):
    """The size of a diagram's label: smaller when the label is wider than its cell (width), as long chord names are."""
    tw = pdfmetrics.stringWidth(tag(t), "SansB", size) + pdfmetrics.stringWidth(position(t, base), "Sans", size)
    return size if width is None or tw + 5 <= width else round(size * (width - 5) / tw, 2)

def label_line(c, cx, y, t, base, size=7.5, width=None):
    """The shape and position above a diagram, centred on cx; returns its left edge."""
    tag_, pos = tag(t), position(t, base)
    size = label_size(t, base, size, width)
    tw = pdfmetrics.stringWidth(tag_, "SansB", size) + 5 + pdfmetrics.stringWidth(pos, "Sans", size)
    tx = cx - tw / 2
    c.setFillColor(INK); c.setFont("SansB", size); c.drawString(tx, y, tag_)
    c.setFillColor(MUTED); c.setFont("Sans", size); c.drawString(tx + pdfmetrics.stringWidth(tag_, "SansB", size) + 5, y, pos)
    return tx

def note_text(c, x, y, note, size=7.5):
    """A note name; double sharps and flats come from the music font, scaled as design.toml says."""
    if note[-1] in DESIGN["music"]:
        c.drawString(x, y, note[:-1])
        c.setFont("Music", size * DESIGN["music"][note[-1]]); c.drawString(x + pdfmetrics.stringWidth(note[:-1], "Sans", size) + 0.3, y, note[-1])
        c.setFont("Sans", size)
    else:
        c.drawString(x, y, note)

def back_link(c):
    c.setFillColor(LINK); c.setFont("Sans", 8.5)
    txt = "↑ Contents"; w = pdfmetrics.stringWidth(txt, "Sans", 8.5)
    c.drawString(W - M - w, H - M - 8, txt); link(c, "contents", W - M - w - 2, H - M - 11, W - M + 2, H - M + 2)

def page_title(c, text, key, outline=None, level=0):
    c.bookmarkPage(key); c.addOutlineEntry(outline or text, key, level)
    back_link(c)
    c.setFillColor(INK); c.setFont("SansB", 18); c.drawString(M, H - M - 22, text)

FINGER_KEY = "Letters = fingers: I index, M middle, R ring, L little"
def footer(c, page, show_legend=True):
    if show_legend:
        legend(c, M, M + 6, 4.8, 7, right=W - M - 20)
        c.setFillColor(INK); c.setFont("SansB", 7); c.drawRightString(W - M - 24, M - 7, FINGER_KEY)
    c.setFillColor(MUTED); c.setFont("Sans", 7.5); c.drawRightString(W - M, M - 6, str(page))

def chord_link_text(c, x, y, text, key, font="SansB", size=9, color=INK):
    c.setFillColor(color); c.setFont(font, size); c.drawString(x, y, text)
    link(c, key, x - 1, y - 3, x + pdfmetrics.stringWidth(text, font, size) + 1, y + size)

# ---------- cover
def cover(c):
    """The name in lowercase, set on a grid of whole square cells (the frame is the outermost line): one letter per cell
    (the monospaced advance is one cell), the baselines on grid lines two rows apart; the root square, as the full stop, in
    a cell of its own. In the same rhythm, every other row: the subtitle, then the seven steps of the scale stacked in
    thirds, one per cell. The edition on the lowest lines. Everything starts one cell inside the frame."""
    g = (W - 2 * M) / 12; rows = int((H - 2 * M) / g); y0 = (H - rows * g) / 2; y1 = y0 + rows * g   # whole cells, centred
    c.setStrokeColor(COVER_GRID); c.setLineWidth(0.5)
    c.rect(M, y0, W - 2 * M, y1 - y0, stroke=1, fill=0)                     # the frame, the outermost lines of the grid
    for k in range(1, 12): c.line(M + k * g, y0, M + k * g, y1)
    for k in range(1, rows): c.line(M, y0 + k * g, W - M, y0 + k * g)
    line = lambda k: y1 - (k + 1) * g                                    # the k-th line from the top, the frame not counted; the first column starts at x0
    x0 = M + g
    upm, _xh, gl = font_metrics("bold"); size = g * upm / gl["h"][0]; words = WORDMARK.split(" ")
    c.setFillColor(INK); c.setFont("SansB", size)
    for k, w in enumerate(words): c.drawString(x0, line(2 + 2 * k), w)
    yl = line(2 * len(words)); s = size * 0.2
    c.setFillColor(COL["d1"][0]); c.roundRect(x0 + len(words[-1]) * g + (g - s) / 2, yl, s, s, s * 0.14, stroke=0, fill=1)
    sub = 2 + 2 * len(words)                                             # every other row, as the name: the subtitle, then the steps
    c.setFillColor(MUTED); c.setFont("Sans", 16); c.drawString(x0, line(sub), SUBTITLE.lower())
    for k, deg in enumerate(("1", "3", "5", "7", "9", "11", "13")): dot(c, x0 + (k + 0.5) * g, line(sub + 1.5), g * 0.38, deg)
    c.setFillColor(MUTED); c.setFont("Sans", 10); c.drawString(x0, y0 + 2 * g, "Scale degrees · note names · fingers · published sources")
    edition(c, x0, y0 + g, 10)

# ---------- pictures for the website: the card shown with shared links, and the home-screen icon
def site_pictures(folder):
    """share.png (1200 × 630): the cover's name, set on its grid of square cells framed by half cells, with the subtitle,
    the steps and the address beside it; apple-touch-icon.png (180 × 180): the logo. Drawn with the book's own code,
    then turned into PNG next to the PDF; build_site.py puts them on the site."""
    import pypdfium2
    path = os.path.join(folder, "pictures.pdf")
    c = Canvas(path, pagesize=(1200, 630), initialFontName="Sans")
    c.setFillColor(white); c.rect(0, 0, 1200, 630, stroke=0, fill=1)
    m, g = 30, 57; cols, rows = 20, 10                                   # 1140 × 570 inside a 30 pt margin
    c.setStrokeColor(COVER_GRID); c.setLineWidth(1.2); c.rect(m, m, cols * g, rows * g, stroke=1, fill=0)
    for k in range(cols): c.line(m + (k + 0.5) * g, m, m + (k + 0.5) * g, m + rows * g)
    for k in range(rows): c.line(m, m + (k + 0.5) * g, m + cols * g, m + (k + 0.5) * g)
    line = lambda k: 630 - m - (k + 0.5) * g; x0 = m + g / 2; x1 = x0 + 8 * g
    upm, _xh, gl = font_metrics("bold"); size = g * upm / gl["h"][0]; words = WORDMARK.split(" ")
    c.setFillColor(INK); c.setFont("SansB", size)
    for k, w in enumerate(words): c.drawString(x0, line(3 + 2 * k), w)
    s = size * 0.2; c.setFillColor(COL["d1"][0]); c.roundRect(x0 + len(words[-1]) * g + (g - s) / 2, line(1 + 2 * len(words)), s, s, s * 0.14, stroke=0, fill=1)
    c.setFillColor(MUTED); c.setFont("Sans", 30); c.drawString(x1, line(3), SUBTITLE.lower())
    for k, deg in enumerate(("1", "3", "5", "7", "9", "11", "13")): dot(c, x1 + (k + 0.5) * g, line(4.5), g * 0.38, deg)
    c.setFillColor(LINK); c.setFont("Sans", 24); c.drawString(x1, line(7), SITE.removeprefix("https://").rstrip("/"))
    c.showPage()
    k = 180 / 32; c.setPageSize((180, 180)); c.setFillColor(white); c.rect(0, 0, 180, 180, stroke=0, fill=1)   # the logo, as in build_site.logo()
    c.setStrokeColor(HexColor(DESIGN["colors"]["logo_grid"])); c.setLineWidth(1.5)
    for v in (2.5, 11.5, 20.5, 29.5): c.line(v * k, 2.5 * k, v * k, 29.5 * k); c.line(2.5 * k, v * k, 29.5 * k, v * k)
    c.setFillColor(COL["d1"][0]); c.roundRect(3.7 * k, (32 - 12.7 - 6.6) * k, 6.6 * k, 6.6 * k, 0.92 * k, stroke=0, fill=1)
    for cx, d in ((16, "d3"), (25, "d5")): c.setFillColor(COL[d][0]); c.circle(cx * k, 16 * k, 3.3 * k, stroke=0, fill=1)
    c.showPage(); c.save()
    doc = pypdfium2.PdfDocument(path)
    for i, name in enumerate(("share.png", "apple-touch-icon.png")): doc[i].render(scale=1).to_pil().convert("RGB").save(os.path.join(folder, name))
    doc.close(); os.remove(path)

# ---------- contents
def contents(c):
    c.bookmarkPage("contents"); c.addOutlineEntry("Contents", "contents", 0)
    c.setFillColor(INK); c.setFont("SansB", 26); c.drawString(M, H - M - 26, "Contents")
    pages = "; ".join(title[:1].lower() + title[1:] for title, _g in GROUPS)
    y = para(c, f"Every note in every diagram is labelled with its role in the chord, the note names are given under each formula, and a letter under each string shows which finger to use. Each root note has {NG} pages: {pages}. Everything below is clickable.", M, H - M - 56, size=9.5)
    y -= 22
    toc = [(title, k, PAGE[k]) for title, k in (("Two diagrams, explained", "start"), ("How to read the diagrams", "howto"), ("The five CAGED shapes", "caged"),
           ("Chord types and formulas", "types"), ("Chords in major keys", "keys"), ("Chords in minor keys", "minorkeys"),
           ("Slash chords", "slash"), ("Index by chord type", "index"))] + [("How this book was checked", "about", ABOUT_PAGE)]
    for title, key, page in toc:
        c.setFillColor(LINK); c.setFont("Sans", 10.5); c.drawString(M, y, title)
        c.setFillColor(MUTED); c.drawRightString(W - M, y, str(page))
        c.setStrokeColor(LINE); c.setDash(1, 2); c.setLineWidth(0.5)
        c.line(M + pdfmetrics.stringWidth(title, "Sans", 10.5) + 6, y + 2, W - M - 16, y + 2); c.setDash()
        link(c, key, M - 2, y - 4, W - M + 2, y + 11); y -= 15.5
    y -= 12
    c.setFillColor(INK); c.setFont("SansB", 11); c.drawString(M, y, "Chords by root"); y -= 6
    y = para(c, "Each black key has two names: C♯ is the same note as D♭. Both names are shown in the right-hand column.", M, y - 8, size=8.5) - 2
    ROWS = [(0, 1), (2, 3), (4, None), (5, 6), (7, 8), (9, 10), (11, None)]
    colw = (W - 2 * M) / 2; LS = 10.2; cellh = 10 + LS * NG; gap = 4
    c.setFillColor(MUTED); c.setFont("SansB", 7.5)
    for k, head in enumerate(["NATURAL", "SHARP ♯ / FLAT ♭"]): c.drawString(M + k * colw + 4, y - 4, head)
    y -= 10
    for row, (nat, sh) in enumerate(ROWS):
        yt = y - row * (cellh + gap)
        for col, r in enumerate((nat, sh)):
            if r is None: continue
            x = M + col * colw
            c.setFillColor(CARD); c.roundRect(x, yt - cellh, colw - 8, cellh, 6, stroke=0, fill=1)
            c.setFillColor(INK); c.setFont("SansB", 18); c.drawString(x + 12, yt - 28, both_names(r))
            link(c, f"r{r}g0", x, yt - cellh, x + 112, yt)
            for k in range(NG):
                ty = yt - 11 - k * LS
                c.setFillColor(LINK); c.setFont("Sans", 8.5); c.drawString(x + 120, ty, GROUP_SHORT[k])
                c.setFillColor(MUTED); c.drawRightString(x + colw - 20, ty, str(ROOT_PAGE(r, k)))
                link(c, f"r{r}g{k}", x + 118, ty - 3, x + colw - 10, ty + 9)
    colophon(c)
    footer(c, PAGE["contents"], show_legend=False)

def url_text(c, x, y, txt, url, size):
    """A link in running text; returns the x after it."""
    c.setFillColor(LINK); c.setFont("Sans", size); c.drawString(x, y, txt)
    w = pdfmetrics.stringWidth(txt, "Sans", size)
    c.linkURL(url, (x - 1, y - 3, x + w + 1, y + size), relative=0, thickness=0)
    return x + w

def corrections(c, x, y, size):
    """Where to report a mistake: the repository's issues."""
    if not REPO: return
    lead = "Corrections:"
    c.setFillColor(MUTED); c.setFont("Sans", size); c.drawString(x, y, lead)
    url_text(c, x + pdfmetrics.stringWidth(lead, "Sans", size) + 5, y, REPO + "/issues", GITHUB + "/issues", size)

def edition(c, x, y, size):
    """'Version 1.0 · October 2026 · built from github.com/…': the edition, and the repository it is built from
    (on a second line when one line is too long). Returns the y of the last line."""
    txt = f"Version {VERSION} · {DATE}"
    c.setFillColor(INK); c.setFont("SansB", size); c.drawString(x, y, txt)
    if REPO:
        lead = " · built from "
        if x + pdfmetrics.stringWidth(txt + lead + REPO, "Sans", size) > W - M:
            lead, y = "Built from ", y - size * 1.45
        else:
            x += pdfmetrics.stringWidth(txt, "SansB", size)
        c.setFillColor(MUTED); c.setFont("Sans", size); c.drawString(x, y, lead)
        url_text(c, x + pdfmetrics.stringWidth(lead, "Sans", size), y, REPO, GITHUB, size)
    return y

def colophon(c):
    y = M + 34
    c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, y + 14, W - M, y + 14)
    edition(c, M, y, 8.5)
    lic = "CC BY 4.0: free to use, share and adapt, with credit to the author."
    c.setFillColor(MUTED); c.setFont("Sans", 8); c.drawString(M, y - 13, lic)
    url = "creativecommons.org/licenses/by/4.0"
    x = M + pdfmetrics.stringWidth(lic, "Sans", 8) + 5
    c.setFillColor(LINK); c.drawString(x, y - 13, url)
    c.linkURL("https://creativecommons.org/licenses/by/4.0/", (x - 1, y - 16, x + pdfmetrics.stringWidth(url, "Sans", 8) + 1, y - 4), relative=0, thickness=0)
    corrections(c, M, y - 26, 8)

# ---------- start here
ROW1 = 94                            # height of a row of "Common chords"
def marker(c, n, mx, my, tx=None, ty=None, stop=0):
    if tx is not None:
        dx, dy = tx - mx, ty - my; d = (dx * dx + dy * dy) ** 0.5
        if d > 7 + stop:
            c.setStrokeColor(INK); c.setLineWidth(0.6)
            c.line(mx + dx / d * 6.5, my + dy / d * 6.5, tx - dx / d * stop, ty - dy / d * stop)
    c.setFillColor(INK); c.circle(mx, my, 6, stroke=0, fill=1)
    c.setFillColor(white); c.setFont("SansB", 7.5); c.drawCentredString(mx, my - 2.7, str(n))

def start_here(c):
    page_title(c, "Two diagrams, explained", "start")
    y = para(c, "Every mark in a diagram, on two examples: an open chord and a barre chord. Every other diagram in this book is drawn the same way.", M, H - M - 46, size=9.5)
    s = 1.8; top = y - 72
    # left: C major, open position
    tC, bC = find(0, ""); xL = M + 62
    c.setFillColor(INK); c.setFont("SansB", 12); c.drawString(M, y - 18, "C major, open position")
    label_line(c, xL + 2.5 * SP * s, top + 40, tC, bC, size=9)
    g = diagram(c, xL, top, tC, bC, s)
    xs, ry = g["xs"], g["row_y"]
    marker(c, 1, xs[0] - 26, g["top"], xs[0] - 1, g["top"])
    marker(c, 2, xs[0] - 26, g["oy"], xs[0], g["oy"], stop=6)
    marker(c, 3, xs[0] - 26, ry(3), xs[1], ry(3), stop=g["r"] + 1)
    marker(c, 4, xs[5] + 26, ry(2), xs[2], ry(2), stop=g["r"] + 1)
    marker(c, 5, xs[5] + 26, g["oy"], xs[5], g["oy"], stop=g["r"] + 1)
    marker(c, 6, xs[5] + 26, g["oy"] + 20, xs[3], g["oy"], stop=g["r"] + 1)
    marker(c, 7, xs[5] + 26, g["fy"] + 3, xs[5] + 8, g["fy"] + 3)
    # right: B minor, barre
    tB, bB = find(11, "m", "x24432"); xR = M + 330
    c.setFillColor(INK); c.setFont("SansB", 12); c.drawString(M + 272, y - 18, "B minor, barre chord")
    lx = label_line(c, xR + 2.5 * SP * s, top + 40, tB, bB, size=9)
    h = diagram(c, xR, top, tB, bB, s)
    xs2, ry2 = h["xs"], h["row_y"]
    marker(c, 8, xs2[0] - 40, ry2(0), xs2[0] - h["r"] - 13, ry2(0))
    marker(c, 9, xs2[5] + 26, ry2(0), xs2[5] + h["r"] + 3, ry2(0))
    marker(c, 10, xs2[5] + 26, ry2(1), xs2[4], ry2(1), stop=h["r"] + 1)
    marker(c, 11, xs2[5] + 26, h["fy"] + 3, xs2[5] + 8, h["fy"] + 3)
    marker(c, 12, lx - 30, top + 43, lx - 3, top + 43)
    y = min(g["fy"], h["fy"]) - 26
    keyL = ["Nut: the thick line is the end of the neck (open position).", "× = do not play this string.",
            "Root, drawn as a square: here C on the 5th string, fret 3.", "Third: E, the note that makes the chord major.",
            "Open string that sounds: a circle above the nut.", "Fifth: G, the lightest dot.",
            "Finger letters: I\u00a0index, M\u00a0middle, R\u00a0ring, L\u00a0little."]
    keyR = ["The number gives the fret of the first row: fret\u00a02.", "Barre: the pale blue bar is one finger lying flat.",
            "♭3: the minor third (D) makes the chord minor.", "The same letter I under several strings: one flat finger.",
            "The label names the shape (A shape) and the position."]
    ends = []
    for items, start, x in [(keyL, 1, M), (keyR, 8, M + 266)]:   # two columns of notes, each 240 wide
        yy = y
        for k, txt in enumerate(items):
            marker(c, start + k, x + 6, yy + 3)
            yy = para(c, txt, x + 17, yy, size=8.3, width=240) - 3
        ends.append(yy)
    y = min(ends) - 12
    c.setFillColor(INK); c.setFont("SansB", 12); c.drawString(M, y, "Common chords"); y -= 6
    cw = (W - 2 * M) / 4
    for k, (r, q, want) in enumerate(FIRST_TWELVE):
        t, b = find(r, q, want)
        col, row = k % 4, k // 4
        cx = M + cw * col + cw / 2; yt = y - row * ROW1
        name = NOTES[r] + q
        c.setFillColor(INK); c.setFont("SansB", 12); c.drawCentredString(cx, yt - 14, name)
        link(c, f"r{r}g0", cx - cw / 2 + 2, yt - ROW1 + 4, cx + cw / 2 - 2, yt)
        diagram(c, cx - 2.5 * SP + 4, yt - 38, t, b)
    footer(c, PAGE["start"])

# ---------- how to read, and the five CAGED shapes
def howto(c):
    page_title(c, "How to read the diagrams", "howto")
    y = bullets(c, [
        "Strings go left to right from the 6th (thick, low E) to the 1st (thin, high E). Horizontal lines are frets.",
        "A thick line at the top is the nut (open position). A number on the left is the fret of the first row.",
        "A dot above the nut is an open string (a square when it is the root). × means the string is not played.",
        "The pale blue bar is a barre: one finger lying flat across several strings. Notes under the barre also sound, so their degrees are labelled too.",
        "Every note shows its degree in the chord, in the colour of its step of the scale. Roots are dark squares and fifths the lightest dots; printed in black and white, the other notes share one grey and their numbers tell them apart.",
        "The label above each diagram names the CAGED shape the voicing comes from (E\u00a0shape, A\u00a0shape…) and where it sits on the neck. “E shape, 4 strings” is the E shape on the four thinnest strings (like F = xx3211). Voicings outside the five shapes are named by the string that carries the lowest root: Root on 6th, 5th or 4th.",
        "On the pages of black keys each chord also shows its second name, for example A♭m = G♯m. The note names under the formula follow the first name.",
        "Letters under each diagram show the left-hand finger for each string: I\u00a0index, M\u00a0middle, R\u00a0ring, L\u00a0little (pinky). Most guitar books use numbers instead (1\u00a0index, 2\u00a0middle, 3\u00a0ring, 4\u00a0little). Open and muted strings have no letter; the same letter on several strings means one finger lies flat across them, and a pale bar marks it.",
        "The fingerings shown are the usual ones. In a song you may pick another so that fingers can stay on notes shared with the next chord: in Wonderwall, for example, R and L stay on the 3rd fret through Em7, G, Dsus4, A7sus4 and Cadd9."],
        H - M - 46)
    y -= 6; y = legend(c, M, y, 4.8, 7); y -= 34
    c.bookmarkPage("caged"); c.addOutlineEntry("The five CAGED shapes", "caged", 0)
    c.setFillColor(INK); c.setFont("SansB", 18); c.drawString(M, y, "The five CAGED shapes"); y -= 20
    y = para(c, "Almost any chord can be played with one of five shapes, named after the open chords C, A, G, E and D. Slide an open shape up the neck, replace the nut with a barre or your index finger, and you get the same chord type on a new root. Along the neck the shapes link up in the order C → A → G → E → D and then repeat. For example, C major: open C shape, A shape at fret 3, G shape around frets 5–8, E shape at fret 8, D shape at fret 10, and the C shape again at fret 12.", M, y, size=9.5)
    y -= 44
    notes = {"C": "5th", "A": "5th", "G": "6th", "E": "6th", "D": "4th"}       # the string of the lowest root
    cw = (W - 2 * M) / 5; s = 1.0
    for k, (key, t) in enumerate(zip("CAGED", caged())):
        cx = M + cw * k + cw / 2
        c.setFillColor(INK); c.setFont("SansB", 11); c.drawCentredString(cx, y + 18, f"{key} shape")
        g = diagram(c, cx - 2.5 * SP * s, y - 6, t, 0, s)
        c.setFillColor(MUTED); c.setFont("Sans", 8); c.drawCentredString(cx, g["fy"] - 14, "lowest root")
        c.drawCentredString(cx, g["fy"] - 23, f"on the {notes[key]} string")
    y = g["fy"] - 50                     # below the two-line captions
    para(c, "Other chord types come from the same skeletons by changing one or two notes: lower the 3rd for minor, replace a root with the ♭7 for a 7th chord, swap the 3rd for a 2 or 4 for sus chords.", M, y, size=9.5)
    footer(c, PAGE["howto"], show_legend=False)        # the key is on the page itself

# ---------- chord types
def types(c):
    page_title(c, "Chord types and formulas", "types")
    y = H - M - 48
    c.setFillColor(MUTED); c.setFont("SansB", 8.5)
    c.drawString(M, y, "SYMBOL (C)"); c.drawString(M + 80, y, "NAME"); c.drawString(M + 215, y, "FORMULA"); c.drawString(M + 315, y, "WHAT IT IS")
    y -= 7; c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, y, W - M, y); y -= 15
    for gi, (gtitle, grp) in enumerate(GROUPS):
        c.setFillColor(INK); c.setFont("SansB", 10); c.drawString(M, y, gtitle)
        c.setFillColor(MUTED); c.setFont("Sans", 8); c.drawString(M + pdfmetrics.stringWidth(gtitle, "SansB", 10) + 8, y, f"page {gi + 1} of each root")
        y -= 15
        for q, name, formula, desc, _ in grp:
            chord_link_text(c, M, y, "C" + q, f"r0g{gi}", size=10)
            c.setFillColor(INK); c.setFont("Sans", 9); c.drawString(M + 80, y, name)
            c.setFont("SansB", 9); c.drawString(M + 215, y, formula)
            c.setFillColor(MUTED); c.setFont("Sans", 8.5)
            yy = y
            for ln in wrap(desc, "Sans", 8.5, W - 2 * M - 315): c.drawString(M + 315, yy, ln.replace("\u00a0", " ")); yy -= 10
            y = min(y - 14.5, yy - 4.5)
        y -= 6
    y -= 4
    c.setFillColor(INK); c.setFont("SansB", 11); c.drawString(M, y, "Naming notes"); y -= 15
    bullets(c, ["A plain “7” always means the minor 7th (♭7). The major 7th is written separately as maj7 (also M7 or Δ7).",
                "Degrees are counted against the major scale: 3 is the major 3rd, ♭3 the minor 3rd, 7 the major 7th, ♭7 the minor 7th.",
                "9 is the same note as 2, 11 the same as 4 and 13 the same as 6, an octave higher. “add9” adds the 9 without a 7th; “9” includes the ♭7.",
                "In a dim7 chord the 7th is a diminished 7th (°7, written as a double-flat 7 in theory). It sounds the same as the 6th.",
                "ø is the symbol for half-diminished (m7♭5); ° is diminished; + or aug is augmented."], y, size=9, gap=3)
    footer(c, PAGE["types"], show_legend=False)

# ---------- chords in each major and minor key
def keys_table(c, keys, numerals, minor, y):
    x0 = M + 44; cw = (W - M - x0) / 7
    c.setFillColor(MUTED); c.setFont("SansB", 8); c.drawString(M, y, "KEY")
    for i, num in enumerate(numerals): c.drawString(x0 + i * cw, y, num)
    y -= 6; c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, y, W - M, y); y -= 15
    for key in keys:
        c.setFillColor(INK); c.setFont("SansB", 12); c.drawString(M, y - 4, key + ("m" if minor else ""))
        for i, (num, root, pc, tq, sq) in enumerate(key_chords(key, minor)):
            x = x0 + i * cw
            chord_link_text(c, x, y, root + tq, f"r{pc}g{GI[tq]}", size=9.5)
            chord_link_text(c, x, y - 12, root + sq, f"r{pc}g{GI[sq]}", font="Sans", size=8, color=MUTED)
        y -= 21; c.setStrokeColor(CARD); c.setLineWidth(0.6); c.line(M, y + 5, W - M, y + 5); y -= 9
    return y - 6

def keys_page(c):
    page_title(c, "Chords in major keys", "keys")
    y = para(c, "Every major key uses the same pattern of chords, built on the seven notes of its scale: major, minor, minor, major, major, minor, diminished. Roman numerals give the step of the scale (capitals for major chords, lower case for minor, ° for diminished). Each cell shows the triad and, below it, the seventh chord. Every name links to its page.", M, H - M - 46, size=9.5) - 8
    y = keys_table(c, KEYS, NUMERALS, False, y)
    bullets(c, ["The vi chord is the relative minor: the minor key with the same notes (A minor for C major) uses the same chords, starting from vi. Minor keys are on the next page.",
                "C♯ major (7 sharps) is written here as D♭ major (5 flats). F♯ major has six sharps, so its vii chord is spelled E♯dim, the same sound as Fdim.",
                "The V chord is often played as a 7th chord (G7 in C) because it leads strongly back to I."], y, size=9, gap=3)
    footer(c, PAGE["keys"], show_legend=False)

def minor_keys_page(c):
    page_title(c, "Chords in minor keys", "minorkeys")
    y = para(c, "Every natural minor key uses the same pattern: minor, diminished, major, minor, minor, major, major. A minor key has the same notes and chords as its relative major, three semitones higher (A minor and C major), but its home chord is the minor i. Each cell shows the triad and, below it, the seventh chord. Every name links to its page.", M, H - M - 46, size=9.5) - 8
    y = keys_table(c, MINOR_KEYS, MINOR_NUMERALS, True, y)
    bullets(c, ["In practice the v chord is usually played major, often as a 7th chord (E or E7 in A minor, instead of Em), because a major V leads more strongly back to i. This comes from the harmonic minor scale, which raises the 7th note (G♯ in A minor).",
                "Each minor key here is the relative of the major key in the same row of the previous page: D♯ minor (six sharps) goes with F♯ major, so its ii chord is spelled E♯dim, the same sound as Fdim."], y, size=9, gap=3)
    footer(c, PAGE["minorkeys"], show_legend=False)

# ---------- slash chords
def slash_page(c):
    page_title(c, "Slash chords", "slash")
    y = para(c, "C/E means a C chord with E as the lowest note. The bass is usually another note of the chord (here the 3rd), which smooths the bass line between chords. When the bass is not in the chord (C/B), it is a passing note in a falling or rising bass line. Degrees in the diagrams are counted from the chord root, so the bass of D/F♯ shows 3.", M, H - M - 46, size=9.5) - 10
    cw = (W - 2 * M) / 3; ch = 124
    for k, sc in enumerate(SLASH_CHORDS):
        col, row = k % 3, k // 3
        cx = M + cw * col + cw / 2; yt = y - row * ch
        c.setFillColor(CARD); c.roundRect(cx - cw / 2 + 3, yt - ch + 6, cw - 6, ch - 6, 6, stroke=0, fill=1)
        chord_link_text(c, cx - pdfmetrics.stringWidth(sc["name"], "SansB", 12) / 2, yt - 16, sc["name"], f"r{sc['r']}g0", size=12)
        c.setFillColor(MUTED); c.setFont("Sans", 7.5); c.drawCentredString(cx, yt - 27, sc["bass"])
        diagram(c, cx - 2.5 * SP + 3, yt - 48, sc["t"], sc["base"])
    footer(c, PAGE["slash"])

# ---------- index by chord type
def index_page(c):
    page_title(c, "Index by chord type", "index")
    y = para(c, "Every chord in the book. Each name links to its page.", M, H - M - 44, size=9.5) - 6
    x0 = M + 44; cw = (W - M - x0) / 12
    size = min(7.6, min(7.6 * (cw - 6) / pdfmetrics.stringWidth(NOTES[r] + q, "Sans", 7.6) for _t, grp in GROUPS for q, *_x in grp for r in range(12)))
    c.setFillColor(MUTED); c.setFont("SansB", 8.5)
    c.drawString(M, y, "TYPE")
    for r in range(12): c.drawString(x0 + r * cw, y, NOTES[r])
    y -= 6; c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(M, y, W - M, y); y -= 16
    for gi, (gtitle, grp) in enumerate(GROUPS):                                  # one size for every row: the longest name fits
        c.setFillColor(INK); c.setFont("SansB", 10); c.drawString(M, y, gtitle); y -= 17
        for q, name, *_r in grp:
            c.setFillColor(INK); c.setFont("SansB", 8.5); c.drawString(M, y, q or "major")
            for r in range(12):
                chord_link_text(c, x0 + r * cw, y, NOTES[r] + q, f"r{r}g{gi}", font="Sans", size=size, color=LINK)
            y -= 17
        y -= 6
    footer(c, PAGE["index"], show_legend=False)

# ---------- root pages
def formula_sizes(n):
    """The sizes of a formula's degrees and note names on a root page: smaller for six degrees, so that they keep a gap."""
    return (7, 6.8) if n > 5 else (8, 7.5)

LABEL_W = 96; CELL_W = (W - 2 * M - LABEL_W) / 3; ROWS_TOP = H - M - 40   # the name column, three voicing cells, the top of the cards
ROWS_BOTTOM, CARD_PAD, CARD_GAP = M + 18, 6, 4      # the lowest a card may reach; the space under the finger letters; between cards
def cards(r, grp):
    """(y0, bottom) of each card on a root page. A card is as tall as its tallest diagram needs (from 2 pt above the label
    to the finger letters, 36 pt plus 11 pt per fret row) plus the same padding on every page; a page whose cards do not
    fit tightens padding and gaps alike. Space left over stays below the last card."""
    need = [36 + RH * max(max(4, max(v[0] for v in t["n"] if v) + (1 if b > 0 else 0)) for t, b in shown(r, temps)) for *_x, temps in grp]
    pad, gap = CARD_PAD, CARD_GAP
    over = 2 + sum(need) + pad * len(need) + gap * (len(need) - 1) - (ROWS_TOP - ROWS_BOTTOM)
    if over > 0:
        k = 1 - over / (pad * len(need) + gap * (len(need) - 1)); pad, gap = pad * k, gap * k
    out, y0 = [], ROWS_TOP
    for n in need:
        bottom = y0 - 2 - n - pad; out.append((y0, bottom)); y0 = bottom - gap + 2
    return out
def root_page(c, r, gi):
    gtitle, grp = GROUPS[gi]
    key = f"r{r}g{gi}"; page = ROOT_PAGE(r, gi)
    c.bookmarkPage(key); c.addOutlineEntry(gtitle, key, 1)
    back_link(c)
    c.setFillColor(INK); c.setFont("SansB", 26); c.drawString(M, H - M - 26, both_names(r))
    c.setFillColor(MUTED); c.setFont("Sans", 12)
    c.drawString(M + pdfmetrics.stringWidth(both_names(r), "SansB", 26) + 12, H - M - 22, gtitle)
    label_w, cell_w = LABEL_W, CELL_W
    alias_root = other_name(r)
    for (q, qname, formula, desc, temps), (y0, bottom) in zip(grp, cards(r, grp)):
        c.setFillColor(CARD); c.roundRect(M, bottom, W - 2 * M, y0 - 2 - bottom, 6, stroke=0, fill=1)
        name = NOTES[r] + q
        c.setFillColor(INK); c.setFont("SansB", 15 if len(name) <= 5 else 13); c.drawString(M + 10, y0 - 24, name)
        ny = y0 - 38
        if alias_root:
            c.setFillColor(MUTED); c.setFont("SansB", 8); c.drawString(M + 10, y0 - 35, f"= {alias_root}{q}")
            ny = y0 - 47
        tname = qname.replace(" (", "\u00a0(")                                   # "(ø)" stays with its word
        longest = max(pdfmetrics.stringWidth(w.replace("\u00a0", " "), "Sans", 7.5) for w in tname.split(" "))
        yy = para(c, tname, M + 10, ny, size=min(7.5, 7.5 * (label_w - 14) / longest), width=label_w - 14, lead=9.5)   # a word wider than the column: smaller
        degs = formula.split()
        step = min(17, (label_w - 14) / len(degs)); dsize, nsize = formula_sizes(len(degs))
        for k, d in enumerate(degs):
            x = M + 10 + k * step
            c.setFillColor(INK); c.setFont("SansB", dsize); c.drawString(x, yy - 2, d)
            c.setFillColor(MUTED); c.setFont("Sans", nsize); note_text(c, x, yy - 12, spell(r, d))
        for k, (t, base) in enumerate(shown(r, temps)):
            cx = M + label_w + cell_w * k + cell_w / 2
            label_line(c, cx, y0 - 12, t, base, width=cell_w - 16)      # at least 8 pt from the card's edge
            diagram(c, cx - 2.5 * SP + 4, y0 - 28, t, base)
    footer(c, page)

# ---------- last page: how it was checked
def about(c):
    page_title(c, "How this book was checked", "about")
    n, ncites, names, short = provenance()
    y = bullets(c, [
        "Every voicing in this book comes from published sources. It is shown only if at least two independent sources list it: chord libraries, lessons and books by guitar teachers and publishers. Sites that copy one another count as one source (JamPlay and fachords; Guitar World, Guitar Player and MusicRadar, which share a publisher). The open-source database chords-db, and 8notes and akordy.kytary.cz, which reproduce it, are cited but never counted as confirmation.",
        "Every finger letter is the fingering that most of those sources give for that voicing. Where they are evenly split, JustinGuitar’s fingering is used, then Fender’s, then the one an earlier draft of this book printed, then the one chords-db gives.",
        "Each row shows the open-position voicings first, then the movable shapes, lower on the neck first. Of two voicings that differ only by one muted string, the better-sourced one is shown." + (f" {short} chords show fewer than three voicings, because no other voicing of them is listed by two independent sources." if short else ""),
        "Every voicing was also checked by computer: each degree number matches the interval from the root, the root is the lowest note (in slash chords, the named bass), there are no wrong notes, the required notes are present, and the fingering can be played (each finger on one fret, no crossed fingers, at most four frets). The note sets were checked independently with the open-source chord library pychord, and the note names under each formula were compared with its spelling.",
        f"The {n:,} diagrams rest on {ncites:,} citations; each one, with a link to its page, is listed with its voicing in the book’s data files (data/evidence/*.toml). Sources: " + "; ".join(n.replace(" ", "\u00a0") for n in names) + "; and pychord (github.com/yuma-m/pychord) for the note check."],
        H - M - 46, size=9.5, gap=5)
    y -= 10
    y = edition(c, M, y, 9)
    lic = "Licensed under CC BY 4.0:"; url = "creativecommons.org/licenses/by/4.0"
    c.setFillColor(MUTED); c.setFont("Sans", 8.5); c.drawString(M, y - 13, lic)
    url_text(c, M + pdfmetrics.stringWidth(lic, "Sans", 8.5) + 5, y - 13, url, "https://" + url + "/", 8.5)
    corrections(c, M, y - 26, 8.5)
    footer(c, ABOUT_PAGE, show_legend=False)

if __name__ == "__main__":
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    c = Canvas(OUT, pagesize=A4, initialFontName="Sans", lang="en-GB")
    c.setTitle(TITLE); c.setAuthor(AUTHOR); c.setCreator(f"{TITLE} {VERSION}")
    c.setSubject(f"{SUBTITLE}: chords with scale degrees, note names, CAGED shapes and fingerings. Version {VERSION}, {DATE}. Licence: CC BY 4.0")
    c.setKeywords(["guitar", "chords", "CAGED", "intervals", "scale degrees", "fingering"])
    c.showOutline()
    cover(c); c.showPage()
    contents(c); c.showPage()
    start_here(c); c.showPage()
    howto(c); c.showPage()
    types(c); c.showPage()
    keys_page(c); c.showPage()
    minor_keys_page(c); c.showPage()
    slash_page(c); c.showPage()
    index_page(c); c.showPage()
    for r in range(12):
        c.bookmarkPage(f"r{r}"); c.addOutlineEntry(f"{both_names(r)} chords", f"r{r}", 0)
        for gi in range(NG):
            root_page(c, r, gi); c.showPage()
    about(c); c.showPage()
    c.save()
    site_pictures(os.path.dirname(os.path.abspath(OUT)))
    print("ok", OUT)
