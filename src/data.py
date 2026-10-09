# Reads the book's data (data/*.toml; the format is described in data/README.md): the book and its pages, publishers,
# chord types with their voicings, slash chords, and the published sources of every voicing (data/evidence/).
# check() returns everything wrong with the form of the data; audit_data.py prints it, and the builds refuse to run on it.
import os, re, tomllib
from theory import NOTES, OPEN, SEMI, SLASH_DEGREE, pc_of

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
VIA = {"browser", "reader", "image", "data", "archive", "copy"}   # how a page was read, when not from its text

def _load(*path):
    with open(os.path.join(ROOT, *path), "rb") as fh:
        return tomllib.load(fh)

# ---- the two notations: tokens in data/chords (one per string: x, 0, or fret + finger) and the usual frets string
_TOKEN = re.compile(r"x|0|([1-9]|1\d|2[0-4])([IMRL])")
def strings(s):
    """'x 3R 2M 0 1I 0' -> frets [None, 3, 2, 0, 1, 0] and fingers [None, 'R', 'M', None, 'I', None], 6th string first."""
    toks = s.split(" ") if isinstance(s, str) else []
    ms = [_TOKEN.fullmatch(t) for t in toks]
    if len(toks) != 6 or not all(ms): raise ValueError(f"strings {s!r} must be 6 tokens: x, 0, or a fret with a finger (3R)")
    return ([None if t == "x" else 0 if t == "0" else int(m.group(1)) for t, m in zip(toks, ms)],
            [m.group(2) if m.group(2) else None for m in ms])

def parse(frets):
    """'x(10)9(10)(11)x' -> [None, 10, 9, 10, 11, None] (6th string first)."""
    out = [None if x == "x" else int(a or b) for a, b, x in re.findall(r"\((\d+)\)|(\d)|(x)", frets)]
    if len(out) != 6 or "".join(re.findall(r"\(\d+\)|\d|x", frets)) != frets: raise ValueError(f"bad frets {frets!r}")
    return out

def fstr(fr):
    return "".join("x" if f is None else (str(f) if f < 10 else f"({f})") for f in fr)

def fgstr(fg):
    """[None, 'M', 'I', 'R', 'R', 'L'] -> '-MIRRL'."""
    return "".join(g or "-" for g in fg)

def key(fr):
    """Shapes without open strings match in any key (relative frets); open voicings match exactly."""
    if 0 in fr: return ("open", tuple(fr))
    lo = min(f for f in fr if f is not None)
    return ("movable", tuple(None if f is None else f - lo for f in fr))

# ---- loading: every voicing gets its frets, fingers and sources; malformed ones are left out and reported by check()
_P = []
def _voicing(v, where, evidence, ekey, fields):
    for k in sorted(set(v) - fields): _P.append(f"{where}: unknown field {k}")
    try: fr, fg = strings(v.get("strings"))
    except ValueError as e: _P.append(f"{where}: {e}"); return None
    out = dict(v, fr=fr, fg=fg, frets=fstr(fr), fingers=fgstr(fg))
    k = ekey(out)
    out["sources"] = evidence.pop(k, None)
    if out["sources"] is None: _P.append(f"{where}: no sources in the evidence file (key {k!r})"); out["sources"] = []
    return out

def _load_all():
    book = _load("book.toml")
    meta = {k: v for k, v in book.items() if k != "page"}
    types, slash = {}, []
    for p in book.get("page", []):
        for name in p.get("types", []):
            if not os.path.exists(os.path.join(ROOT, "chords", name + ".toml")): _P.append(f"data/book.toml: data/chords/{name}.toml does not exist"); continue
            t = _load("chords", name + ".toml")
            ev = _load("evidence", name + ".toml") if os.path.exists(os.path.join(ROOT, "evidence", name + ".toml")) else {}
            vs = [_voicing(v, f"data/chords/{name}.toml voicing {k + 1} ({v.get('strings')})", ev, lambda o: o["frets"], {"chord", "strings", "pin", "skip"})
                  for k, v in enumerate(t.get("voicings", []))]
            t["voicings"] = [v for v in vs if v]
            for k in ev: _P.append(f"data/evidence/{name}.toml: {k!r} is not a voicing of data/chords/{name}.toml")
            types[name] = t
    ev = _load("evidence", "slash.toml")
    for k, c in enumerate(_load("slash.toml").get("chords", [])):
        v = _voicing(c, f"data/slash.toml chord {k + 1} ({c.get('name')} {c.get('strings')})", ev, lambda o: f"{o.get('name')} {o['frets']}", {"name", "strings", "book"})
        if v: slash.append(v)
    for k in ev: _P.append(f"data/evidence/slash.toml: {k!r} is not a chord of data/slash.toml")
    return meta, book.get("page", []), types, slash

BOOK, PAGES, TYPES, SLASH = _load_all()      # the book's title and edition; its pages; chord types by file name; slash chords
SOURCES = _load("sources.toml")

def check():
    """Problems with the form of the data, as readable lines (empty when all is well)."""
    P = list(_P)
    for f in ("title", "subtitle", "version", "date", "author", "github", "site"):
        if not isinstance(BOOK.get(f), str): P.append(f"data/book.toml: {f} must be text in quotes")
    files = {f[:-5] for f in os.listdir(os.path.join(ROOT, "chords")) if f.endswith(".toml")}
    listed = [n for p in PAGES for n in p.get("types", [])]
    for p in PAGES:
        for f in ("title", "short"):
            if not isinstance(p.get(f), str): P.append(f"data/book.toml: a [[page]] has no {f}")
    for n in sorted(files - set(listed)): P.append(f"data/chords/{n}.toml is not listed in data/book.toml")
    for n in sorted({n for n in listed if listed.count(n) > 1}): P.append(f"{n} is listed twice in data/book.toml")
    for n in sorted({f[:-5] for f in os.listdir(os.path.join(ROOT, "evidence")) if f.endswith(".toml")} - files - {"slash"}):
        P.append(f"data/evidence/{n}.toml belongs to no chord type")
    for sid, s in SOURCES.items():
        for f in ("name", "site"):
            if not isinstance(s.get(f), str): P.append(f"data/sources.toml [{sid}]: missing {f}")
        seen, c = {sid}, s.get("counts_as")
        while c:
            if c not in SOURCES: P.append(f"data/sources.toml [{sid}]: counts_as {c} is unknown"); break
            if c in seen: P.append(f"data/sources.toml [{sid}]: counts_as goes round in a circle"); break
            seen.add(c); c = SOURCES[c].get("counts_as")
        if "confirms" in s and not isinstance(s["confirms"], bool): P.append(f"data/sources.toml [{sid}]: confirms must be true or false")
        if s.get("copies") and s["copies"] not in SOURCES: P.append(f"data/sources.toml [{sid}]: copies {s['copies']} is unknown")

    def voicing(where, v, chord_type):
        fr = v["fr"]
        bass = next((i for i in range(6) if fr[i] is not None), None)
        if bass is None: P.append(f"{where}: no notes"); return
        if chord_type and bass > 2: P.append(f"{where}: the lowest note must be on the 6th, 5th or 4th string")
        if chord_type and 0 not in fr:
            lo = min(f for f in fr if f is not None)
            if (OPEN[bass] + fr[bass]) % 12 != 0 or not 1 <= lo <= 12:
                P.append(f"{where}: a movable shape is written with its root on C, lowest fret 1 to 12")
        if not chord_type and not isinstance(v.get("book"), bool): P.append(f"{where}: book must be true or false")
        for mark in ("pin", "skip") if chord_type else ():        # the author's marks: a reason, or { roots = [...], why = "..." }
            m = v.get(mark)
            if m is None or isinstance(m, str) and m: continue
            if not (isinstance(m, dict) and set(m) == {"roots", "why"} and isinstance(m["why"], str) and m["why"] and isinstance(m["roots"], list) and m["roots"]):
                P.append(f"{where}: {mark} is a reason in quotes, or {{ roots = [\"D\"], why = \"...\" }}"); continue
            if 0 in fr: P.append(f"{where}: {mark}: an open voicing has one root, so it takes no roots")
            for n in m["roots"]:
                try: pc_of(n)
                except Exception: P.append(f"{where}: {mark}: {n!r} is not a note name")
        if chord_type and v.get("pin") and v.get("skip"): P.append(f"{where}: pin and skip together")
        if not v["sources"]: P.append(f"{where}: no sources")
        for c in v["sources"]:
            w = f"{where}, source {c.get('by')} {c.get('chord', '')}"
            if c.get("by") not in SOURCES: P.append(f"{w}: {c.get('by')!r} is not in data/sources.toml")
            if not isinstance(c.get("url"), str) or not c["url"].startswith(("https://", "http://")): P.append(f"{w}: no link")
            if c.get("counts_as") and c["counts_as"] not in SOURCES: P.append(f"{w}: counts_as {c['counts_as']!r} is unknown")
            if c.get("via") is not None and c["via"] not in VIA: P.append(f"{w}: via {c['via']!r} is not one of {sorted(VIA)}")
            for k in set(c) - {"by", "url", "chord", "frets", "fingers", "counts_as", "via", "note"}: P.append(f"{w}: unknown field {k}")
            try: cf = parse(c.get("frets") or "")
            except ValueError: P.append(f"{w}: frets {c.get('frets')!r} are missing or malformed"); continue
            if key(cf) != key(fr): P.append(f"{w}: frets {c['frets']} are another voicing")
            g = c.get("fingers")
            if g is not None and (not isinstance(g, str) or len(g) != 6 or set(g) - set("IMRL-")
                                  or any((cf[i] not in (None, 0)) != (g[i] != "-") for i in range(6))):
                P.append(f"{w}: fingers {g!r} must be 6 of I M R L -, a letter on each fretted string")

    symbols = {}
    for n, t in TYPES.items():
        where = f"data/chords/{n}.toml"
        for f in ("symbol", "name", "formula", "about"):
            if not isinstance(t.get(f), str): P.append(f"{where}: missing {f}")
        if "also" in t and not isinstance(t["also"], str): P.append(f"{where}: also must be text in quotes")
        for k in set(t) - {"symbol", "name", "also", "formula", "optional", "about", "voicings"}: P.append(f"{where}: unknown field {k}")
        degs = str(t.get("formula", "")).split()
        if not degs or degs[0] != "1" or any(d not in SEMI for d in degs): P.append(f"{where}: formula {t.get('formula')!r} must start with 1 and use known degrees")
        if not isinstance(t.get("optional"), list) or any(d not in degs for d in t["optional"]): P.append(f"{where}: optional must list degrees of the formula ([] for none)")
        if t.get("symbol") in symbols: P.append(f"{where}: symbol {t['symbol']!r} is also used by {symbols[t['symbol']]}")
        symbols[t.get("symbol")] = n
        seen = set()
        allowed = {SEMI[d] for d in degs if d in SEMI}
        for k, v in enumerate(t["voicings"]):
            w = f"{where} voicing {k + 1} ({v['strings']})"
            voicing(w, v, True)
            bass = next((i for i in range(6) if v["fr"][i] is not None), None)
            if bass is not None and any((OPEN[i] + f - OPEN[bass] - v["fr"][bass]) % 12 not in allowed for i, f in enumerate(v["fr"]) if f is not None):
                P.append(f"{w}: a note that is not in the formula {t.get('formula')} (the lowest note is the root)")
            if bass is not None:                         # the name, for reading the file: the root is the lowest note (C for a movable shape)
                name = NOTES[(OPEN[bass] + v["fr"][bass]) % 12] + str(t.get("symbol", ""))
                if v.get("chord") != name: P.append(f"{w}: chord must be {name!r}, the lowest note and the symbol (it is {v.get('chord')!r})")
            if key(v["fr"]) in seen: P.append(f"{w}: the same voicing appears twice")
            seen.add(key(v["fr"]))
    seen = set()
    for k, v in enumerate(SLASH):
        w = f"data/slash.toml chord {k + 1} ({v.get('name')} {v['strings']})"
        if not re.fullmatch(r"[A-G][♯♭]?m?/[A-G][♯♭]?", str(v.get("name"))): P.append(f"{w}: name {v.get('name')!r} is not like C/E or Am/G")
        voicing(w, v, False)
        if (v.get("name"), tuple(v["fr"])) in seen: P.append(f"{w}: appears twice")
        seen.add((v.get("name"), tuple(v["fr"])))
        if v.get("book") and re.fullmatch(r"[A-G][♯♭]?m?/[A-G][♯♭]?", str(v.get("name"))):   # the book labels every note from the chord's root
            r = pc_of(v["name"].split("/")[0].rstrip("m"))
            odd = sorted({(OPEN[i] + f - r) % 12 for i, f in enumerate(v["fr"]) if f is not None} - set(SLASH_DEGREE))
            if odd: P.append(f"{w}: notes {odd} semitones above the root have no degree name for a slash chord")
    return P

def require_valid():
    """Stop a build when the data is malformed."""
    P = check()
    if P: raise SystemExit("The data has problems (run make audit):\n" + "\n".join(P[:40]))
