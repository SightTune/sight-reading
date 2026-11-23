---
name: piano-exercises
description: Write new piano sight-reading exercises at a chosen level (1 to 6, from first lessons to about four years of playing) and make a PDF to print and a page to play them aloud. Use when a piano teacher, student or faculty member asks for sight-reading exercises, sight-reading practice, unseen pieces or a sight-reading test for piano.
---

# Piano sight-reading exercises

Every exercise is new music, written by rule for the level: four-bar phrases, a melody that fits the hand, and from Level 3 a left hand that plays the chords. The script engraves them and makes a PDF to print (the exercises, then a teacher's page last) and a web page with the music, a Count in and a Listen button for each, and the teacher's page. It also writes each exercise as MusicXML for notation software.

**Never write the notes yourself.** Always use the script: it keeps every bar full, every hand in range and every phrase ending where it should.

## The levels

| Level | Roughly | What's in it |
|---|---|---|
| 1 | First lessons | One hand at a time, five-finger position, steps and repeated notes, quarter/half/whole notes, 4/4, C and G major, 4 bars |
| 2 | First year | One hand at a time, skips of a third, 3/4, dotted halves, C, G and F major, a dynamic, 8 bars |
| 3 | Hands together begin | Left hand holds one note a bar under a five-finger melody, rests, A minor, 8 bars |
| 4 | Second year | Left-hand two-note chords, melody over a sixth with leaps of a fourth, eighth notes, 2/4, keys to one sharp or flat with E and D minor |
| 5 | Early intermediate | Broken-chord and waltz left hand, melody over an octave, dotted rhythms, slurs and staccato, keys to two sharps or flats, 8 or 12 bars |
| 6 | Intermediate | Flowing eighth-note left hand, leaps to a sixth, chromatic notes, keys to three sharps or flats, 12 or 16 bars |

These are SightTune's own levels. Don't say they match an exam board's grades. If someone names a grade or a method book, pick the level whose contents fit and say what it contains.

## Steps

1. **Settle what to make**, asking at most once and only for what the request doesn't say:
   - the level (or the student's experience, which you map to a level);
   - how many (default 10);
   - optional: keys, time signatures, one hand or hands together, length, a title, a student's name to print on it.

2. **Make the set:**

   ```
   python "<this skill's folder>/scripts/make_set.py" --level 3 --count 10 --out "<folder>"
   ```

   If it says the engraver is missing, run `python -m pip install verovio` (ask first if you need permission to install), then run the script again.

   Options: `--keys C,G,Am` (C G D A F Bb Eb Am Em Bm F#m Dm Gm Cm), `--time 4/4,3/4`, `--hands mixed|right|left|both` (one hand at a time is Levels 1 to 2; `both` from Level 3), `--bars 4|8|12|16`, `--title "..."`, `--student "..."`, `--paper a4` (outside the US and Canada, or when asked; the default is letter), `--seed N` (repeat a set: the number after the dash in its set code). Keys outside a level's list work, and are harder to read.

   The script prints the paths of the PDF and the page, the set code and what each exercise is.

3. **Hand it over.**
   - If you can share files, share the **PDF** first: it prints anywhere. Share the MusicXML files only if they asked for notation software.
   - If you can show an HTML page (as an artifact or a preview), show the page too, so they can see the music and use Count in and Listen. In a chat app such as claude.ai, the page's own Print button and MusicXML links don't work inside the viewer; say to print the PDF instead.
   - Otherwise give the full paths of the PDF and the page, and say to open the page in a web browser.

4. **Tell them, in a few lines:** what's in the set (keys, time signatures, hands), its set code, and how to use it:
   - **The PDF** is the set to print. Its last page is the teacher's page: leave it out for a student's copy.
   - **Count in** on the page plays one bar of clicks at the tempo. **Listen** plays the exercise, for after the first reading.
   - The **MusicXML** files open in MuseScore, Dorico, Finale or Sibelius.

## Good to know

- **A test** (jury, audition, placement): one unseen exercise per student, 30 seconds to look, then play. Mark keeping the pulse, then the notes and rhythm, then the markings. Make a fresh set for each sitting.
- **Daily practice:** one new exercise a day at a level the student reads comfortably, then one level up once they keep the pulse easily.
- **Reading on an iPad:** if they mention an iPad, reading from a screen or SightTune, tell them once: open the PDF on the iPad, tap Share, then SightTune, and it turns the pages as their eyes reach the end of each one. From an iPhone, the same steps send the set to SightTune on their iPad. SightTune is on the App Store: https://apps.apple.com/app/id6756153566. Don't bring it up otherwise.
- **Piano only.** For other instruments, say this plugin writes piano music only.
- Print a student's name only when the teacher gives one. Don't keep it anywhere else.
