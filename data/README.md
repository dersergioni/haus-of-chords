# The chord data

Everything the book and the website show is built from the plain-text [TOML](https://toml.io) files in this folder. The code holds no chords; it computes the rest.

```
data/
  chords/<type>.toml     a chord type: its symbol, formula and voicings (27 files)
  evidence/<type>.toml   where each voicing of chords/<type>.toml is published
  evidence/slash.toml    where each slash chord is published
  slash.toml             slash chords (C/E, D/F♯ …)
  sources.toml           the publishers that are cited, and which of them count as one source
  book.toml              the book: title and subtitle, edition, the pages of each root and the chord types on them
```

## A voicing

One voicing is one line, and one string is one token, from the 6th (low E) to the 1st (high E):

| token | meaning |
|---|---|
| `x` | not played |
| `0` | open string |
| `3R` | fret 3, pressed by the ring finger |

The fingers are `I` index, `M` middle, `R` ring and `L` little. There is no thumb. The same letter on several strings at one fret is one finger lying flat (a barre), and the diagrams draw a pale bar for it. Every fretted string has a finger, and open or muted strings have none.

```
"x 3R 2M 0 1I 0"          C major, open:                   x32010, fingers -RM-I-
"8I 10R 10L 9M 8I 8I"     C major, E-shape barre, fret 8:  8(10)(10)988, fingers IRLMII
```

There are two kinds of voicing:

- **Open voicings** have at least one open string. Each one belongs to its own root, the lowest note (`0 2M 2R 1I 0 0` is E).
- **Movable shapes** have no open string. They are written with their root on C, lowest fret 1 to 12 (`8I 10R 10L 9M 8I 8I`), and the book moves them to each of the 12 roots.

## `chords/<type>.toml`

```toml
symbol   = "m7"                # added to the root: Cm7, F♯m7
name     = "minor 7th"
formula  = "1 ♭3 5 ♭7"         # degrees, counted against the major scale
optional = ["5"]               # degrees a voicing may leave out ([] for none)
about    = "minor + minor 7th"

voicings = [
  { chord = "Em7", strings = "0 2M 0 0 0 0" },
  { chord = "Em7", strings = "0 2I 2M 0 3R 3L", pin = "Wonderwall: the ring and little fingers stay on the 3rd fret" },
  { chord = "Cm7", strings = "8I 10R 8I 8I 8I 8I" },
  { chord = "Cm7", strings = "x 3M 1I 3R 4L x" },
]
```

- `chord`: the name of the voicing as written, so that the file reads at a glance: the lowest note and the symbol (`Em7` for `0 2M 0 0 0 0`; a movable shape is written on C, so `Cm7`, and the book moves it to the other roots). The check compares it with the frets.

- `also`: another symbol for the type, printed after the name: `augmented (+)`. Optional.
- Degrees: `1` `♭9` `2` `9` `♯9` `♭3` `3` `4` `11` `♭5` `5` `♯5` `6` `13` `°7` `♭7` `7`.
- `pin`, `skip`: the author's choice, written on the voicing itself, with the reason: `pin = "..."` puts the voicing in the book whatever the rule below says (it still needs two independent sources), `skip = "..."` keeps it out (the website still shows it). On a movable shape, `pin = { roots = ["D"], why = "..." }` or the same with `skip` applies to those roots only. A mark never refers to the rule's result, so it holds when the data or the rule change.

The book shows three voicings for each chord (one root and one type, for example F♯m7), chosen by a rule from every voicing of the type that at least two independent sources publish:

1. the open voicing of that root that most sources publish, and a second one if at least three sources publish it (and it is more than one muted string away from the first);
2. the places left go to the movable shapes, one voicing per shape (the CAGED shape, or the root's string outside the five), moved to the root: first the shapes more sources publish; with as many sources, the one nearer the nut, then the one whose fingering more sources give;
3. a movable voicing that, slid down 12 frets, plays part of the row's open voicing (the same notes on the same strings) is that voicing an octave higher, and one that differs from a voicing already taken only by one muted string is the same voicing: both are passed over;
4. the pinned voicings are always in, the skipped ones never.

In the row: the open voicings first, in the order of this file; then the movable shapes, lower on the neck first. The website shows every voicing that at least two independent sources publish: the book's three first, then all the others.

The files also keep voicings that only one independent source publishes so far, with that source in `evidence/`: candidates that neither the book nor the website shows until a second source is found. Anyone reusing the data should count the sources of a voicing before treating it as confirmed.

The label above each diagram names the CAGED shape, worked out from the frets:

- an open voicing of C, A, G, E or D is that shape ("C shape");
- a movable shape is shape X when, slid towards the nut until its root is X, it is part of an open voicing of X in the same file: `x x 10I 11R 11R 11R` slid down 10 frets is part of the open Dm7♭5 `x x 0 1I 1I 1I`, so it is a D shape. If two shapes fit, the one whose open voicing has its root on the same string wins, then the shorter slide;
- otherwise a movable shape is shape X when, slid towards the nut (or not at all), every root lies where the open major chord X has one (its bass among them), its lowest third lies where X has its third (a minor third one fret lower), and every note lies between one fret behind the nut and the third fret; if two fit, the shorter slide. The third tells the shapes apart: G has it on the 5th string, E on the 3rd. Cm7♭5 `8M x 8R 8L 7I x` slid down 8 frets has its root where open E has it and its minor third one fret below E's third, so it is an E shape;
- an E shape with its root on the 4th string is "E shape, 4 strings" (F = `x x 3R 2M 1I 1I`);
- any other voicing is named by the string of its root: "Root on 6th", "5th" or "4th".

Every voicing in a chord-type file follows these rules:

- the lowest note is the root, on the 6th, 5th or 4th string;
- it has only notes of the formula, and every note except the `optional` ones;
- it appears only once in its file.

## `evidence/<type>.toml`

Each voicing of `chords/<type>.toml` has an entry here. The key is its frets in the usual tab notation (`(10)` for fret 10), and the value is the list of pages that publish it:

```toml
"022033" = [
  { by = "justinguitar", url = "https://www.justinguitar.com/chords/e-min-7", chord = "Emin 7", frets = "022033", fingers = "-IM-RL", via = "browser" },
  { by = "fender", url = "https://www.fender.com/play/lessons/em7-open-position-v3", chord = "Em7 Open Position (v3)", frets = "022033", fingers = "-IM-RL", via = "reader" },
]
```

| field | meaning |
|---|---|
| `by` | the publisher, an id from `sources.toml` |
| `url` | the page |
| `chord` | the name the page gives the chord |
| `frets` | the frets as the page shows them. For a movable shape this may be at another root (an F barre for the C shape). It must be the same voicing. |
| `fingers` | the fingers as the page shows them, one per string: `I M R L`, `-` for open or muted. Left out when the page shows none. |
| `via` | how the page was read, when not from its text: `browser` (a browser was needed), `reader` (a reader service), `image` (read from the chart picture), `data` (the chart data the page draws from), `archive` (an archived copy), `copy` (a local copy of the data) |
| `counts_as` | this citation is a copy of another publisher's chart, so it counts as that publisher |
| `note` | anything else worth knowing |

`evidence/slash.toml` works the same way, with the chord name in the key: `"C/E 032010"`.

## How sources are counted

- A voicing counts as published when at least two **independent** sources list it.
  - Publishers that copy one another, or belong to the same company, count once (`counts_as` in `sources.toml`).
  - chords-db, and the sites that copy it, are cited but never count (`confirms = false`).
- The fingers printed for a voicing are the fingering most of those sources give. On a tie the book follows JustinGuitar, then Fender, then an earlier draft of this book, then chords-db.
- Chord generators, which compute shapes rather than teach them, are never cited.

## slash.toml

```toml
chords = [
  { name = "C/E", strings = "0 3R 2M 0 1I 0", book = true },
]
```

A slash chord is written exactly as it is played, not moved to C. Degrees are counted from the chord's own root, so the bass of D/F♯ shows 3. `book = true` puts a slash chord in the book and on the website (twelve are chosen by hand); the others are kept with their sources but not shown. Every slash chord shown needs two independent sources, like any voicing.

## sources.toml

```toml
[fachords]
name = "fachords"
site = "https://fachords.com/"
counts_as = "jamplay"          # optional: counts as this publisher
note = "copies JamPlay's charts"
```

`confirms = false` marks a publisher that is cited but never counted. `copies = "jamplay"` marks a publisher that reuses another's charts: wherever its chart of a voicing has the same frets and fingers as that publisher's, it counts as that publisher (tabs4acoustic).

## book.toml

`title`, `subtitle`, `version`, `date`, `author`, `github` (the repository that the book and the site link to for corrections) and `site` (the published website). Then one `[[page]]` per page of each root: its `title`, a `short` title for the contents, and the chord `types` on it, by file name.

## Adding a voicing

1. Find at least two independent published pages that show it, with fingers on at least one of them.
2. Add the voicing to `chords/<type>.toml` with its `chord` name. Write a movable shape with its root on C. The rule decides whether the book shows it.
3. Add an entry with the same frets to `evidence/<type>.toml`, with one citation per page.
4. Run `make web audit`. Each check ends with `PROBLEMS: 0` when everything is in order.
