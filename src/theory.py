# Music theory the book needs: note names, the guitar's tuning, chord degrees, note spelling and the chords of each key.
# Nothing here reads the data files.

NOTES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]   # the name each root is printed with
OPEN = [4, 9, 2, 7, 11, 4]          # pitch classes of the open strings, 6th string first (standard tuning)

# ---- chord degrees: semitones above the root, letter steps above the root, colour (one per step of the scale), name
DEGREES = {
    "1":  (0, 0, "d1", "root"),
    "♭9": (1, 1, "d2", "flat ninth"),
    "2":  (2, 1, "d2", "second"),
    "9":  (2, 1, "d2", "ninth"),
    "♯9": (3, 1, "d2", "sharp ninth"),
    "♭3": (3, 2, "d3", "minor third"),
    "3":  (4, 2, "d3", "major third"),
    "4":  (5, 3, "d4", "fourth"),
    "11": (5, 3, "d4", "eleventh"),
    "♭5": (6, 4, "d5", "flat fifth"),
    "5":  (7, 4, "d5", "fifth"),
    "♯5": (8, 4, "d5", "sharp fifth"),
    "6":  (9, 5, "d6", "sixth"),
    "13": (9, 5, "d6", "thirteenth"),
    "°7": (9, 6, "d7", "diminished seventh"),
    "♭7": (10, 6, "d7", "minor seventh"),
    "7":  (11, 6, "d7", "major seventh"),
}
SEMI = {d: v[0] for d, v in DEGREES.items()}
STEPS = {d: v[1] for d, v in DEGREES.items()}
GROUP = {d: v[2] for d, v in DEGREES.items()}       # colour: d1 root, d2 2nd/9th, d3 third, d4 4th/11th, d5 fifth, d6 6th/13th, d7 seventh
DEG_NAME = {d: v[3] for d, v in DEGREES.items()}

# the key to the colours (the book and the site): one colour per step of the scale, named the same way each time,
# in the order of the scale, 1 to 7; (the number in its dot, the name, the degrees it covers: checked below)
KEY = [("1", "root", ["1"]), ("2", "2nd / 9th", ["2", "9", "♭9", "♯9"]), ("3", "3rd", ["3", "♭3"]), ("4", "4th / 11th", ["4", "11"]),
       ("5", "5th", ["5", "♭5", "♯5"]), ("6", "6th / 13th", ["6", "13"]), ("7", "7th", ["7", "♭7", "°7"])]
KEY_LABELS = [(dot, name) for dot, name, _degs in KEY]          # the dots show the exact degree (♭5, ♯9 …); the key names the step
assert sorted(d for *_x, ds in KEY for d in ds) == sorted(DEGREES), "theory.KEY must cover every degree once"
assert all(GROUP[d] == GROUP[dot] for dot, _n, ds in KEY for d in ds), "theory.KEY: one colour per item"

SLASH_DEGREE = {SEMI[d]: d for d in ("1", "9", "♭3", "3", "4", "5", "6", "♭7", "7")}   # how a slash chord's notes are labelled

# ---- note spelling: each chord degree takes its own letter (E♭ in Cm, B𝄫 in Cdim7, E♯ in F♯ chords)
LETTERS = "CDEFGAB"
NATPC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACC = {0: "", 1: "♯", 2: "𝄪", -1: "♭", -2: "𝄫"}

def pc_of(name):
    """Pitch class of a note name: 'E♭' -> 3."""
    acc = name[1:]
    return (NATPC[name[0]] + acc.count("♯") - acc.count("♭") + 2 * acc.count("𝄪") - 2 * acc.count("𝄫")) % 12

def note_above(name, steps, semis):
    """The note `steps` letters and `semis` semitones above a note name."""
    letter = LETTERS[(LETTERS.index(name[0]) + steps) % 7]
    diff = (pc_of(name) + semis - NATPC[letter]) % 12
    if diff > 6: diff -= 12
    return letter + ACC[diff]

def spell(root, deg):
    """Name of a chord degree above a root (pitch class), spelled from the root's printed name."""
    return note_above(NOTES[root], STEPS[deg], SEMI[deg])

# ---- black keys have two names: the chord names use C♯, E♭, F♯, A♭, B♭
SHARPS = {1: "C♯", 3: "D♯", 6: "F♯", 8: "G♯", 10: "A♯"}
FLATS = {1: "D♭", 3: "E♭", 6: "G♭", 8: "A♭", 10: "B♭"}

def other_name(r):
    """The second name of a black key (the one not used in the chord names), or None for white keys."""
    if r not in SHARPS: return None
    return FLATS[r] if NOTES[r] == SHARPS[r] else SHARPS[r]

def both_names(r):
    return f"{SHARPS[r]} / {FLATS[r]}" if r in SHARPS else NOTES[r]

# ---- chords in each major key, and in each natural minor key (the relative minors, in the same order)
KEYS = ["C", "D♭", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]
NUMERALS = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
SCALE = [0, 2, 4, 5, 7, 9, 11]
TRIAD = ["", "m", "m", "", "", "m", "dim"]
SEVENTH = ["maj7", "m7", "m7", "maj7", "7", "m7", "m7♭5"]

MINOR_KEYS = ["A", "B♭", "B", "C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯"]
MINOR_NUMERALS = ["i", "ii°", "III", "iv", "v", "VI", "VII"]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]
MINOR_TRIAD = ["m", "dim", "", "m", "m", "", ""]
MINOR_SEVENTH = ["m7", "m7♭5", "maj7", "m7", "m7", "maj7", "7"]

def key_chords(key, minor=False):
    """[(numeral, root name, root pitch class, triad type, seventh type)] for a major key, or a natural minor one."""
    num, scale, tri, sev = (MINOR_NUMERALS, MINOR_SCALE, MINOR_TRIAD, MINOR_SEVENTH) if minor else (NUMERALS, SCALE, TRIAD, SEVENTH)
    out = []
    for i in range(7):
        root = note_above(key, i, scale[i])
        out.append((num[i], root, pc_of(root), tri[i], sev[i]))
    return out
