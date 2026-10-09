# Audit of the chord data (independent of the PDF): notes, degrees, bass, fingers, sources, spelling.
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
from collections import Counter
from pychord import Chord
import data
P = list(data.check())
print("0. form of the data files:", "no problems" if not P else f"{len(P)} problems")
if P: print("\nPROBLEMS:", len(P)); print("\n".join(P[:40])); raise SystemExit(1)   # the rest is worked out from the data
import evidence
from chords import ALL, OPTIONAL, SLASH_CHORDS, shown, frets, near_dup, tag
from theory import NOTES, OPEN, SEMI, spell, pc_of, KEYS, SCALE, MINOR_KEYS, MINOR_SCALE, key_chords
fs = data.fstr
book_vs = [(r, q, formula, t, b) for q, name, formula, desc, temps in ALL for r in range(12) for t, b in shown(r, temps)]
print("A. voicings shown:", len(book_vs), "| rows:", len(ALL) * 12)

# A. notes, degree labels, bass, required notes, fingers, playability
ORDER = {"I": 0, "M": 1, "R": 2, "L": 3}
for r, q, formula, t, b in book_vs:
    fr = frets(t, b); fg = t["fing"]; name = f"{NOTES[r]}{q} {fs(fr)}"
    allowed = {SEMI[d] for d in formula.split()}
    req = {SEMI[d] for d in formula.split() if d not in OPTIONAL[q]}
    got, pcs = set(), []
    for i, v in enumerate(t["n"]):
        if v is None: continue
        iv = (OPEN[i] + fr[i] - r) % 12
        if iv != SEMI[v[1]]: P.append(f"{name}: string {6-i} labelled {v[1]} but sounds {iv} semitones above the root")
        if v[1] not in formula.split(): P.append(f"{name}: label {v[1]} not in formula {formula}")
        got.add(iv); pcs.append(iv)
    if not got <= allowed: P.append(f"{name}: extra notes {got - allowed}")
    if not req <= got: P.append(f"{name}: missing {req - got}")
    if pcs[0] != 0: P.append(f"{name}: bass is not the root")
    for i in range(6):
        if (fr[i] not in (None, 0)) != (fg[i] is not None): P.append(f"{name}: finger/fret mismatch on string {6-i}")
    used = {}
    for i in range(6):
        if fg[i]: used.setdefault(fg[i], []).append(i)
    for f, ss in used.items():
        if len({fr[i] for i in ss}) > 1: P.append(f"{name}: {f} on two frets")
        if len(ss) > 1 and any(fr[i] is None or fr[i] < fr[ss[0]] for i in range(min(ss), max(ss) + 1)): P.append(f"{name}: {f} flat over a lower, open or muted string")
    fl = sorted(used, key=ORDER.get)
    for a, c2 in zip(fl, fl[1:]):
        if fr[used[a][0]] > fr[used[c2][0]]: P.append(f"{name}: fingers cross ({a} above {c2})")
    fretted = [f for f in fr if f]
    if fretted and max(fretted) - min(fretted) > 3: P.append(f"{name}: stretch over 4 frets")
    for a, z, o in t["bars"]:                   # a drawn barre: no other finger at its fret under it
        if any(fr[i] == fr[a] and fg[i] != fg[a] for i in range(a, z + 1)): P.append(f"{name}: barre of {fg[a]} drawn over another finger")
    if max(fretted or [0]) > 15: P.append(f"{name}: above fret 15")
    if b == 0 and max(fretted or [0]) > 5: P.append(f"{name}: open diagram too tall")
print("A. notes, labels, bass, fingers, playability:", "no problems" if not P else f"{len(P)} problems")

# B. independent check with pychord
BASEPC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
pc = lambda n: (BASEPC[n[0]] + n[1:].count("#") - n[1:].count("b")) % 12
conv = lambda n: n.replace("𝄫", "bb").replace("𝄪", "##").replace("♭", "b").replace("♯", "#")
QMAP = {"": "", "m": "m", "7": "7", "m7": "m7", "maj7": "M7", "sus2": "sus2", "sus4": "sus4", "5": "5", "6": "6", "9": "9",
        "add9": "add9", "7sus4": "7sus4", "m7♭5": "m7-5", "dim7": "dim7", "aug": "aug", "m6": "m6", "6/9": "69",
        "maj9": "M9", "m9": "m9", "13": "13", "7♯9": "7+9", "dim": "dim",
        "m(maj7)": "mM7", "m11": "m11", "9sus4": "9sus4", "7♭9": "7b9", "7♯5": "7#5"}
pb = 0
for r, q, formula, t, b in book_vs:
    want = {pc(n) for n in Chord(conv(NOTES[r]) + QMAP[q]).components()}
    got = {(OPEN[i] + f) % 12 for i, f in enumerate(frets(t, b)) if f is not None}
    opt = {(r + SEMI[d]) % 12 for d in OPTIONAL[q]}
    if q == "13": want = {x for x in want if (x - r) % 12 != 5}          # pychord's 13 includes the 11; guitarists leave it out
    if not (got <= want and want - got <= opt): pb += 1; P.append(f"pychord: {NOTES[r]}{q} {fs(frets(t, b))} notes {sorted(got)} vs {sorted(want)}")
spell_bad = [f"{NOTES[r]}{q}" for q, n, f, *_ in ALL for r in range(12)
             if sorted(conv(spell(r, d)) for d in f.split()) != sorted(x for x in Chord(conv(NOTES[r]) + QMAP[q]).components() if not (q == "13" and (pc(x) - r) % 12 == 5))]
P += [f"note spelling of {c} differs from pychord" for c in spell_bad]
print("B. pychord: notes of", len(book_vs), "voicings,", "problems:", pb, "| note spelling of", len(ALL) * 12, "chords, problems:", len(spell_bad), spell_bad[:5])

# C. sources: at least two independent publishers list every voicing, and one gives every fingering (data/evidence/*.toml)
need = 0
for r, q, formula, t, b in book_vs:
    fr = frets(t, b); fg = t["fing"]; name = f"{NOTES[r]}{q} {fs(fr)}"
    v, f, _ = evidence.support(q, fr, fg)
    if len(v) >= 2: need += 1
    else: P.append(f"{name}: listed by {len(v)} independent source(s) {evidence.names(v)}")
    if not f: P.append(f"{name}: no source gives the fingering {data.fgstr(fg)}")
print(f"C. sources: {need} of {len(book_vs)} voicings listed by 2 or more independent sources")
for s in SLASH_CHORDS:
    fr = frets(s["t"], s["base"]); fg = s["t"]["fing"]
    v, f, _ = evidence.support("slash", fr, fg)
    if len(v) < 2: P.append(f"slash {s['name']} {fs(fr)}: {len(v)} independent source(s)")
    if not f: P.append(f"slash {s['name']} {fs(fr)}: no source gives the fingering")
    comp = {pc(x) for x in Chord(conv(s["name"])).components()}
    got = {(OPEN[i] + x) % 12 for i, x in enumerate(fr) if x is not None}
    bass = next((OPEN[i] + x) % 12 for i, x in enumerate(fr) if x is not None)
    if not (got <= comp and bass == pc(conv(s["name"].split("/")[1]))): P.append(f"slash {s['name']}: notes {got} vs pychord {comp}")
    for i, x in enumerate(s["t"]["n"]):
        if x and (OPEN[i] + fr[i] - s["r"]) % 12 != SEMI[x[1]]: P.append(f"slash {s['name']}: wrong label on string {6-i}")
print("C. slash chords checked against the sources and pychord:", len(SLASH_CHORDS))
# every chords-db citation really is in chords-db
db = json.load(open(os.path.join(HERE, "guitar.json")))["chords"]
alld = {tuple(None if x < 0 else (0 if x == 0 else x + p_["baseFret"] - 1) for x in p_["frets"])
        for entries in db.values() for e in entries for p_ in e["positions"]}
allv = [(ty["symbol"], v) for ty in data.TYPES.values() for v in ty["voicings"]] + [("slash", v) for v in data.SLASH]
ndb = 0
for q, v in allv:
    for c in v["sources"]:
        if c["by"] != "chords-db": continue
        ndb += 1
        if tuple(data.parse(c.get("frets") or v["frets"])) not in alld: P.append(f"data: chords-db citation {q} {c.get('chord')} {c.get('frets')} not in chords-db")
print(f"C. chords-db citations checked against chords-db: {ndb}")
# the author's marks (pin, skip in data/chords): a pinned voicing has 2+ independent sources and is in every row it is
# pinned for; no row has more than ROW pins; a mark that changes nothing today is listed (it still holds if the data change).
from chords import EVERY, ROW, voicings
marks, idle = [], []
for q, n_, f_, d_, temps in ALL:
    for t in EVERY[q]:
        for m in ("pin", "skip"):
            for r in sorted(t[m]):
                if t["only"] not in (None, r): continue
                name = f"{NOTES[r]}{q} {m} {fs(frets(t, voicings(r, [t], near=False)[0][1]))}" if voicings(r, [t], near=False) else f"{NOTES[r]}{q} {m}"
                marks.append(name)
                if m == "pin" and t["nsrc"] < 2: P.append(f"{name}: a pinned voicing needs 2 or more independent sources ({t['nsrc']})")
                row = [x for x, b in shown(r, temps)]
                if m == "pin" and not any(x is t for x in row): P.append(f"{name}: pinned but not in its row")
                if m == "skip" and any(x is t for x in row): P.append(f"{name}: skipped but in its row")
                plain = [dict(x, pin=frozenset(), skip=frozenset()) if x is t else x for x in temps]   # the row without this mark
                if [fs(frets(x, b)) for x, b in shown(r, plain)] == [fs(frets(x, b)) for x, b in shown(r, temps)]: idle.append(name)
    for r in range(12):
        if sum(1 for t in temps if r in t["pin"] and t["only"] in (None, r)) > ROW: P.append(f"{NOTES[r]}{q}: more than {ROW} pinned voicings")
print(f"C. the author's marks: {len(marks)} {marks}; marks that change nothing today: {idle or 'none'}")

# D. chords in each key: spelling and quality via pychord
for key in KEYS:
    for num, root, rpc, tq, sq in key_chords(key):
        scale = {(pc_of(key) + s) % 12 for s in SCALE}
        for qq in (tq, sq):
            comp = {pc(x) for x in Chord(conv(root) + QMAP[qq]).components()}
            if not comp <= scale: P.append(f"key {key}: {root}{qq} has notes outside the scale")
        if pc_of(root) != rpc: P.append(f"key {key}: {root} pitch")
for key in MINOR_KEYS:
    scale = {(pc_of(key) + s) % 12 for s in MINOR_SCALE}
    for num, root, rpc, tq, sq in key_chords(key, minor=True):
        for qq in (tq, sq):
            comp = {pc(x) for x in Chord(conv(root) + QMAP[qq]).components()}
            if not comp <= scale: P.append(f"minor key {key}: {root}{qq} has notes outside the scale")
        if pc_of(root) != rpc: P.append(f"minor key {key}: {root} pitch")
    major = KEYS[MINOR_KEYS.index(key)]
    if (pc_of(key) - pc_of(major)) % 12 != 9: P.append(f"minor key {key} is not the relative minor of {major}")
print("D. chords in each key: 12 major and 12 minor keys x 7 degrees x triad and seventh checked against the scale")

# E. each shown row has 2-3 voicings, no duplicates
cnt = Counter(len(shown(r, temps)) for q, n, f, d, temps in ALL for r in range(12))
dups = [f"{NOTES[r]}{q}" for q, n, f, d, temps in ALL for r in range(12) if len({fs(frets(t, b)) for t, b in shown(r, temps)}) != len(shown(r, temps))]
P += [f"{c}: the same voicing twice in its row" for c in dups]
print("E. voicings per row:", dict(cnt), "| duplicate voicings in a row:", dups or "none")

print("\nPROBLEMS:", len(P)); print("\n".join(P[:40]))
raise SystemExit(1 if P else 0)          # a problem fails the build: make audit, and the publishing workflow
