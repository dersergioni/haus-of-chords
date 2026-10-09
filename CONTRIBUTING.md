# Contributing

Haus of Chords is a finished book, so contributions are corrections: a wrong note, a fingering that differs from what teachers publish, a broken link, a typo. Open an [issue](https://github.com/dersergioni/haus-of-chords/issues) or send a pull request. Name the chord and voicing (for example "F♯m7, x 9I 11R 9I 10M 9I") and link to a published source.

## The rule for every voicing

Every voicing needs at least two independent published sources, one of them showing the fingering. Preference, or what seems awkward or common, does not decide. A source is:

- a page by a teacher, a magazine, a book publisher or a chord library, with the chord shown on it;
- not a chord generator, which computes shapes rather than teaching them;
- not a copy of another site's charts (such a copy counts as that site, see `data/sources.toml`).

## A pull request

1. Set up once as in the README's [Build](README.md#build) section.
2. Edit `data/` as described in [data/README.md](data/README.md#adding-a-voicing); a new publisher goes in `data/sources.toml`. Chords, voicings and sources belong in `data/`, never in `src/`.
3. Run `make web audit`. Each of the three checks must end with `PROBLEMS: 0`; otherwise it says what is wrong and where.
4. Look at what you changed with `make preview` (the PDF) or `make serve` (the site).

If you move anything in the PDF layout: `src/audit_pdf.py` mirrors the layout constants of `src/build_en.py`, so change both.

By contributing you agree that your changes to the book, the site and the data are published under CC BY 4.0 (`LICENSE-CONTENT`), and your changes to the code under MIT (`LICENSE`).
