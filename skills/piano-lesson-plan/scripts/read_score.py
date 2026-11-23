"""Read a piano score in MusicXML and say what the player has to manage in it.

    python read_score.py <score.musicxml | score.xml | score.mxl>

Prints JSON: the title, key and time (and any changes), tempo, length, each hand's range,
largest leap, chords and rhythms, the busiest bars, roughly which sight-reading level the
piece sits at and why, and the options for a matching sight-reading set from the
piano-exercises skill. It reads the file only. Standard library only.
"""
from __future__ import annotations

import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTERS = "CDEFGAB"
MAX_BYTES = 30_000_000

# The keys the exercise writer has, and the first level that uses each. These follow
# piano-exercises/scripts/sightread.py LEVELS (a test checks they still agree).
KEY_LEVEL = {"C": 1, "G": 1, "F": 2, "Am": 3, "D": 4, "Em": 4, "Dm": 4,
             "Bb": 5, "Bm": 5, "Gm": 5, "A": 6, "Eb": 6, "F#m": 6, "Cm": 6}
METER_LEVEL = {4: 1, 3: 2, 2: 4}    # beats in a bar of quarter notes
BEYOND = 7                          # past Level 6

MAJOR = {-7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F", 0: "C",
         1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#"}
MINOR = {-7: "Abm", -6: "Ebm", -5: "Bbm", -4: "Fm", -3: "Cm", -2: "Gm", -1: "Dm", 0: "Am",
         1: "Em", 2: "Bm", 3: "F#m", 4: "C#m", 5: "G#m", 6: "D#m", 7: "A#m"}

# Note values, in quarter notes, with the first level that uses each.
VALUES = {4: ("whole notes", 1), 3: ("dotted half notes", 2), 2: ("half notes", 1),
          1.5: ("dotted quarter notes", 5), 1: ("quarter notes", 1), 0.75: ("dotted eighth notes", BEYOND),
          0.5: ("eighth notes", 4), 0.375: ("dotted sixteenth notes", BEYOND),
          0.25: ("sixteenth notes", BEYOND), 0.125: ("thirty-second notes", BEYOND), 8: ("breves", 1)}
TYPE_QUARTERS = {"breve": 8, "whole": 4, "half": 2, "quarter": 1, "eighth": 0.5, "16th": 0.25,
                 "32nd": 0.125, "64th": 0.0625}


def key_code(fifths: int, minor: bool) -> str:
    fifths = max(-7, min(7, fifths))
    return (MINOR if minor else MAJOR)[fifths]


def key_label(code: str) -> str:
    minor = code.endswith("m")
    root = code[:-1] if minor else code
    root = root[0] + root[1:].replace("#", "♯").replace("b", "♭")
    return f"{root} {'minor' if minor else 'major'}"


def pitch_name(step: str, alter: int, octave: int) -> str:
    return f"{step}{'♯' * alter if alter > 0 else '♭' * -alter}{octave}"


def interval_name(semitones: int) -> str:
    names = {0: "a repeated note", 1: "a second", 2: "a second", 3: "a third", 4: "a third", 5: "a fourth",
             6: "a tritone", 7: "a fifth", 8: "a sixth", 9: "a sixth", 10: "a seventh", 11: "a seventh",
             12: "an octave"}
    return names.get(semitones, f"more than an octave ({semitones} semitones)")


def signature(fifths: int) -> dict:
    sig = {letter: 0 for letter in LETTERS}
    for letter in ("FCGDAEB"[:fifths] if fifths > 0 else "BEADGCF"[:-fifths]):
        sig[letter] = 1 if fifths > 0 else -1
    return sig


def load(path: str) -> ET.Element:
    if os.path.getsize(path) > MAX_BYTES:
        sys.exit("That file is too large to be a single score.")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            name = None
            try:
                container = ET.fromstring(z.read("META-INF/container.xml"))
                rootfile = container.find(".//{*}rootfile")
                name = rootfile.get("full-path") if rootfile is not None else None
            except (KeyError, ET.ParseError):
                pass
            if name not in z.namelist():
                name = None
            if not name:
                name = next((n for n in z.namelist() if n.lower().endswith((".xml", ".musicxml"))
                             and not n.startswith("META-INF")), None)
            if not name:
                sys.exit("No MusicXML score inside that .mxl file.")
            if z.getinfo(name).file_size > MAX_BYTES:
                sys.exit("That file is too large to be a single score.")
            data = z.read(name)
    else:
        with open(path, "rb") as f:
            data = f.read()
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        sys.exit(f"That isn't a readable MusicXML file ({e}).")
    if root.tag == "score-timewise":
        sys.exit("This is timewise MusicXML. Export the score again as ordinary (partwise) MusicXML.")
    if root.tag != "score-partwise":
        sys.exit("That isn't a MusicXML score.")
    return root


def choose_part(root: ET.Element):
    """The piano part: the one on two staves, else one named piano, else the first."""
    parts = root.findall("part")
    if not parts:
        sys.exit("The score has no parts.")
    names = {sp.get("id"): (sp.findtext("part-name") or "").strip() for sp in root.findall("part-list/score-part")}

    def staves(p):
        return max([int(s.text) for s in p.iter("staves") if (s.text or "").strip().isdigit()] or [1])

    def rank(i_p):
        i, p = i_p
        return (staves(p) == 2, "piano" in names.get(p.get("id"), "").lower(), -i)

    _, part = max(enumerate(parts), key=rank)
    others = [names.get(p.get("id")) or p.get("id") for p in parts if p is not part]
    return part, names.get(part.get("id")) or "", staves(part), others


def quarters(note: ET.Element, divisions: int) -> float | None:
    """A note's written value in quarter notes, from its type and dots, else its duration."""
    kind = note.findtext("type")
    if kind in TYPE_QUARTERS:
        value = TYPE_QUARTERS[kind]
        add = value
        for _ in note.findall("dot"):
            add /= 2
            value += add
        return value
    duration = note.findtext("duration")
    if duration and duration.strip().lstrip("-").isdigit() and divisions:
        return int(duration) / divisions
    return None


def analyse(root: ET.Element) -> dict:
    part, part_name, n_staves, others = choose_part(root)
    title = (root.findtext("work/work-title") or root.findtext("movement-title") or "").strip()
    composer = ""
    for creator in root.findall("identification/creator"):
        if creator.get("type") == "composer":
            composer = (creator.text or "").strip()

    divisions, fifths, minor = 1, 0, False
    keys, times, tempo, modes = [], [], None, set()
    beats = beat_type = None
    sig = signature(0)
    raised = set()                       # (letter, alter) the minor key raises: its 6th and 7th
    bars = []                            # per bar: {"n", "onsets": {staff: n}, "accidentals", "leaps"}
    stats = defaultdict(lambda: {"low": None, "high": None, "chord": 1, "leap": 0, "onsets": 0, "eighths": 0,
                                 "voices": set()})
    values = defaultdict(int)
    tuplets = chromatic = 0
    articulation = False
    group = {}                           # (staff, voice) -> (bar, pitches sounding together now)
    last = {}                            # (staff, voice) -> the previous note or chord's outer pitch

    def close(sv):
        bar, pitches = group.pop(sv, (None, None))
        if not pitches:
            return
        staff = sv[0]
        s = stats[staff]
        s["chord"] = max(s["chord"], len(pitches))
        outer = max(pitches) if staff == 1 else min(pitches)
        if sv in last:
            leap = abs(outer - last[sv])
            s["leap"] = max(s["leap"], leap)
            if leap > 7:
                bar["leaps"] += 1
        last[sv] = outer

    for m in part.findall("measure"):
        bar = {"n": m.get("number") or str(len(bars) + 1), "onsets": defaultdict(int), "accidentals": 0, "leaps": 0}
        bars.append(bar)
        for el in m:
            if el.tag == "attributes":
                d = el.findtext("divisions")
                if d and d.strip().isdigit():
                    divisions = int(d)
                k = el.find("key")
                if k is not None and (k.findtext("fifths") or "").strip().lstrip("-").isdigit()                         and abs(int(k.findtext("fifths"))) <= 7:
                    fifths = int(k.findtext("fifths"))
                    mode = (k.findtext("mode") or "major").strip().lower()
                    minor = mode == "minor"
                    if mode not in ("major", "minor", "none", ""):
                        modes.add(mode)
                    code = key_code(fifths, minor)
                    if not keys or keys[-1]["code"] != code:
                        keys.append({"bar": bar["n"], "code": code})
                    sig = signature(fifths)
                    raised = set()
                    if minor:
                        tonic = LETTERS.index(code[0])
                        for degree in (5, 6):
                            letter = LETTERS[(tonic + degree) % 7]
                            raised.add((letter, sig[letter] + 1))
                t = el.find("time")
                if t is not None:
                    b, bt = (t.findtext("beats") or "").strip(), (t.findtext("beat-type") or "").strip()
                    label = f"{b}/{bt}" if b and bt else None
                    beats = int(b) if b.isdigit() else None
                    beat_type = int(bt) if bt.isdigit() else None
                    if label and (not times or times[-1]["time"] != label):
                        times.append({"bar": bar["n"], "time": label})
            elif el.tag in ("direction", "sound") and tempo is None:
                sound = el if el.tag == "sound" else el.find("sound")
                metronome = el.find(".//metronome") if el.tag == "direction" else None
                if metronome is not None and metronome.findtext("per-minute"):
                    unit = metronome.findtext("beat-unit") or "quarter"
                    dot = "." if metronome.find("beat-unit-dot") is not None else ""
                    tempo = f"{unit}{dot} = {metronome.findtext('per-minute').strip()}"
                elif sound is not None and sound.get("tempo"):
                    tempo = f"quarter = {round(float(sound.get('tempo')))}"
            elif el.tag == "note":
                if el.find("grace") is not None or el.find("cue") is not None:
                    continue
                staff = int(el.findtext("staff") or 1) if n_staves > 1 else 1
                voice = (el.findtext("voice") or "1").strip()
                sv = (staff, voice)
                is_chord = el.find("chord") is not None
                if not is_chord:
                    close(sv)
                    value = quarters(el, divisions)
                    if el.find("time-modification") is not None:
                        tuplets += 1
                    elif value is not None and not (el.find("rest") is not None and el.findtext("type") is None):
                        values[value] += 1
                notations = el.find("notations")
                if notations is not None and (notations.find("slur") is not None
                                              or notations.find("articulations/staccato") is not None):
                    articulation = True
                pitch = el.find("pitch")
                if pitch is None:
                    continue
                step = (pitch.findtext("step") or "C").strip()
                alter = round(float(pitch.findtext("alter") or 0))
                octave = int(pitch.findtext("octave") or 4)
                midi = 12 * (octave + 1) + NATURAL.get(step, 0) + alter
                s = stats[staff]
                s["voices"].add(voice)
                if s["low"] is None or midi < s["low"][0]:
                    s["low"] = (midi, pitch_name(step, alter, octave))
                if s["high"] is None or midi > s["high"][0]:
                    s["high"] = (midi, pitch_name(step, alter, octave))
                if not is_chord:
                    s["onsets"] += 1
                    bar["onsets"][staff] += 1
                    if (quarters(el, divisions) or 1) <= 0.5:
                        s["eighths"] += 1
                if alter != sig.get(step, 0) and (step, alter) not in raised:
                    chromatic += 1
                    bar["accidentals"] += 1
                group.setdefault(sv, (bar, []))[1].append(midi)
    for sv in list(group):
        close(sv)

    result = report(title, composer, part_name, others, n_staves, keys, times, tempo, bars, stats,
                    values, tuplets, chromatic, articulation, beats, beat_type)
    if modes:
        result["mode"] = ", ".join(sorted(modes))
        result["sight_reading"]["notes"].append(
            f"The score is marked {result['mode']}; the key shown is the major key of its key signature.")
    if not times:
        result["sight_reading"]["notes"].append("The score has no time signature; choose the set's time yourself.")
    return result


def report(title, composer, part_name, others, n_staves, keys, times, tempo, bars, stats, values, tuplets,
           chromatic, articulation, beats, beat_type) -> dict:
    first_key = keys[0]["code"] if keys else "C"
    first_time = times[0]["time"] if times else None
    first_beats, first_type = beats, beat_type
    if times:
        parts = times[0]["time"].split("/")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            first_beats, first_type = int(parts[0]), int(parts[1])

    played = [b for b in bars if sum(b["onsets"].values())]
    together = n_staves > 1 and played and \
        sum(1 for b in played if b["onsets"][1] and b["onsets"][2]) / len(played) >= 0.5
    melody, bass = stats[1], stats[2] if n_staves > 1 else None

    reasons = []                         # (level, what)

    def because(level, what):
        reasons.append((level, what))

    because(KEY_LEVEL.get(first_key, BEYOND), key_label(first_key))
    for k in keys[1:]:
        because(max(KEY_LEVEL.get(k["code"], BEYOND), 5), f"a change of key to {key_label(k['code'])}")
    if first_type == 4 and first_beats in METER_LEVEL:
        because(METER_LEVEL[first_beats], f"{first_beats}/4")
    elif first_time == "2/2":
        because(4, "2/2")
    elif first_time:
        because(5, f"{first_time} time")
    if len(times) > 1:
        because(5, "changes of time signature")
    if together:
        because(3, "hands together")
    if bass and bass["onsets"]:
        if bass["chord"] >= 4:
            because(BEYOND, f"left-hand chords of {bass['chord']} notes")
        elif bass["chord"] == 3:
            because(5, "three-note chords in the left hand")
        elif bass["chord"] == 2:
            because(4, "two-note chords in the left hand")
        per_bar = bass["onsets"] / max(1, len(played))
        if bass["eighths"] / bass["onsets"] > 0.6 and first_beats and per_bar >= 1.5 * first_beats:
            because(6, "a flowing eighth-note left hand")
        elif first_beats and per_bar >= first_beats:
            because(5, "a moving left hand (a note or more a beat)")
    if melody["chord"] == 2:
        because(6, "double notes in the right hand")
    elif melody["chord"] >= 3:
        because(BEYOND, f"right-hand chords of {melody['chord']} notes")
    for staff, s in stats.items():
        if len(s["voices"]) > 1:
            because(BEYOND, f"two voices in one hand ({'right' if staff == 1 else 'left'} hand)")
            break
    for value, count in values.items():
        name, level = VALUES.get(value, (f"notes of {value} beats", BEYOND))
        because(level, name)
    if tuplets:
        because(BEYOND, "triplets or other tuplets")
    if chromatic:
        because(6, f"accidentals outside the key ({chromatic} notes)")
    if articulation:
        because(5, "slurs or staccato")
    if melody["low"] and melody["high"]:
        span = melody["high"][0] - melody["low"][0]
        because(1 if span <= 7 else 4 if span <= 9 else 5 if span <= 14 else BEYOND,
                f"a {'right-hand' if n_staves > 1 else 'melody'} range of {interval_name(span) if span <= 12 else f'{span} semitones'}")
        leap = melody["leap"]
        because(1 if leap <= 2 else 2 if leap <= 7 else 5 if leap <= 9 else 6 if leap <= 12 else BEYOND,
                f"leaps of up to {interval_name(leap)}")

    level = max((lv for lv, _ in reasons), default=1)
    why = [what for lv, what in sorted(reasons, key=lambda r: -r[0]) if lv == level]

    sr_level = max(1, min(6, level - 1))
    options = [f"--level {sr_level}"]
    notes = []
    if first_key in KEY_LEVEL:
        options.append(f"--keys {first_key}")
    else:
        same_mode = [k for k in KEY_LEVEL if k.endswith("m") == first_key.endswith("m")]
        fifths = next(f for f, c in (MINOR if first_key.endswith("m") else MAJOR).items() if c == first_key)
        table = MINOR if first_key.endswith("m") else MAJOR
        near = sorted(same_mode, key=lambda k: abs(next(f for f, c in table.items() if c == k) - fifths))[:2]
        notes.append(f"The exercise writer has no {key_label(first_key)}. Nearest keys it has: "
                     + " and ".join(key_label(k) for k in near) + ".")
    if first_type == 4 and first_beats in METER_LEVEL:
        options.append(f"--time {first_beats}/4")
    elif first_time:
        notes.append(f"The exercise writer has 2/4, 3/4 and 4/4 only, not {first_time}.")
    if together and sr_level >= 3:
        options.append("--hands both")
    elif together:
        notes.append(f"Level {sr_level} is one hand at a time; hands together starts at Level 3.")

    def hand(s):
        if not s or s["low"] is None:
            return None
        return {"range": [s["low"][1], s["high"][1]],
                "largest_leap": interval_name(s["leap"]),
                "chords": "single notes" if s["chord"] == 1 else f"up to {s['chord']} notes at once",
                "notes": s["onsets"]}

    # Bars clearly busier than the piece's usual bar: more notes, accidentals and big leaps.
    def load_of(b):
        return sum(b["onsets"].values()) + 2 * b["accidentals"] + 2 * b["leaps"]
    loads = sorted(load_of(b) for b in played)
    usual = loads[len(loads) // 2] if loads else 0
    busiest = sorted((b for b in played if load_of(b) > 1.25 * usual), key=lambda b: -load_of(b))[:3]
    return {
        "title": title or None,
        "composer": composer or None,
        "part": part_name or None,
        "other_parts": others,
        "key": key_label(first_key),
        "key_changes": [{"bar": k["bar"], "key": key_label(k["code"])} for k in keys[1:]],
        "time": first_time,
        "time_changes": times[1:],
        "tempo": tempo,
        "bars": len(bars),
        "hands": "hands together" if together else ("two staves, mostly one hand at a time" if n_staves > 1 else "one staff"),
        "right_hand" if n_staves > 1 else "melody": hand(melody),
        "left_hand": hand(bass) if n_staves > 1 else None,
        "rhythms": [VALUES.get(v, (f"notes of {v} beats",))[0] for v in sorted(values, reverse=True)]
                   + (["triplets or other tuplets"] if tuplets else []),
        "accidentals_outside_the_key": chromatic,
        "slurs_or_staccato": articulation,
        "busiest_bars": [{"bar": b["n"], "notes": sum(b["onsets"].values()), "accidentals": b["accidentals"],
                          "leaps_over_a_fifth": b["leaps"]} for b in busiest],
        "level": {"estimate": "beyond Level 6" if level >= BEYOND else f"about Level {level}",
                  "because": why},
        "sight_reading": {"level": sr_level, "options": " ".join(options), "notes": notes},
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")    # keys like B♭ print on Windows consoles too
    args = (argv if argv is not None else sys.argv[1:])
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args and args[0] in ("-h", "--help") else 2)
    print(json.dumps(analyse(load(args[0])), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
