"""The score reader reads keys, times, hands and rhythms right, and places music at the right level.

    python -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "skills", "piano-exercises", "scripts"))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "piano-lesson-plan", "scripts"))
from sightread import KEYS, LEVELS, compose, to_musicxml  # noqa: E402
import read_score  # noqa: E402
from read_score import KEY_LEVEL, METER_LEVEL, analyse, load  # noqa: E402


def read(xml: str) -> dict:
    return analyse(ET.fromstring(xml.split("\n", 2)[2] if xml.startswith("<?xml") else xml))


def level_of(result) -> int:
    estimate = result["level"]["estimate"]
    return 7 if "beyond" in estimate else int(estimate.split()[-1])


def note(step, octave, dur, kind, staff, voice=1, dot=False, alter=0, triplet=False, chord=False):
    return (f"<note>{'<chord/>' if chord else ''}<pitch><step>{step}</step>"
            f"{f'<alter>{alter}</alter>' if alter else ''}<octave>{octave}</octave></pitch>"
            f"<duration>{dur}</duration><voice>{voice}</voice><type>{kind}</type>{'<dot/>' if dot else ''}"
            f"{'<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>' if triplet else ''}"
            f"<staff>{staff}</staff></note>")


def simple_bar(n):
    return (f'<measure number="{n}">' + note("E", 5, 36, "half", 1, dot=True) + "<backup><duration>36</duration></backup>"
            + note("E", 3, 36, "half", 2, voice=5, dot=True) + "</measure>")


# An E major piece in 6/8 with sixteenths, triplets, two voices in the right hand and a change to G major.
HARD = ("<score-partwise version='4.0'><work><work-title>Study</work-title></work>"
        "<part-list><score-part id='P1'><part-name>Piano</part-name></score-part></part-list><part id='P1'>"
        "<measure number='1'><attributes><divisions>12</divisions><key><fifths>4</fifths><mode>major</mode></key>"
        "<time><beats>6</beats><beat-type>8</beat-type></time><staves>2</staves></attributes>"
        + note("E", 5, 3, "16th", 1) + note("F", 5, 3, "16th", 1, alter=1) + note("G", 5, 3, "16th", 1, alter=1)
        + note("A", 5, 3, "16th", 1) + note("B", 5, 6, "eighth", 1) + note("E", 5, 18, "quarter", 1, dot=True)
        + "<backup><duration>36</duration></backup>" + note("B", 4, 36, "half", 1, voice=2, dot=True)
        + "<backup><duration>36</duration></backup>" + note("E", 3, 36, "half", 2, voice=5, dot=True)
        + "</measure><measure number='2'><attributes><key><fifths>1</fifths><mode>major</mode></key></attributes>"
        + note("G", 5, 4, "eighth", 1, triplet=True) + note("A", 5, 4, "eighth", 1, triplet=True)
        + note("B", 5, 4, "eighth", 1, triplet=True) + note("D", 5, 18, "quarter", 1, dot=True)
        + note("C", 5, 6, "eighth", 1) + "<backup><duration>36</duration></backup>"
        + note("G", 2, 36, "half", 2, voice=5, dot=True) + "</measure>"
        + "".join(simple_bar(n) for n in range(3, 6)) + "</part></score-partwise>")


class Levels(unittest.TestCase):
    def test_the_tables_match_the_exercise_writer(self):
        for name in KEYS:
            self.assertEqual(KEY_LEVEL[name], min(lv.n for lv in LEVELS.values() if name in lv.keys), name)
        for beats in (2, 3, 4):
            self.assertEqual(METER_LEVEL[beats], min(lv.n for lv in LEVELS.values() if beats in lv.meters), beats)

    def test_the_writers_music_never_reads_above_its_level(self):
        for level in LEVELS:
            for hand in (["right", "left"] if level < 3 else ["both"]):
                for seed in range(40):
                    self.assertLessEqual(level_of(read(to_musicxml(compose(level, seed, hand=hand)))), level,
                                         f"level {level} seed {seed} {hand}")
        self.assertEqual(level_of(read(to_musicxml(compose(1, 3)))), 1)

    def test_every_key_and_time_reads_back(self):
        for name, key in KEYS.items():
            for beats in (2, 3, 4):
                r = read(to_musicxml(compose(6, 5, key=name, beats=beats)))
                self.assertEqual(r["key"], read_score.key_label(name))
                self.assertEqual(r["time"], f"{beats}/4")
                self.assertEqual(r["hands"], "hands together")

    def test_options_for_a_matching_set(self):
        r = read(to_musicxml(compose(5, 2, key="Bb", beats=3)))
        self.assertEqual(level_of(r), 5)
        self.assertEqual(r["sight_reading"]["options"], "--level 4 --keys Bb --time 3/4 --hands both")
        r = read(to_musicxml(compose(3, 2, key="Am", beats=4)))
        self.assertEqual(r["sight_reading"]["options"], "--level 2 --keys Am --time 4/4")
        self.assertIn("one hand at a time", r["sight_reading"]["notes"][0])


class RealScores(unittest.TestCase):
    def test_a_harder_piece(self):
        r = read(HARD)
        self.assertEqual(r["title"], "Study")
        self.assertEqual(r["key"], "E major")
        self.assertEqual(r["key_changes"], [{"bar": "2", "key": "G major"}])
        self.assertEqual(r["time"], "6/8")
        self.assertEqual(r["bars"], 5)
        self.assertEqual(r["level"]["estimate"], "beyond Level 6")
        for reason in ("E major", "sixteenth notes", "triplets or other tuplets", "two voices in one hand (right hand)"):
            self.assertIn(reason, r["level"]["because"])
        self.assertEqual(r["accidentals_outside_the_key"], 0)
        self.assertEqual(sorted(b["bar"] for b in r["busiest_bars"]), ["1", "2"])
        options = r["sight_reading"]
        self.assertEqual(options["options"], "--level 6 --hands both")
        self.assertIn("Nearest keys it has: A major and D major", " ".join(options["notes"]))
        self.assertIn("not 6/8", " ".join(options["notes"]))

    def test_compressed_mxl(self):
        xml = to_musicxml(compose(4, 9, key="G", beats=2))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "piece.mxl")
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("META-INF/container.xml",
                           '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
                           '<rootfile full-path="score/piece.xml"/></rootfiles></container>')
                z.writestr("score/piece.xml", xml)
            r = analyse(load(path))
        self.assertEqual((r["key"], r["time"]), ("G major", "2/4"))

    def test_prints_on_a_windows_console(self):
        import subprocess
        xml = to_musicxml(compose(5, 1, key="Bb"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "piece.musicxml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml)
            script = os.path.join(HERE, "..", "skills", "piano-lesson-plan", "scripts", "read_score.py")
            run = subprocess.run([sys.executable, script, path], capture_output=True,
                                 env={**os.environ, "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(run.returncode, 0, run.stderr.decode("utf-8", "replace"))
        self.assertIn("B♭ major", run.stdout.decode("utf-8"))

    def test_not_a_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "notes.xml")
            with open(path, "w") as f:
                f.write("<html><body>hello</body></html>")
            with self.assertRaises(SystemExit):
                load(path)


if __name__ == "__main__":
    unittest.main()
