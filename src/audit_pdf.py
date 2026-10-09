# Audit of what is printed in the PDF. Usage: python3 audit_pdf.py file.pdf
import os, sys, re
import pdfplumber
from pdfplumber.utils import extract_words
from pypdf import PdfReader
import build_en as B                 # the page map and the diagram geometry this audit mirrors
from chords import GROUPS, shown, tag, position
from theory import NOTES, spell, pc_of, other_name, both_names

PDF = sys.argv[1] if len(sys.argv) > 1 else B.OUT
W, H, M = B.W, B.H, B.M
P = []
label_w, cell_w = B.LABEL_W, B.CELL_W
nrows = n_names = n_notes = n_labels = n_marks = n_fingers = 0

with pdfplumber.open(PDF) as pdf:
    pages = pdf.pages
    if len(pages) != B.ABOUT_PAGE: P.append(f"page count {len(pages)} != {B.ABOUT_PAGE}")
    # ---------- 1. chord pages: names, aliases, degrees, notes, labels, dots, ×, fingers, fret numbers
    for r in range(12):
        for gi, (gtitle, grp) in enumerate(GROUPS):
            pno = B.ROOT_PAGE(r, gi); page = pages[pno - 1]
            # words by size and weight, not by font file: a ♯ or ♭ may come from a fallback font in the middle of a word
            words = extract_words([dict(ch, bold="Bold" in ch["fontname"], size=round(ch["size"], 2)) for ch in page.chars], extra_attrs=["size", "bold"])
            head = " ".join(w["text"] for w in words if w["top"] < 75)
            if both_names(r) not in head or gtitle not in head: P.append(f"p{pno}: header '{head}'")
            for qi, ((q, qname, formula, desc, temps), (y0, bottom)) in enumerate(zip(grp, B.cards(r, grp))):
                nrows += 1
                ytop, ybot = H - y0, H - bottom
                lab = [w for w in words if ytop <= w["top"] < ybot and w["x0"] < M + label_w - 4]
                big = [w["text"] for w in lab if w["size"] >= 12.5 and w["bold"]]   # the name (a large 𝄪 in the notes is not bold)
                if big != [NOTES[r] + q]: P.append(f"p{pno} row {qi+1}: name {big}")
                else: n_names += 1
                al = other_name(r)
                if al and " ".join(w["text"] for w in lab if w["bold"] and abs(w["size"] - 8) < 0.05 and abs(w["top"] - (H - (y0 - 35)) + 6) < 4) != f"= {al}{q}":
                    P.append(f"p{pno} {NOTES[r]+q}: alias missing or wrong")
                dsize, nsize = B.formula_sizes(len(formula.split()))
                degs = sorted([w for w in lab if w["bold"] and abs(w["size"] - dsize) < 0.05 and not w["text"].startswith("=") and w["text"] not in (al or "", f"{al}{q}")], key=lambda w: w["x0"])
                degs = [w for w in degs if w["text"] in formula.split()]
                if [w["text"] for w in degs] != formula.split(): P.append(f"p{pno} {NOTES[r]+q}: degrees {[w['text'] for w in degs]}"); continue
                dtop = degs[0]["top"]
                notes = sorted([w for w in lab if abs(w["size"] - nsize) < 0.05 and not w["bold"] and dtop + 3 < w["top"] < dtop + 16], key=lambda w: w["x0"])
                for m in [w for w in lab if w["text"] in ("𝄪", "𝄫") and dtop + 3 < w["top"] < dtop + 16]:   # set larger, from the music font
                    n = max((w for w in notes if w["x1"] <= m["x0"] + 0.5), key=lambda w: w["x1"], default=None)
                    if n and m["x0"] - n["x1"] < 1.5: n["text"] += m["text"]; n["x1"] = m["x1"]
                expect = [spell(r, d) for d in formula.split()]
                if len(notes) != len(expect): P.append(f"p{pno} {NOTES[r]+q}: {len(notes)} notes printed, {len(expect)} expected"); continue
                for d, n, e in zip(degs, notes, expect):
                    n_notes += 1
                    if abs(d["x0"] - n["x0"]) > 0.6: P.append(f"p{pno} {NOTES[r]+q}: note {n['text']} not under {d['text']}")
                    if n["text"] != e: P.append(f"p{pno} {NOTES[r]+q}: under {d['text']} printed {n['text']}, expected {e}")
                for a, b2 in zip(notes, notes[1:]):
                    if a["x1"] + 0.8 > b2["x0"]: P.append(f"p{pno} {NOTES[r]+q}: notes {a['text']} and {b2['text']} touch")
                vs = shown(r, temps)
                for k, (t, base) in enumerate(vs):
                    cx = M + label_w + cell_w * k + cell_w / 2; cx0 = cx - cell_w / 2
                    lsize = B.label_size(t, base, width=cell_w - 16)     # long labels shrink to fit their cell
                    cell = [w["text"] for w in words if ytop <= w["top"] < ytop + 16 and cx0 <= w["x0"] < cx0 + cell_w and abs(w["size"] - lsize) < 0.05]
                    want = (tag(t) + " " + position(t, base)).split()
                    if cell != want: P.append(f"p{pno} {NOTES[r]+q} cell {k+1}: label '{' '.join(cell)}' != '{' '.join(want)}'")
                    else: n_labels += 1
                    xs = [cx - 2.5 * B.SP + 4 + i * B.SP for i in range(6)]
                    gtop = y0 - 28
                    rows_ = max(4, max(v[0] for v in t["n"] if v) + (1 if base > 0 else 0))
                    expect = []
                    for i, v in enumerate(t["n"]):
                        if v is None: expect.append((i, "×", gtop + B.OPEN_DY)); continue
                        o, d = v
                        expect.append((i, d, gtop + B.OPEN_DY if (base == 0 and o == 0) else gtop - ((o + 1 if base > 0 else o) - 0.5) * B.RH))
                    got = [w for w in words if xs[0] - 8 < (w["x0"] + w["x1"]) / 2 < xs[5] + 8 and gtop - rows_ * B.RH - 2 < H - (w["top"] + w["bottom"]) / 2 < gtop + 14
                           and (abs(w["size"] - B.R * B.LABEL_K[0]) < 0.05 or abs(w["size"] - B.R * B.LABEL_K[1]) < 0.05 or w["text"] == "×")]
                    for i, d, yc in expect:
                        n_marks += 1
                        hit = [w for w in got if abs((w["x0"] + w["x1"]) / 2 - xs[i]) < 4 and abs(H - (w["top"] + w["bottom"]) / 2 - yc) < 4]
                        if len(hit) != 1 or hit[0]["text"] != d: P.append(f"p{pno} {NOTES[r]+q} cell {k+1} string {6-i}: expected {d}, found {[w['text'] for w in hit]}")
                    if len(got) != len(expect): P.append(f"p{pno} {NOTES[r]+q} cell {k+1}: {len(got)} marks, {len(expect)} expected")
                    fy = gtop - rows_ * B.RH - 8.5
                    letters = [w for w in words if abs(w["size"] - B.FING_SIZE) < 0.15 and xs[0] - 8 < (w["x0"] + w["x1"]) / 2 < xs[5] + 8 and abs(H - w["bottom"] - fy) < 3]
                    printed = [None] * 6
                    for w in letters: printed[min(range(6), key=lambda j: abs(xs[j] - (w["x0"] + w["x1"]) / 2))] = w["text"]
                    n_fingers += 1
                    if printed != t["fing"]: P.append(f"p{pno} {NOTES[r]+q} cell {k+1}: fingers {printed} expected {t['fing']}")
                    fret = [w["text"] for w in words if abs(w["size"] - 7) < 0.05 and w["bold"] and xs[0] - 30 < w["x1"] < xs[0] and abs(H - (w["top"] + w["bottom"]) / 2 - (gtop - B.RH / 2)) < 4]
                    if fret != ([str(base)] if base > 0 else []): P.append(f"p{pno} {NOTES[r]+q} cell {k+1}: fret number {fret}, expected {base}")
                extra = [w["text"] for w in words if ytop <= w["top"] < ytop + 16 and abs(w["size"] - 7.5) < 0.05 and w["x0"] >= M + label_w + cell_w * len(vs)]
                if extra: P.append(f"p{pno} {NOTES[r]+q}: text in an empty cell {extra}")
    print(f"1. chord pages: rows {nrows}, names {n_names}, note names {n_notes}, labels {n_labels}, dots and × {n_marks}, finger rows {n_fingers}")

    # ---------- 2. layout: overlaps and margins on every page
    ov = []; nwords = 0; nfret = 0
    for pi, page in enumerate(pages, start=1):
        words = page.extract_words(extra_attrs=["size"])
        nwords += len(words)
        for w in words:
            if w["x0"] < M - 1.5 or w["x1"] > W - M + 1.5 or w["top"] < 20 or w["bottom"] > H - 12: ov.append(f"p{pi}: '{w['text']}' outside the margins")
        for a in range(len(words)):
            for b2 in range(a + 1, len(words)):
                u, v = words[a], words[b2]
                if u["x0"] < v["x1"] - 0.6 and v["x0"] < u["x1"] - 0.6 and u["top"] < v["bottom"] - 0.6 and v["top"] < u["bottom"] - 0.6:
                    ov.append(f"p{pi}: '{u['text']}' overlaps '{v['text']}'")
        shapes = [s for s in page.curves + page.rects if (s["x1"] - s["x0"]) < 150]
        for w in words:
            if re.fullmatch(r"\d+", w["text"]) and abs(w["size"] - 7.0) < 0.05 and pi >= B.PAGE["slash"]:
                nfret += 1
                inside = lambda s: s["x0"] <= w["x0"] and s["x1"] >= w["x1"] and s["top"] <= w["top"] and s["bottom"] >= w["bottom"]   # the card behind it
                if any(s["x0"] < w["x1"] + 0.5 and s["x1"] > w["x0"] - 0.5 and s["top"] < w["bottom"] and s["bottom"] > w["top"] and not inside(s) for s in shapes):
                    ov.append(f"p{pi}: fret number {w['text']} touches a dot or barre")
    # chord pages: everything except header and footer sits inside its card
    for r in range(12):
        for gi, (gtitle, grp) in enumerate(GROUPS):
            pno = B.ROOT_PAGE(r, gi); boxes = B.cards(r, grp)
            for w in pages[pno - 1].extract_words():
                if w["top"] < 75 or w["bottom"] > H - (M + 18): continue
                if not any(H - (y0 - 2) <= w["top"] and w["bottom"] <= H - bottom for y0, bottom in boxes): ov.append(f"p{pno}: '{w['text']}' sticks out of its card")
    # names in the index and key tables must not run into one another (one chord root per word)
    for pno in (B.PAGE["keys"], B.PAGE["minorkeys"], B.PAGE["index"]):
        for w in pages[pno - 1].extract_words():
            if len(re.findall(r"[A-G](?:[♯♭])?(?=[a-z0-9(♯♭]|$)", w["text"])) > 1 and not re.search(r"[A-G]/[A-G]", w["text"]):
                ov.append(f"p{pno}: chord names run together: '{w['text']}'")
    print(f"2. layout: {nwords} words on {len(pages)} pages checked for overlaps and margins, {nfret} fret numbers checked against dots and barres:", "no problems" if not ov else f"{len(ov)} problems")
    P += ov

    # ---------- 3. links: every internal link lands on the right page, and the linked text is on that page
    rd = PdfReader(PDF)
    pageno = {p.indirect_reference.idnum: i + 1 for i, p in enumerate(rd.pages)}
    nlinks = 0; ext = []
    for pi, p in enumerate(rd.pages, start=1):
        for a in p.get("/Annots") or []:
            o = a.get_object(); rect = [float(x) for x in o["/Rect"]]
            if "/A" in o: ext.append(str(o["/A"]["/URI"])); continue
            nlinks += 1
            dest = pageno.get(o["/Dest"][0].idnum)
            if dest is None: P.append(f"p{pi}: link to nowhere"); continue
            txt = " ".join(w["text"] for w in pages[pi - 1].extract_words() if w["x0"] >= rect[0] - 1 and w["x1"] <= rect[2] + 1 and H - w["bottom"] >= rect[1] - 2 and H - w["top"] <= rect[3] + 2)
            dtext = pages[dest - 1].extract_text() or ""
            m = re.fullmatch(r"([A-G][♯♭]?)(\S*)", txt.strip())
            if pi <= len(B.FRONT) and m and pi != B.PAGE["contents"]:
                root = m.group(1); q = m.group(2)
                rpc = pc_of(root)
                want = B.ROOT_PAGE(rpc, B.GI[q]) if q in B.GI else None
                if re.search(r"/[A-G]", q): want = B.ROOT_PAGE(rpc, 0)   # slash chord: page of its chord
                if want and dest != want: P.append(f"p{pi}: link '{txt}' goes to page {dest}, expected {want}")
    print(f"3. links: {nlinks} internal links checked, external: {sorted(set(ext))}")
    def count(o): return sum(count(x) if isinstance(x, list) else 1 for x in o)
    print("   bookmarks:", count(rd.outline))

    # ---------- 4. fonts and glyphs
    allt = "".join(p.extract_text() or "" for p in pages)
    bad = [ch for ch in ("�", "□") if ch in allt]
    helv = sum(1 for p in pages for ch in p.chars if "Helvetica" in ch["fontname"])
    # words that must never appear in the book: "thumb" (fingers are I M R L), plus any listed in the local file .audit-forbidden
    extra = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".audit-forbidden")
    words = ["thumb"] + ([w.strip() for w in open(extra, encoding="utf8") if w.strip()] if os.path.exists(extra) else [])
    words += [w.strip() for w in os.environ.get("AUDIT_FORBIDDEN", "").split(",") if w.strip()]   # on GitHub: a repository secret
    found = [(w[:2] if len(w) > 4 else w[:1]) + "…" for w in words if w.lower() in allt.lower()]   # cut short: a CI log is public
    if found: P.append(f"forbidden words in the text: {found}")
    if bad: P.append(f"missing glyphs in the text: {bad}")
    if helv: P.append(f"{helv} characters set in a non-embedded font")
    print("4. missing glyphs:", bad or "none", "| characters set in a non-embedded font:", helv, f"| forbidden words checked: {len(words)}, found:", found or "none")

print("\nPROBLEMS:", len(P)); print("\n".join(P[:40]))
raise SystemExit(1 if P else 0)          # a problem fails the build: make audit, and the publishing workflow
