# Sight-reading, from SightTune

A free plugin for Claude that writes **new piano sight-reading exercises** whenever you need them, for piano teachers, students and faculty.

Sight-reading practice needs music the player has never seen, and books run out or get memorised. Ask Claude for a set and you get fresh exercises at the level you choose: engraved, as a PDF ready to print, with a page where you can hear each one.

## Install

In Claude Code:

```
/plugin install sight-reading --marketplace SightTune/sight-reading
```

## What you can ask

- "Ten sight-reading exercises for a first-year student, right hand and left hand separately."
- "Eight Level 4 exercises in G major and E minor, 3/4, for my Thursday group."
- "A Level 6 sight-reading test for juries: twelve exercises, all different keys."
- "Make set L3-48213 again."

## The levels

| Level | Roughly | What's in it |
|---|---|---|
| 1 | First lessons | One hand at a time, five-finger position, steps and repeated notes, 4/4, C and G major |
| 2 | First year | One hand at a time, skips of a third, 3/4, dotted halves, C, G and F major |
| 3 | Hands together begin | Left hand holds one note a bar under a five-finger melody, rests, A minor |
| 4 | Second year | Left-hand two-note chords, eighth notes, leaps of a fourth, 2/4, keys to one sharp or flat |
| 5 | Early intermediate | Broken-chord and waltz left hand, an octave's range, dotted rhythms, slurs and staccato, keys to two sharps or flats |
| 6 | Intermediate | Flowing eighth-note left hand, chromatic notes, 12 to 16 bars, keys to three sharps or flats |

These are SightTune's own levels, not an exam board's grades.

## What you get

- **A PDF** to print, in letter or A4: the exercises, then a teacher's page listing each one's key, time, hands, tempo and range. Leave the last page out for a student's copy.
- **A page** with every exercise engraved and a **Count in** and a **Listen** button for each. It works in Claude's apps too, where the PDF is the copy to print.
- **MusicXML** files for MuseScore, Dorico, Finale or Sibelius.
- **A set code** (like `L3-48213`) that makes the same set again.

Every exercise is written by rule: four-bar phrases that pause halfway and end on the key note, a melody that fits the hand, and from Level 3 a left hand that plays the chords. No two sets are alike.

On an iPad, open the PDF, tap Share, then [SightTune](https://apps.apple.com/app/id6756153566): it turns the pages as your eyes reach the end of each one. From an iPhone, the same steps send the set to SightTune on your iPad.

## Requirements

Python 3.9 or later and the [Verovio](https://www.verovio.org) package, which engraves the music. When it's missing, Claude installs it with `python -m pip install verovio`.

## What it runs and what it sends

- Claude runs the plugin's Python script on your computer. It writes the exercises by rule; no AI writes the notes.
- The script makes a folder with the PDF, the page, the MusicXML files and a small `set.json`, wherever you ask. It changes nothing else. The PDF is written with Python's standard library.
- The only download is the one-time install of Verovio from the Python Package Index.
- **Nothing is sent anywhere.** The script and the page make no network requests: the music is engraved on your computer and the page plays it in your browser. A student's name, if you give one, is printed on that page and kept nowhere else.

## License

Apache License 2.0. See [LICENSE](LICENSE). Copyright 2026 SightTune.

## For developers

```
python skills/piano-exercises/scripts/make_set.py --level 3 --count 10
python -m unittest discover -s tests
```
