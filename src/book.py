# What the book (build_en.py) and the website (build_site.py) share: the title and edition (data/book.toml),
# the design tokens (src/design.toml), and the numbers on "How this reference was checked".
import os, tomllib
from urllib.parse import urlparse
import data, evidence
from chords import ALL, SLASH_CHORDS, shown, voicings, frets, ROW
from theory import NOTES

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
TITLE, SUBTITLE = data.BOOK["title"], data.BOOK["subtitle"]
WORDMARK = TITLE.lower()     # the name as the cover and the site set it: lowercase, as the Bauhaus printed
VERSION, DATE = data.BOOK["version"], data.BOOK["date"]
AUTHOR = data.BOOK["author"]
GITHUB = data.BOOK["github"] or None          # the repository: source, corrections and suggestions
REPO = GITHUB.removeprefix("https://") if GITHUB else None
SITE = data.BOOK["site"].rstrip("/") + "/"     # the published website, with a final slash
PDF_NAME = TITLE + ".pdf"
SLUG = TITLE.lower().replace(" ", "-")         # haus-of-chords: file names of the downloads

# design tokens: fonts and colours (src/design.toml)
with open(os.path.join(HERE, "design.toml"), "rb") as _fh:
    DESIGN = tomllib.load(_fh)

# a chord diagram, in points (the book) or SVG units (the site): string spacing, fret height, dot radius, the row of open
# strings above the nut; the degree in a dot is 7.2 high, or 6.3 when it has two characters
SP, RH, R, OPEN_DY = 15, 11, 5.2, 7.5
LABEL_K = (7.2 / R, 6.3 / R)
def font_path(k): return os.path.join(PROJ, DESIGN["fonts"][k])

def font_metrics(k):
    """Units per em, x-height, and the advance and left side bearing of each ASCII glyph of a design font: for setting
    the cover's name on its grid (the x-height one cell, the first stem of a line on a grid line)."""
    from fontTools.ttLib import TTFont
    f = TTFont(font_path(k)); hm = f["hmtx"]
    return f["head"].unitsPerEm, f["OS/2"].sxHeight, {chr(u): hm[g] for u, g in f.getBestCmap().items() if u < 128}

def provenance():
    """Numbers for the last page, worked out from the sources in data/ and the voicings the book shows:
    (voicings shown, citations behind them, publisher names, rows with fewer than three voicings)."""
    cites, used = set(), set()
    rows = [(r, q, t, b) for q, _n, _f, _d, temps in ALL for r in range(12) for t, b in shown(r, temps)]
    rows += [(s["r"], "slash", s["t"], s["base"]) for s in SLASH_CHORDS]
    for r, q, t, b in rows:
        v, _f, cs = evidence.support(q, frets(t, b), t["fing"])
        used |= v
        cites |= {(c["by"], c.get("url"), c.get("chord"), c.get("frets")) for c in cs}
    short = sum(1 for q, *_x, temps in ALL for r in range(12) if len(voicings(r, temps)) < ROW)
    names = []
    for k, s in sorted(evidence.SOURCES.items(), key=lambda kv: kv[1]["name"].lower()):
        cl = evidence.cluster({"by": k})
        if cl in used or not evidence.confirms(cl):       # every publisher behind a shown voicing, and chords-db with its copies
            where = "github.com/tombatossals/chords-db" if k == "chords-db" else urlparse(s["site"]).hostname.removeprefix("www.")
            names.append(s["name"] if s["name"].lower() == where else f"{s['name']} ({where})")
    return len(rows), len(cites), names, short
