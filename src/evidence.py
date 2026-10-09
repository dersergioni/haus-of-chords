# Published evidence for every voicing and fingering (data/evidence/*.toml).
# A voicing counts as confirmed when at least two independent publishers list it; publishers that copy one another,
# or share a publisher, count once (counts_as), and chords-db and its copies never count (confirms = false). A publisher
# that reuses another's charts (copies) counts as that publisher wherever its chart of the voicing is the same.
import data
from data import key, SOURCES

def cluster(c):
    """The publisher a citation counts as."""
    sid = c.get("counts_as") or c["by"]
    while SOURCES[sid].get("counts_as"): sid = SOURCES[sid]["counts_as"]
    return sid

def confirms(cl):
    return SOURCES[cl].get("confirms", True)

_IDX = {}                            # (chord symbol or "slash", shape key) -> every voicing of that shape
for _t in data.TYPES.values():
    for _v in _t["voicings"]:
        _IDX.setdefault((_t["symbol"], key(_v["fr"])), []).append(_v)
for _v in data.SLASH:                # the same slash shape in another key (A/C♯ x4222x, B/D♯ x6444x) is the same voicing
    _IDX.setdefault(("slash", key(_v["fr"])), []).append(_v)

def assign(cites):
    """The publisher each citation of one voicing counts as (a list, in order). A citation by a publisher that copies
    another's charts counts as that one when it has a chart of this voicing with the same shape and the same fingers
    (a chart without fingers cannot be shown to be the same)."""
    chart = lambda c: (key(data.parse(c["frets"])), c.get("fingers"))
    out = []
    for c in cites:
        cl, src = cluster(c), SOURCES[c["by"]].get("copies")
        if src and any(cluster(o) == cluster({"by": src}) and chart(o) == chart(c) and c.get("fingers") for o in cites):
            cl = cluster({"by": src})
        out.append(cl)
    return out

def support(q, fr, fg):
    """(publishers that list the voicing, publishers that give exactly this fingering, citations); non-confirming excluded."""
    cites = [c for v in _IDX.get((q, key(list(fr))), []) for c in v["sources"]]
    want = "".join(x or "-" for x in fg)
    cls = assign(cites)
    voicing = {cl for cl in cls if confirms(cl)}
    fingering = {cl for c, cl in zip(cites, cls) if c.get("fingers") == want and confirms(cl)}
    return voicing, fingering, cites

def names(clusters):
    """Readable names for a set of publishers, e.g. 'JamPlay chord library / fachords'."""
    return sorted(" / ".join(sorted(SOURCES[s]["name"] for s in SOURCES if cluster({"by": s}) == c)) for c in clusters)
