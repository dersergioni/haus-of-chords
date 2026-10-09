# The chords of the book, worked out from data/: chord types grouped as the pages of each root, every voicing as a template
# (degrees, offsets and barre from the frets), the order of the voicings in a row, their labels, and the slash chords.
import data, evidence
from theory import OPEN, SEMI, SLASH_DEGREE, pc_of

CAGED = {0: "C", 9: "A", 7: "G", 4: "E", 2: "D"}   # root of an open chord -> the shape named after it
LABEL = {"E": "E shape", "A": "A shape", "D": "D shape", "C": "C shape", "G": "G shape", "E4": "E shape, 4 strings"}

def _major(semi):
    """CAGED letter -> the (string, fret) of every note a given number of semitones above the root in that open major
    chord: 0 the roots (C x32010: 5th string fret 3, 2nd fret 1), 4 the thirds (C x32010: 4th string fret 2, 1st open)."""
    out = {}
    for v in next(ty for ty in data.TYPES.values() if ty["symbol"] == "")["voicings"]:
        fr = v["fr"]
        if 0 not in fr: continue
        bass = next(i for i in range(6) if fr[i] is not None); root = (OPEN[bass] + fr[bass]) % 12
        if root in CAGED and CAGED[root] not in out:
            out[CAGED[root]] = {(i, f) for i, f in enumerate(fr) if f is not None and (OPEN[i] + f - root) % 12 == semi}
    return out
MAJOR_ROOTS, MAJOR_THIRDS = _major(0), _major(4)

def shape_of(fr, opens, formula):
    """The CAGED shape of a voicing, worked out from its frets ("R" outside the five shapes).
    An open voicing of C, A, G, E or D is that shape. A movable shape is shape X when, slid down towards the nut until
    its root is X, it is part of an open voicing of X of the same chord type (opens: root -> frets of its open voicings).
    When two shapes fit, the one whose open voicing has its root on the same string wins, then the shorter slide.
    Otherwise it is shape X when, slid down (or not at all), every root lies where the open major chord X has one, its bass
    among them; its lowest third lies where X has its third (a minor third one fret lower); and every note lies between one
    fret behind the nut and the third fret (the shorter slide wins). The third tells the shapes apart: G has it on the 5th
    string, E on the 3rd.
    An E shape with its root on the 4th string is "E4", the E shape on the four highest strings."""
    bass = next(i for i in range(6) if fr[i] is not None)
    x = None
    if 0 in fr:
        x = CAGED.get((OPEN[bass] + fr[bass]) % 12)
    else:
        fits = []                                       # (root on another string, slide, shape)
        for k in range(min(f for f in fr if f is not None) + 1):
            s = [None if f is None else f - k for f in fr]
            root = (OPEN[bass] + s[bass]) % 12
            if root not in CAGED: continue
            match = [o for o in opens.get(root, ()) if all(a is None or a == b for a, b in zip(s, o))]
            if match: fits.append((all(next(i for i in range(6) if o[i] is not None) != bass for o in match), k, CAGED[root]))
        if not fits:                                    # the shape of the open major chord whose roots and third it shares
            root = (OPEN[bass] + fr[bass]) % 12
            deg = {SEMI[d]: d for d in formula.split()}
            at_deg = [(i, f, deg[(OPEN[i] + f - root) % 12]) for i, f in enumerate(fr) if f is not None]
            roots = [(i, f) for i, f, d in at_deg if d == "1"]
            third = next(((i, f + (d == "♭3")) for i, f, d in at_deg if d in ("3", "♭3")), None)
            for shape, at in MAJOR_ROOTS.items():
                for i, p in at:
                    k = fr[bass] - p
                    if i != bass or k < 0: continue
                    if (all((j, f - k) in at for j, f in roots) and all(f is None or -1 <= f - k <= 3 for f in fr)
                            and (third is None or (third[0], third[1] - k) in MAJOR_THIRDS[shape])): fits.append((False, k, shape))
        if fits: x = min(fits)[2]
    if x == "E" and bass == 2: x = "E4"
    return x or "R"

def opens_of(ty):
    """Root -> the frets of every open voicing of a chord type."""
    out = {}
    for v in ty["voicings"]:
        if 0 in v["fr"]:
            bass = next(i for i in range(6) if v["fr"][i] is not None)
            out.setdefault((OPEN[bass] + v["fr"][bass]) % 12, []).append(v["fr"])
    return out

def barre(fr, fg, lo):
    """(first, last) string of the index finger lying flat at the lowest fret of a movable shape, or None: a barre chord
    (the position label "barre, fret N")."""
    idx = [i for i in range(6) if fr[i] == lo and fg[i] == "I"]
    return (idx[0], idx[-1]) if len(idx) >= 2 else None

def bars(n, fg):
    """Every barre to draw: a finger lying flat on two or more strings at one fret, as (first string, last string, row
    offset), wherever it is (open voicings, slash chords and any finger included)."""
    at = {}
    for i, (v, f) in enumerate(zip(n, fg)):
        if v and f: at.setdefault((f, v[0]), []).append(i)
    return sorted((s[0], s[-1], o) for (_f, o), s in at.items() if len(s) >= 2)

def template(v, q, formula, opens):
    """A voicing with its degrees, offsets, barre, CAGED shape and number of sources worked out from the data.
    Open voicings belong to their own root and are drawn from the nut; movable ones start at their lowest fret."""
    fr, fg = v["fr"], v["fg"]
    deg = {SEMI[d]: d for d in formula.split()}
    bass = next(i for i in range(6) if fr[i] is not None)
    root = (OPEN[bass] + fr[bass]) % 12
    lab = [None if f is None else deg[(OPEN[i] + f - root) % 12] for i, f in enumerate(fr)]
    pub, fpub, _c = evidence.support(q, fr, fg)        # the same in every key
    marks = {}
    for m in ("pin", "skip"):                             # the author's marks: the roots they apply to
        x = v.get(m)
        marks[m] = frozenset() if not x else frozenset([root]) if 0 in fr else frozenset(range(12)) if isinstance(x, str) else frozenset(pc_of(n) for n in x["roots"])
    t = dict(shape=shape_of(fr, opens, formula), fing=fg, pin=marks["pin"], skip=marks["skip"],
             nsrc=len(pub), nfing=len(fpub))            # independent publishers of the voicing, and of its fingering
    if 0 in fr:
        t.update(n=[None if f is None else (f, d) for f, d in zip(fr, lab)], only=root, bar=None)
    else:
        lo = min(f for f in fr if f is not None)
        t.update(n=[None if f is None else (f - lo, d) for f, d in zip(fr, lab)], only=None, bar=barre(fr, fg, lo))
    t["bars"] = bars(t["n"], fg)
    return t

def tag(t):
    """CAGED shape name, or (outside the five shapes) the string that carries the lowest root."""
    if t["shape"] in LABEL: return LABEL[t["shape"]]
    bass = next(i for i, v in enumerate(t["n"]) if v)
    return f"Root on {6 - bass}th"   # bass is always on the 6th, 5th or 4th string

def position(t, base):
    """Where the voicing sits: open, barre at a fret, or from a fret."""
    if base == 0:
        return "open" if any(v and v[0] == 0 for v in t["n"]) else "first position"
    return f"barre, fret {base}" if t["bar"] else f"from fret {base}"

# ---- chord types, grouped as the pages of each root (data/book.toml); each row: symbol, name, formula, what it is, voicings
def display_name(ty):
    """'diminished (°)': the name, with the type's other symbol when it has one."""
    return ty["name"] + (f" ({ty['also']})" if ty.get("also") else "")

# every published voicing of each type, the book's candidates and the spares (for the site); a candidate that fewer than
# two independent publishers list (and that is not kept by the author's decision) is left out of the book automatically
EVERY = {ty["symbol"]: [template(v, ty["symbol"], ty["formula"], opens) for v in ty["voicings"]]
         for ty in data.TYPES.values() for opens in [opens_of(ty)]}
GROUPS = [(page["title"], [(ty["symbol"], display_name(ty), ty["formula"], ty["about"], [t for t in EVERY[ty["symbol"]] if t["nsrc"] >= 2])
                           for ty in (data.TYPES[n] for n in page["types"])])
          for page in data.PAGES]
GROUP_SHORT = [page["short"] for page in data.PAGES]
ALL = [row for _t, g in GROUPS for row in g]
FILE = {ty["symbol"]: name for name, ty in data.TYPES.items()}     # chord symbol -> data file name (also the URL slug)
OPTIONAL = {ty["symbol"]: tuple(ty["optional"]) for ty in data.TYPES.values()}   # degrees a voicing may leave out

def ref(t):
    """Pitch class of the root when the shape's first row sits at the nut."""
    for i, v in enumerate(t["n"]):
        if v and v[1] == "1":
            return (OPEN[i] + v[0]) % 12

def frets(t, base):
    return [None if v is None else base + v[0] for v in t["n"]]

def _score(t): return (t["nsrc"], t["nfing"])   # how well sourced: publishers of the voicing, then of its fingering

def voicings(root, templates, near=True, pinned=lambda t: False):
    """The voicings of one chord in the order the book shows them: open voicings first (in the order of their data file),
    then movable shapes lower on the neck first; at the same fret, the one more sources publish, then the one whose
    fingering more sources give. Of two voicings that differ only by one muted string, the better-sourced one is kept
    (near=False keeps both, for the website)."""
    out = []
    for t in templates:
        if t["only"] is not None:
            if t["only"] != root: continue
            base = 0
        else:
            base = base_of(t, root)
            if base + max(v[0] for v in t["n"] if v) > 15: continue
        out.append((t, base))
    out.sort(key=lambda v: (v[1], -v[0]["nsrc"], -v[0]["nfing"]) if v[1] else (0, 0, 0))   # stable: open voicings keep their order
    if not near: return out
    kept = []
    for v in out:
        f = frets(*v)
        clash = [k for k in kept if near_dup(f, frets(*k))]
        if not clash: kept.append(v)
        elif pinned(v[0]) and not any(pinned(k[0]) for k in clash): kept = [k for k in kept if k not in clash] + [v]   # a pinned voicing wins
        elif not any(pinned(k[0]) for k in clash) and v[1] and all(k[1] for k in clash) and all(_score(v[0]) > _score(k[0]) for k in clash):
            kept = [k for k in kept if k not in clash] + [v]
    return sorted(kept, key=out.index)

def near_dup(a, b):
    """Two voicings (frets) that are the same, or differ only by one muted string."""
    d = [i for i in range(6) if a[i] != b[i]]
    return len(d) == 0 or (len(d) == 1 and (a[d[0]] is None or b[d[0]] is None))

ROW = 3                              # voicings the book shows in each row
OPEN2 = 3                            # sources a second open voicing of a root needs
rel = lambda t: [None if v is None else v[0] for v in t["n"]]

def base_of(t, root):
    """The fret a movable shape starts at for a root (never 0: a movable shape is never turned into an open chord)."""
    return (root - ref(t)) % 12 or 12

def octave_copy(f, o):
    """f, slid down 12 frets, plays the same notes on the same strings as (part of) the open voicing o."""
    return all(x is None or (o[i] is not None and x - 12 == o[i]) for i, x in enumerate(f))

def shown(root, templates):
    """The three voicings of one chord in the book (templates: every voicing of the type with 2+ independent sources).
    "Better sourced": more independent sources, then more sources for the fingering.
    1. The open voicing of the root that most sources publish, and a second one that OPEN2+ sources publish (not one
       muted string away from the first).
    2. The movable shapes, one per shape (CAGED shape, or the root's string), its best-sourced voicing; the places
       left go to the shapes more sources publish; with as many sources, the one nearer the nut, then the one whose
       fingering more sources give. A voicing that, slid down 12 frets, plays
       part of an open voicing of the row is that voicing an octave up, and one muted string away from a voicing
       already taken is the same voicing: both are passed over.
    The author's marks come first: pin puts a voicing in, skip keeps it out. Shown: the open voicings in the order of
    the data file, then lower on the neck first."""
    pool = [t for t in templates if root not in t["skip"]]
    pin = [t for t in pool if root in t["pin"] and t["only"] in (None, root)]
    opens = sorted((t for t in pool if t["only"] == root), key=_score, reverse=True)
    take = [(t, 0) for t in opens[:1]]
    take += [(t, 0) for t in opens[1:2] if t["nsrc"] >= OPEN2 and not near_dup(frets(t, 0), frets(*take[0]))]
    take = [(t, base_of(t, root) if t["only"] is None else 0) for t in pin] + [v for v in take if not any(v[0] is t for t in pin)]
    rank = lambda t: (t["nsrc"], -base_of(t, root), t["nfing"])
    best = {}
    for t in sorted((t for t in pool if t["only"] is None), key=rank, reverse=True):
        if not any(near_dup(rel(t), rel(b)) for b in best.values()): best.setdefault(tag(t), t)
    for t in sorted(best.values(), key=rank, reverse=True):
        if len(take) >= ROW: break
        v = (t, base_of(t, root)); f = frets(*v)
        if any(v[0] is k[0] for k in take) or max(x for x in f if x is not None) > 15: continue
        if any(octave_copy(f, frets(*k)) for k in take if k[0]["only"] is not None) or any(near_dup(f, frets(*k)) for k in take): continue
        take.append(v)
    order = lambda v: (0, next(i for i, t in enumerate(templates) if t is v[0])) if v[0]["only"] is not None else (1, v[1], -v[0]["nsrc"])
    return sorted(take, key=order)[:max(ROW, len(pin))]

def find(r, q, want=None):
    """(template, base fret) of a chord's voicing: the first one, or the one with these frets ('x24432')."""
    temps = next(row[4] for row in ALL if row[0] == q)
    for t, b in voicings(r, temps):
        if want is None or data.fstr(frets(t, b)) == want: return t, b
    raise KeyError((r, q, want))

# twelve common chords (the book's page 3, the site's home page): (root, type, frets or None for the first voicing)
FIRST_TWELVE = [(4, "", None), (9, "", None), (2, "", None), (7, "", None), (0, "", None), (5, "", "xx3211"),
                (4, "m", None), (9, "m", None), (2, "m", None), (4, "7", None), (9, "7", None), (2, "7", None)]

def caged():
    """The five open major chords the CAGED shapes are named after, in C A G E D order."""
    major = next(row[4] for row in ALL if row[0] == "")
    return [next(t for t in major if t["only"] is not None and t["shape"] == k) for k in "CAGED"]

# ---- slash chords shown in the book (data/slash.toml, book = true)

def slash_chord(v):
    """Degrees are counted from the chord root, so the bass of D/F♯ shows 3. Drawn from the nut when it fits in 4 frets."""
    name = v["name"]
    chord, bass = name.split("/")
    q = "m" if chord.endswith("m") else ""
    r, b = pc_of(chord.rstrip("m")), pc_of(bass)
    fr, fg = v["fr"], v["fg"]
    fretted = [f for f in fr if f]
    base = 0 if 0 in fr or max(fretted) <= 4 else min(fretted)
    n = [None if f is None else ((f if base == 0 else f - base), SLASH_DEGREE[(OPEN[i] + f - r) % 12]) for i, f in enumerate(fr)]
    t = dict(shape="R", n=n, fing=fg, why=None, only=r, bar=barre(fr, fg, base) if base > 0 else None, bars=bars(n, fg))
    passing = (b - r) % 12 not in {0, 3 if q == "m" else 4, 7}     # the bass is not a note of the triad
    return dict(name=name, t=t, base=base, r=r, q=q, bass=f"{SLASH_DEGREE[(b - r) % 12]} in the bass" + (" (passing note)" if passing else ""))

SLASH_CHORDS = [slash_chord(v) for v in data.SLASH if v["book"]]
