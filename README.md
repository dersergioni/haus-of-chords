# Haus of Chords

A free guitar chord book and website. Every note in every diagram shows its degree in the chord, the note names are given under each formula, and a letter under each string shows the finger. Every voicing is published by at least two independent sources: guitar teachers, publishers and chord libraries.

**[Website](https://dersergioni.github.io/haus-of-chords/)** · **[PDF](https://dersergioni.github.io/haus-of-chords/downloads/Haus%20of%20Chords.pdf)** · version 1.0, October 2026, by dersergioni ([changelog](CHANGELOG.md))

- **The book**: 58 A4 pages. 27 chord types on 12 roots, three voicings each; how to read the diagrams, the five CAGED shapes, the chords of every major and minor key, 12 slash chords, an index, and how every voicing was checked.
- **The website**: a page for every chord, with every voicing that at least two independent sources publish and links to those sources; light and dark themes and a left-handed view. Downloads: the PDF, the chord data, ChordPro definitions and chords-db JSON.

It is a finished, curated book rather than a growing collection. Corrections are welcome: open an [issue](https://github.com/dersergioni/haus-of-chords/issues) or a pull request with a link to a published source ([how](CONTRIBUTING.md)).

## How the voicings are chosen

- A voicing is in the book only if at least two independent sources publish it. Sites that copy one another, or share a publisher, count once; chords-db and its copies are cited but never counted.
- A rule picks the three voicings of each chord: the open voicing that most sources publish (plus a second open voicing if three or more sources publish it), then movable shapes, one per shape, the best-sourced first and, on a tie, the one nearer the nut. A movable voicing that only repeats the open chord an octave up is skipped.
- Where a song needs a particular voicing, or a weakly sourced one only repeats what the row already shows, the author marks it in or out, with the reason written next to it in the data.
- The printed fingering is the one most of those sources give.
- Each row shows the open voicings first, then the movable shapes, lower on the neck first.

Every citation, with a link to its page, is in `data/evidence/`. The rules in full: [data/README.md](data/README.md).

## Build

Python 3.11 or later (`python3 --version`; if it is older, use a newer one, for example `python3.12`, in the first line):

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
make web audit     # build the PDF and the site into dist/, then run the three checks
make preview       # a PNG of every page of the PDF, in build/preview
make serve         # the site at http://127.0.0.1:8000
```

The Makefile uses `.venv` without activating it, and the fonts are in `fonts/`: nothing else to install. With Google Chrome or Chromium installed, the site check also tests pages at phone width.

## How it is made

```text
data/                 the chords and their sources, plain TOML (the format: data/README.md)
src/
  theory.py           note names, degrees, spelling, the chords of each key
  data.py             reads data/ and checks its form
  evidence.py         counts the independent sources of a voicing
  chords.py           the voicings of each row, their labels, the slash chords
  book.py             what the book and the site share: title, edition, design, the numbers on the last page
  build_en.py         the PDF (reportlab)
  build_site.py       the website (static HTML, inline SVG diagrams, works without JavaScript)
  audit_data.py       checks the data: notes, degrees, fingers, sources, spelling
  audit_pdf.py        reads the PDF back and checks every name, note, dot, finger, label and link
  audit_site.py       checks every page, link and diagram of the site, contrast and phone width
  preview.py          PNG renders of the PDF's pages
  design.toml         fonts and colours
  site/               the site's CSS and script
  guitar.json         chords-db, to check every citation of it
fonts/                JetBrains Mono, Noto Music
licenses/             the licences of the third-party files
.github/workflows/    on every push to master: build, run the checks, publish the site
```

The code holds no chords: it reads `data/` and computes degrees, note names, barres, positions and the order of each row. `make audit` runs three checks (data, PDF, site); each must end with `PROBLEMS: 0`, and the site is published only when all three pass.

## Sources and credits

The voicings and fingerings are cited from:

- JustinGuitar, Fender, JamPlay and fachords, tabs4acoustic, ChordBank;
- Guitar World, Guitar Player and MusicRadar, Acoustic Guitar magazine, guitar.com;
- Guitar For Dummies, Guitar Tricks, JG Music Lessons, Guitar Command;
- jazz-guitar-licks.com, jazzguitar.be, onlineguitarbooks.com;
- guitar-chord.org, guitar-chords.org.uk, Lauren Bateman, Mike Tyka's chord-shape tables and Wikipedia;
- chords-db (github.com/tombatossals/chords-db, MIT, in `src/guitar.json`) and its copies 8notes and akordy.kytary.cz: cited, never counted.

The note sets were checked with [pychord](https://github.com/yuma-m/pychord). Fonts: JetBrains Mono (text) and Noto Music (𝄪 𝄫).

## Licence

- The book, the website (its text and diagrams) and the chord data (`data/`), © 2026 dersergioni: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Free to share and adapt, even commercially, if you credit "Haus of Chords by dersergioni" with a link to https://github.com/dersergioni/haus-of-chords, link to the licence and say if you changed anything. See `LICENSE-CONTENT`.
- The code (`src/`, including the site's CSS and script): MIT. See `LICENSE`.
- Third-party files (`fonts/`, `src/guitar.json`) keep their own licences. See `licenses/`.
