"""Piano sight-reading exercises, written by rule.

    from sightread import LEVELS, compose, to_musicxml

compose(level, seed, ...) writes one exercise. It plans the harmony in four-bar phrases (the
first phrase pauses on the dominant, the last ends on the key note), writes a melody that sits
on the chord on strong beats and moves only by the steps and leaps its level allows, and, from
Level 3, a left hand that plays the chords from a fixed hand position. The same seed always
writes the same music. Standard library only.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

LETTERS = "CDEFGAB"
NATURAL = (0, 2, 4, 5, 7, 9, 11)
MAJOR = (0, 2, 4, 5, 7, 9, 11)
MINOR = (0, 2, 3, 5, 7, 8, 11)          # harmonic minor: the leading note is always raised


@dataclass(frozen=True)
class Key:
    name: str
    letter: int                         # index into LETTERS of the key note
    alter: int                          # -1 flat, +1 sharp
    minor: bool
    fifths: int

    @property
    def scale(self):
        return MINOR if self.minor else MAJOR

    @property
    def pc(self):
        return (NATURAL[self.letter] + self.alter) % 12

    @property
    def label(self):
        accidental = {1: "♯", -1: "♭"}.get(self.alter, "")
        return f"{LETTERS[self.letter]}{accidental} {'minor' if self.minor else 'major'}"

    def signature(self):
        """The alteration the key signature gives each letter."""
        sig = {letter: 0 for letter in LETTERS}
        for letter in ("FCGDAEB"[:self.fifths] if self.fifths > 0 else "BEADGCF"[:-self.fifths]):
            sig[letter] = 1 if self.fifths > 0 else -1
        return sig


KEYS = {k.name: k for k in (
    Key("C", 0, 0, False, 0), Key("G", 4, 0, False, 1), Key("D", 1, 0, False, 2), Key("A", 5, 0, False, 3),
    Key("F", 3, 0, False, -1), Key("Bb", 6, -1, False, -2), Key("Eb", 2, -1, False, -3),
    Key("Am", 5, 0, True, 0), Key("Em", 2, 0, True, 1), Key("Bm", 6, 0, True, 2), Key("F#m", 3, 1, True, 3),
    Key("Dm", 1, 0, True, -1), Key("Gm", 4, 0, True, -2), Key("Cm", 0, 0, True, -3),
)}


@dataclass(frozen=True)
class Level:
    n: int
    summary: str
    bars: tuple
    meters: tuple                       # beats in the bar (quarter notes)
    keys: tuple
    together: bool                      # hands together; else one hand at a time
    left: str                           # the left hand, hands together: root, dyad, broken, flowing
    span: tuple                         # the melody's range, in scale steps from the key note
    moves: tuple                        # (interval in scale steps, weight)
    tempo: tuple
    dynamics: int                       # 0 none, 1 one at the start, 2 one per phrase
    articulation: bool
    chromatic: bool


STEPS = ((0, 2), (1, 5), (-1, 5))
THIRDS = ((0, 1), (1, 5), (-1, 5), (2, 3), (-2, 3))
FOURTHS = THIRDS + ((3, 1), (-3, 1))
FIFTHS = FOURTHS + ((4, 1), (-4, 1))
SIXTHS = FIFTHS + ((5, .5), (-5, .5))

LEVELS = {lv.n: lv for lv in (
    Level(1, "One hand at a time, in a five-finger position. Steps and repeated notes; quarter, half "
             "and whole notes; 4/4; C and G major.",
          (4,), (4,), ("C", "G"), False, "", (0, 4), STEPS, (60, 72), 0, False, False),
    Level(2, "One hand at a time. Skips of a third; 3/4 as well as 4/4; dotted half notes; "
             "C, G and F major; a dynamic marking.",
          (8,), (4, 3), ("C", "G", "F"), False, "", (0, 4), THIRDS, (66, 80), 1, False, False),
    Level(3, "Hands together for the first time: the left hand holds one note a bar under a "
             "five-finger melody. Rests; A minor.",
          (8,), (4, 3), ("C", "G", "F", "Am"), True, "root", (0, 4), THIRDS, (66, 84), 1, False, False),
    Level(4, "The left hand plays two-note chords. The melody spans a sixth with leaps of a fourth; "
             "eighth notes; 2/4; keys to one sharp or flat, with E and D minor; dynamics per phrase.",
          (8,), (4, 3, 2), ("C", "G", "F", "D", "Am", "Em", "Dm"), True, "dyad", (0, 5), FOURTHS,
          (72, 92), 2, False, False),
    Level(5, "The left hand plays broken chords and waltz patterns. The melody spans an octave with "
             "leaps to a fifth; dotted rhythms; slurs and staccato; keys to two sharps or flats.",
          (8, 12), (4, 3, 2), ("C", "G", "F", "D", "Bb", "Am", "Em", "Dm", "Bm", "Gm"), True, "broken",
          (-1, 7), FIFTHS, (76, 100), 2, True, False),
    Level(6, "The left hand plays flowing eighth-note accompaniments. Leaps to a sixth; chromatic "
             "notes; 12 to 16 bars; keys to three sharps or flats.",
          (12, 16), (4, 3, 2),
          ("C", "G", "F", "D", "Bb", "A", "Eb", "Am", "Em", "Dm", "Bm", "Gm", "F#m", "Cm"), True, "flowing",
          (-1, 7), SIXTHS, (80, 112), 2, True, True),
)}

METRONOME = (56, 60, 63, 66, 69, 72, 76, 80, 84, 88, 92, 96, 100, 104, 108, 112, 116, 120)


def cells(level: int, beats: int):
    """The rhythms a bar may have at a level, in quarter notes (a negative length is a rest)."""
    c = {4: [[1, 1, 1, 1], [2, 1, 1], [1, 1, 2], [2, 2]], 3: [[1, 1, 1], [2, 1], [1, 2]], 2: [[1, 1], [2]]}[beats]
    if level >= 2:
        c += {4: [[3, 1], [1, 2, 1]], 3: [[3]], 2: []}[beats]
    if level >= 3:
        c += {4: [[1, -1, 1, 1], [2, 1, -1]], 3: [[1, -1, 1], [2, -1]], 2: [[1, -1]]}[beats]
    if level >= 4:
        c += {4: [[.5, .5, 1, 1, 1], [1, .5, .5, 2], [1, 1, .5, .5, 1]],
              3: [[.5, .5, 1, 1], [1, .5, .5, 1]], 2: [[.5, .5, 1], [1, .5, .5]]}[beats]
    if level >= 5:
        c += {4: [[1.5, .5, 1, 1], [1.5, .5, 2], [.5, .5, .5, .5, 2]],
              3: [[1.5, .5, 1], [2, .5, .5]], 2: [[1.5, .5], [.5, .5, .5, .5]]}[beats]
    if level >= 6:
        c += {4: [[.5, .5, .5, .5, 1, 1], [1, .5, .5, .5, .5, 1]],
              3: [[.5, .5, .5, .5, 1], [1, .5, .5, .5, .5]], 2: [[.5, .5, .5, .5]]}[beats]
    return c


def holds(level: int, beats: int):
    """Rhythms for a bar that pauses at the end of a phrase: its last note is long."""
    if level == 1:
        return {4: [[4], [2, 2]], 3: [[3]], 2: [[2]]}[beats]
    return {4: [[4], [2, 2], [1, 1, 2]], 3: [[3], [1, 2]], 2: [[2], [1, 1]]}[beats]


def finals(level: int, beats: int):
    """Rhythms for the last bar: the key note, long, reached by step from a weak beat or the bar before."""
    if level == 1:
        return {4: [[4]], 3: [[3]], 2: [[2]]}[beats]
    return {4: [[4], [1, 1, 2]], 3: [[3]], 2: [[2]]}[beats]


STRONG = {4: (0, 2), 3: (0,), 2: (0,)}
# semitones a leap of so many scale steps may span: no augmented or diminished intervals, no sevenths
GOOD_INTERVALS = {0: {0}, 1: {1, 2}, 2: {3, 4}, 3: {5}, 4: {7}, 5: {8, 9}, 7: {12}}
CHORD_TONES = {"I": (0, 2, 4), "IV": (3, 5, 0), "V": (4, 6, 1)}
# The left hand's chords in one hand position (scale steps; -1 is the leading note below)
ROOT = {"I": [0], "IV": [3], "V": [4]}
DYAD = {"I": [0, 4], "IV": [0, 5], "V": [-1, 4]}
TRIAD = {"I": [0, 2, 4], "IV": [0, 3, 5], "V": [-1, 3, 4]}

OPENING = (("I", "IV", "I", "V"), ("I", "V", "I", "V"), ("I", "I", "IV", "V"), ("I", "IV", "V", "V"))
CLOSING = (("I", "IV", "V", "I"), ("I", "V", "V", "I"), ("I", "I", "V", "I"))
MIDDLE = (("IV", "I", "IV", "V"), ("V", "I", "IV", "V"), ("IV", "IV", "I", "V"), ("V", "V", "I", "V"))


@dataclass
class Note:
    beat: float                          # where it starts in the bar, in quarter notes
    dur: float
    degrees: list                        # scale steps from the key note; empty for a rest
    chroma: int = 0                      # +1: raised a semitone (a chromatic note)
    finger: int | None = None
    dynamic: str | None = None
    slur: str | None = None              # "start" or "stop"
    staccato: bool = False


@dataclass
class Exercise:
    level: int
    key: Key
    beats: int
    hand: str                            # "right", "left" or "both"
    tempo: int
    seed: int
    chords: list
    melody: list                         # bars of Notes: the right hand, or the left hand alone
    accomp: list | None = None           # bars of Notes: the left hand, hands together
    tonic_melody: int = 60
    tonic_accomp: int = 48
    phrases: list = field(default_factory=list)

    @property
    def bars(self):
        return len(self.melody)

    @property
    def melody_clef(self):
        return "bass" if self.hand == "left" else "treble"

    def pitch(self, degree: int, part: str, chroma: int = 0):
        """(midi, letter, alter, octave) of a scale step in the melody or the accompaniment."""
        tonic = self.tonic_melody if part == "melody" else self.tonic_accomp
        octave, step = divmod(degree, 7)
        midi = tonic + 12 * octave + self.key.scale[step] + chroma
        letter = (self.key.letter + step) % 7
        alter = (midi - NATURAL[letter]) % 12
        alter = alter - 12 if alter > 6 else alter
        return midi, LETTERS[letter], alter, (midi - alter) // 12 - 1

    def events(self):
        """Every sounding note as (start, length, midi), in quarter notes from the start."""
        out = []
        for part, bars in (("melody", self.melody), ("accomp", self.accomp or [])):
            for b, bar in enumerate(bars):
                for n in bar:
                    for d in n.degrees:
                        out.append((b * self.beats + n.beat, n.dur, self.pitch(d, part, n.chroma)[0]))
        return sorted(out)

    def describe(self):
        hands = {"right": "right hand", "left": "left hand", "both": "hands together"}[self.hand]
        sounding = [self.pitch(d, "melody", n.chroma) for bar in self.melody for n in bar for d in n.degrees]
        low, high = min(sounding), max(sounding)
        return {
            "level": self.level, "key": self.key.label, "time": f"{self.beats}/4", "hands": hands,
            "bars": self.bars, "tempo": self.tempo, "seed": self.seed,
            "melody_range": [spelled(low), spelled(high)],
        }


def spelled(p) -> str:
    """A pitch from Exercise.pitch as a note name: F♯4, B♭3."""
    _, letter, alter, octave = p
    return letter + {-2: "𝄫", -1: "♭", 0: "", 1: "♯", 2: "𝄪"}[alter] + str(octave)


def name(midi: int) -> str:
    return ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"][midi % 12] + str(midi // 12 - 1)


def semitones(key: Key, a: int, b: int) -> int:
    def m(d):
        o, s = divmod(d, 7)
        return 12 * o + key.scale[s]
    return abs(m(a) - m(b))


# MARK: - Where the hands sit

def place_tonic(key: Key, lo: int, hi: int, clef: str, five_finger: bool) -> int:
    """The MIDI number of the key note for a part spanning scale steps lo..hi.

    Treble: the lowest position that keeps the part at or above middle C (the right hand's first
    positions start there), or, for wider parts, at or above A3 and under C6. Bass: the highest
    position that keeps the part at or under middle C (D4 for hands-together chords) and above E2."""
    def at(t, d):
        o, s = divmod(d, 7)
        return t + 12 * o + key.scale[s]
    options = [key.pc + 12 * o for o in range(2, 8)]
    if clef == "treble":
        floor = 60 if five_finger else 57
        fits = [t for t in options if at(t, lo) >= floor and at(t, hi) <= 84]
        return min(fits) if fits else min(t for t in options if at(t, lo) >= floor)
    ceiling = 60 if five_finger else 62
    fits = [t for t in options if at(t, lo) >= 40 and at(t, hi) <= ceiling]
    return max(fits) if fits else min(t for t in options if at(t, lo) >= 40)


# MARK: - Composing

class Writer:
    def __init__(self, level: Level, key: Key, beats: int, rng: random.Random):
        self.level, self.key, self.beats, self.rng = level, key, beats, rng
        self.lo, self.hi = level.span
        self.weights = dict(level.moves)

    def allowed(self, prev: int, d: int, prev_move: int, run: int) -> bool:
        if not self.lo <= d <= self.hi:
            return False
        move = d - prev
        if move not in self.weights:
            return False
        if semitones(self.key, prev, d) not in GOOD_INTERVALS[abs(move)]:
            return False                                    # augmented and diminished intervals
        if move == 0 and run >= 3:                          # no more than three of one note
            return False
        if abs(prev_move) >= 3 and (move == 0 or move * prev_move > 0 or abs(move) > 2):
            return False                                    # after a leap, turn back by step or third
        return True

    def bar(self, cell, chord, prev, prev_move, run, start=None, target=None, before=None, goal=None, avoid=None):
        """Degrees for the notes of one bar. `start` fixes the first note; `target` limits the
        last; `before` limits the note before the last (to step into a target in the next bar
        or this one). `goal` is the note the line heads for; `avoid` is a bar not to repeat."""
        slots, lengths, t = [], [], 0.0
        for c in cell:
            if c > 0:
                slots.append(t)
                lengths.append(c)
            t += abs(c)
        for _ in range(400):
            p, pm, r, degs, ok = prev, prev_move, run, [], True
            for i, onset in enumerate(slots):
                if i == 0 and start is not None:
                    d, pm, r = start, 0, 0
                else:
                    cands = [p + m for m in self.weights if self.allowed(p, p + m, pm, r)]
                    if self.key.minor:
                        # the raised seventh belongs to the dominant chord, or steps up to the key note
                        if p % 7 == 6 and chord != "V":
                            cands = [d for d in cands if d == p + 1]
                        cands = [d for d in cands if d % 7 != 6 or chord == "V"
                                 or (i == len(slots) - 2 and target and d + 1 in target)]
                    if i == len(slots) - 1 and target is not None:
                        cands = [d for d in cands if d in target]
                    elif i == len(slots) - 2 and before is not None:
                        cands = [d for d in cands if d in before]
                    if lengths[i] == .5 or (i and lengths[i - 1] == .5):
                        cands = [d for d in cands if abs(d - p) <= 2]       # no leaps into or out of eighths
                    if onset in STRONG[self.beats]:
                        cands = [d for d in cands if d % 7 in CHORD_TONES[chord]]
                    elif self.level.n >= 2:
                        cands = [d for d in cands if d % 7 in CHORD_TONES[chord] or abs(d - p) <= 1]
                    if not cands:
                        ok = False
                        break
                    d = self.rng.choices(cands, [self.weight(p, d, pm, goal) for d in cands])[0]
                    pm = d - p
                r = r + 1 if d == p else 1
                p = d
                degs.append(d)
            if ok and degs != avoid:
                return degs, p, pm, r
        return None

    def weight(self, prev, d, prev_move, goal):
        move = d - prev
        w = self.weights[move]
        if goal is not None:                                # phrases climb to a high point, then fall
            w *= 3 if abs(d - goal) < abs(prev - goal) else .4 if abs(d - goal) > abs(prev - goal) else 1
        if move == 0 and prev_move == 0:
            w *= .3                                         # one repeated note is plenty
        return w


def harmony(bars: int, rng: random.Random):
    """Chords bar by bar, and each phrase's role: open (ends on V), middle (ends on V), close."""
    roles = {4: ["close"], 8: ["open", "close"], 12: ["open", "middle", "close"],
             16: ["open", "close", "middle", "close"]}[bars]
    chords = []
    for role in roles:
        chords += rng.choice({"open": OPENING, "middle": MIDDLE, "close": CLOSING}[role])
    return chords, roles


def compose(level_n: int, seed: int, key: str | None = None, beats: int | None = None,
            hand: str | None = None, bars: int | None = None) -> Exercise:
    """One exercise. `hand`: "right" or "left" (one hand) or "both" (Level 3 and up)."""
    level = LEVELS[level_n]
    if hand == "both" and not level.together:
        raise ValueError(f"Level {level_n} is one hand at a time; hands together starts at Level 3")
    for attempt in range(80):
        rng = random.Random(seed * 1000 + attempt)
        ex = _compose(level, KEYS[key or rng.choice(level.keys)], beats or rng.choice(level.meters),
                      hand or ("both" if level.together else "right"), bars or rng.choice(level.bars), seed, rng)
        if ex is not None and not check(ex):
            return ex
    raise RuntimeError(f"could not write an exercise for level {level_n}, seed {seed}")


def _compose(level: Level, key: Key, beats: int, hand: str, n_bars: int, seed: int, rng: random.Random):
    w = Writer(level, key, beats, rng)
    chords, roles = harmony(n_bars, rng)
    normal = cells(level.n, beats)
    tonics = [t for t in (0, 7) if w.lo <= t <= w.hi]
    neighbours = {t + s for t in tonics for s in (-1, 1) if w.lo <= t + s <= w.hi}
    end_cells = [rng.choice(finals(level.n, beats) if role == "close" else holds(level.n, beats)) for role in roles]

    melody, rhythms, opening = [], [], []          # opening: the first phrase's first two bars
    prev, pm, run = None, 0, 0
    for b in range(n_bars):
        phrase, place = divmod(b, 4)
        role, chord = roles[phrase], chords[b]
        final, cadence = b == n_bars - 1, place == 3 and b != n_bars - 1
        closes = place == 3 and role == "close"             # this bar ends on the key note
        one_note_end = sum(1 for c in end_cells[phrase] if c > 0) == 1

        # A closing phrase after the first begins as the first did (one or two bars).
        if phrase and role == "close" and place < 2 and place < len(opening) and chord == chords[place]                 and (place == 0 or len(melody[-1]) and rhythms[-1] == opening[0][0]):
            cell, degs = opening[place]
            if place == 0 or w.allowed(prev, degs[0], pm, run):
                melody.append(_notes(cell, degs))
                rhythms.append(cell)
                prev, pm, run = degs[-1], (degs[-1] - degs[-2]) if len(degs) > 1 else 0, 1
                continue

        # rhythm
        if place == 3:
            cell = end_cells[phrase]
        elif place == 2 and rng.random() < .4 and min(rhythms[b - 2]) > 0:
            cell = rhythms[b - 2]                       # the phrase's first rhythm comes back
        else:
            options = [c for c in normal if min(c) > 0 or (place != 0 and b != n_bars - 2)]
            weights = [sum(1 for x in c if x > 0) * (.3 if rhythms and c == rhythms[-1] else 1) for c in options]
            cell = rng.choices(options, weights)[0]

        # where the notes must go
        start = target = before = None
        if closes:
            target = set(tonics)
            if not one_note_end:
                before = neighbours
        elif place == 3:
            target = {d for d in range(w.lo, w.hi + 1) if d % 7 in (1, 4)}
        elif place == 2 and role == "close" and one_note_end:
            target = neighbours                         # step into the key note
        if b == 0:
            choices = [d for d in (0, 2, 4) if w.lo <= d <= w.hi]
            start = rng.choices(choices, [3, 2, 1][:len(choices)])[0]
        elif place == 0:
            tones = [d for d in range(w.lo, w.hi + 1) if d % 7 in CHORD_TONES[chord] and abs(d - prev) <= 4]
            start = rng.choices(tones, [1 + (d > prev) for d in tones])[0] if tones else prev

        if place == 0:
            peak = rng.choices([w.hi - 2, w.hi - 1, w.hi], [1, 2, 2])[0]
        goal = peak if place < 2 else (0 if role == "close" else 1)
        avoid = [n.degrees[0] for n in melody[-1] if n.degrees] if melody and rhythms[-1] == cell else None
        got = w.bar(cell, chord, prev if prev is not None else start, pm, run, start, target, before, goal, avoid)
        if got is None:
            return None
        degs, prev, pm, run = got
        melody.append(_notes(cell, degs))
        rhythms.append(cell)
        if phrase == 0 and place < 2:
            opening.append((cell, degs))

    ex = Exercise(level.n, key, beats, hand, 0, seed, chords, melody)
    ex.tonic_melody = place_tonic(key, w.lo, w.hi, ex.melody_clef, w.lo >= 0 and w.hi - w.lo <= 5)
    if hand == "both":
        ex.accomp = [_left(level.left, chords[b], beats, b == n_bars - 1) for b in range(n_bars)]
        ex.tonic_accomp = place_tonic(key, -1, 5, "bass", False)
    ex.tempo = rng.choice([t for t in METRONOME if level.tempo[0] <= t <= level.tempo[1]])
    ex.phrases = roles
    _mark(ex, level, rng)
    return ex


def _notes(cell, degs):
    out, t, k = [], 0.0, 0
    for c in cell:
        if c > 0:
            out.append(Note(t, c, [degs[k]]))
            k += 1
        else:
            out.append(Note(t, -c, []))
        t += abs(c)
    return out


def _left(style: str, chord: str, beats: int, final: bool):
    if final:
        shape = {"root": ROOT, "dyad": DYAD}.get(style, TRIAD)[chord]
        return [Note(0, beats, list(shape))]
    if style == "root":
        return [Note(0, beats, list(ROOT[chord]))]
    if style == "dyad":
        return [Note(0, beats, list(DYAD[chord]))]
    low, mid, top = TRIAD[chord]
    if style == "broken":
        if beats == 4:
            return [Note(i, 1, [d]) for i, d in enumerate((low, top, mid, top))]
        return [Note(0, 1, [low])] + [Note(i, 1, [mid, top]) for i in range(1, beats)]
    pattern = {4: (low, top, mid, top, low, top, mid, top), 3: (low, top, mid, top, mid, top),
               2: (low, top, mid, top)}[beats]
    return [Note(i * .5, .5, [d]) for i, d in enumerate(pattern)]


def _mark(ex: Exercise, level: Level, rng: random.Random):
    """Fingering for the first notes, dynamics, slurs, staccato and chromatic notes."""
    notes = [n for bar in ex.melody for n in bar if n.degrees]
    every = [n.degrees[0] for n in notes]
    opening = [n.degrees[0] for bar in ex.melody[:2] for n in bar if n.degrees]
    if max(every) - level.span[0] <= 4:
        position = level.span[0]                        # the whole piece sits in one five-finger position
    elif max(opening) - min(opening) <= 4:
        position = min(opening) if ex.hand != "left" else max(opening) - 4
    else:
        position = None
    if position is not None:
        first = every[0]
        notes[0].finger = position + 4 - first + 1 if ex.hand == "left" else first - position + 1
    if ex.accomp:
        ex.accomp[0][0].finger = 5

    if level.dynamics:
        a, b = rng.choice([("p", "f"), ("f", "p"), ("mf", "p"), ("p", "mf"), ("mf", "f")])
        for phrase in range(len(ex.phrases) if level.dynamics == 2 else 1):
            first_note = next(n for n in ex.melody[phrase * 4] if n.degrees)
            first_note.dynamic = (a, b)[phrase % 2]

    if level.articulation:
        for g in range(0, ex.bars, 2):
            group = [n for bar in ex.melody[g:g + 2] for n in bar]
            sounding = [n for n in group if n.degrees]
            roll = rng.random()
            if roll < .5 and len(sounding) >= 3 and all(n.degrees for n in group):
                sounding[0].slur, sounding[-1].slur = "start", "stop"
            elif roll < .75:
                for n in sounding[:-1]:
                    if n.dur == 1:
                        n.staccato = True

    if level.chromatic:
        budget = ex.bars // 4
        for b, bar in enumerate(ex.melody):
            if budget == 0:
                break
            for i in range(1, len(bar) - 1):
                n, nxt, pre = bar[i], bar[i + 1], bar[i - 1]
                if not (n.degrees and nxt.degrees and pre.degrees) or n.beat in STRONG[ex.beats] or n.slur:
                    continue
                d, after, before = n.degrees[0], nxt.degrees[0], pre.degrees[0]
                if after - d == 1 and semitones(ex.key, d, after) == 2 and before != d - 1 \
                        and semitones(ex.key, before, d) + (1 if before < d else -1) not in (3, 6) \
                        and rng.random() < .5:
                    n.chroma = 1
                    budget -= 1
                    break


# MARK: - MusicXML

DIVISIONS = 2
TYPES = {.5: ("eighth", 0), 1: ("quarter", 0), 1.5: ("quarter", 1), 2: ("half", 0), 3: ("half", 1), 4: ("whole", 0)}
ACCIDENTAL = {-2: "flat-flat", -1: "flat", 0: "natural", 1: "sharp", 2: "double-sharp"}


def _beams(bar, beats):
    """Begin/continue/end for runs of eighths within a beam group (half a bar in 4/4, a beat otherwise)."""
    window = 2 if beats == 4 else 1
    marks, run = [None] * len(bar), []

    def close():
        if len(run) >= 2:
            for j, i in enumerate(run):
                marks[i] = "begin" if j == 0 else "end" if j == len(run) - 1 else "continue"
        run.clear()
    for i, n in enumerate(bar):
        if n.dur == .5 and n.degrees and (not run or int(bar[run[0]].beat // window) == int(n.beat // window)):
            run.append(i)
        else:
            close()
            if n.dur == .5 and n.degrees:
                run.append(i)
    close()
    return marks


def to_musicxml(ex: Exercise, title: str = "") -> str:
    two = ex.accomp is not None
    sig = ex.key.signature()
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
           '"http://www.musicxml.org/dtds/partwise.dtd">',
           '<score-partwise version="4.0">']
    if title:
        out.append(f"  <movement-title>{escape(title)}</movement-title>")
    out += ['  <identification><encoding><software>SightTune sight-reading</software></encoding></identification>',
            '  <part-list><score-part id="P1"><part-name print-object="no">Piano</part-name></score-part></part-list>',
            '  <part id="P1">']
    bar_len = ex.beats * DIVISIONS
    for b in range(ex.bars):
        out.append(f'    <measure number="{b + 1}">')
        if b and b % 4 == 0:
            out.append('      <print new-system="yes"/>')
        if b == 0:
            clefs = ('<clef number="1"><sign>G</sign><line>2</line></clef>'
                     '<clef number="2"><sign>F</sign><line>4</line></clef>') if two else (
                '<clef><sign>F</sign><line>4</line></clef>' if ex.melody_clef == "bass"
                else '<clef><sign>G</sign><line>2</line></clef>')
            out.append(f'      <attributes><divisions>{DIVISIONS}</divisions>'
                       f'<key><fifths>{ex.key.fifths}</fifths><mode>{"minor" if ex.key.minor else "major"}</mode></key>'
                       f'<time><beats>{ex.beats}</beats><beat-type>4</beat-type></time>'
                       f'{"<staves>2</staves>" if two else ""}{clefs}</attributes>')
            out.append('      <direction placement="above"><direction-type><metronome parentheses="no">'
                       f'<beat-unit>quarter</beat-unit><per-minute>{ex.tempo}</per-minute></metronome>'
                       f'</direction-type>{"<staff>1</staff>" if two else ""}<sound tempo="{ex.tempo}"/></direction>')
        out += _staff(ex, ex.melody[b], "melody", 1, 1, two, sig, above=ex.hand != "left")
        if two:
            out.append(f'      <backup><duration>{bar_len}</duration></backup>')
            out += _staff(ex, ex.accomp[b], "accomp", 2, 5, two, sig, above=False)
        if b == ex.bars - 1:
            out.append('      <barline location="right"><bar-style>light-heavy</bar-style></barline>')
        out.append('    </measure>')
    out += ['  </part>', '</score-partwise>', '']
    return "\n".join(out)


def _staff(ex, bar, part, staff, voice, two, sig, above):
    lines, shown = [], {}
    staff_tag = f"<staff>{staff}</staff>" if two else ""
    beams = _beams(bar, ex.beats)
    for i, n in enumerate(bar):
        if n.dynamic:
            lines.append(f'      <direction placement="below"><direction-type><dynamics><{n.dynamic}/></dynamics>'
                         f'</direction-type>{staff_tag}</direction>')
        kind, dot = TYPES[n.dur]
        dur = int(n.dur * DIVISIONS)
        dots = "<dot/>" * dot
        if not n.degrees:
            whole = n.dur == ex.beats
            rest = '<rest measure="yes"/>' if whole else "<rest/>"
            type_tag = "" if whole else f"<type>{kind}</type>{dots}"
            lines.append(f"      <note>{rest}<duration>{dur}</duration><voice>{voice}</voice>{type_tag}{staff_tag}</note>")
            continue
        for j, d in enumerate(sorted(n.degrees)):
            midi, letter, alter, octave = ex.pitch(d, part, n.chroma)
            current = shown.get((letter, octave), sig[letter])
            accidental = f"<accidental>{ACCIDENTAL[alter]}</accidental>" if alter != current else ""
            shown[(letter, octave)] = alter
            alter_tag = f"<alter>{alter}</alter>" if alter else ""
            extra = ""
            if j == 0:
                if beams[i]:
                    extra += f'<beam number="1">{beams[i]}</beam>'
                notations = ""
                if n.finger:
                    notations += (f'<technical><fingering placement="{"above" if above else "below"}">'
                                  f'{n.finger}</fingering></technical>')
                if n.staccato:
                    notations += "<articulations><staccato/></articulations>"
                if n.slur:
                    notations += f'<slur type="{n.slur}" number="1"/>'
                if notations:
                    extra += f"<notations>{notations}</notations>"
            chord = "<chord/>" if j else ""
            lines.append(f"      <note>{chord}<pitch><step>{letter}</step>{alter_tag}<octave>{octave}</octave></pitch>"
                         f"<duration>{dur}</duration><voice>{voice}</voice><type>{kind}</type>{dots}"
                         f"{accidental}{staff_tag}{extra}</note>")
    return lines


# MARK: - Checks

def check(ex: Exercise) -> list:
    """What's wrong with an exercise, if anything (empty when it keeps every rule)."""
    problems = []
    lv = LEVELS[ex.level]
    for b, bar in enumerate(ex.melody):
        if abs(sum(n.dur for n in bar) - ex.beats) > 1e-9:
            problems.append(f"bar {b + 1}: melody doesn't fill the bar")
    for b, bar in enumerate(ex.accomp or []):
        if abs(sum(n.dur for n in bar) - ex.beats) > 1e-9:
            problems.append(f"bar {b + 1}: left hand doesn't fill the bar")
    degs = [n.degrees[0] for bar in ex.melody for n in bar if n.degrees]
    if min(degs) < lv.span[0] or max(degs) > lv.span[1]:
        problems.append("melody leaves its range")
    if degs[-1] % 7 != 0:
        problems.append("melody doesn't end on the key note")
    if abs(degs[-1] - degs[-2]) != 1 and len([n for n in ex.melody[-1] if n.degrees]) == 1:
        problems.append("the last note isn't reached by step")
    moves = {m for m, _ in lv.moves}
    for a, c in zip(degs, degs[1:]):
        if c - a not in moves and abs(c - a) > 4:
            problems.append(f"leap of {c - a} steps")
    midis = [m for _, _, m in ex.events()]
    if ex.hand != "left" and min(m for m in (ex.pitch(d, 'melody')[0] for d in degs)) < 57:
        problems.append("right hand too low")
    if ex.accomp:
        low_right = min(ex.pitch(d, "melody")[0] for d in degs)
        high_left = max(ex.pitch(d, "accomp")[0] for bar in ex.accomp for n in bar for d in n.degrees)
        if low_right <= high_left:
            problems.append("hands overlap")
    if not midis:
        problems.append("no notes")
    if ex.key.minor:
        flat = [(b, n) for b, bar in enumerate(ex.melody) for n in bar if n.degrees]
        for (b, n), (_, nxt) in zip(flat, flat[1:]):
            if n.degrees[0] % 7 == 6 and ex.chords[b] != "V" and nxt.degrees[0] != n.degrees[0] + 1:
                problems.append(f"bar {b + 1}: raised seventh off the dominant, unresolved")
    return problems
