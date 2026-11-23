"""The exercise writer keeps its rules at every level, and its MusicXML is well formed.

    python -m unittest discover -s tests
"""
import os
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "piano-exercises", "scripts"))
from sightread import KEYS, LEVELS, check, compose, to_musicxml  # noqa: E402

SEEDS = range(40)


class Rules(unittest.TestCase):
    def test_every_level_keeps_its_rules(self):
        for level in LEVELS:
            for hand in (["right", "left"] if level < 3 else ["both", "right"]):
                for seed in SEEDS:
                    ex = compose(level, seed, hand=hand)
                    self.assertEqual(check(ex), [], f"level {level} seed {seed} {hand}")

    def test_every_key_and_time_at_level_6(self):
        for key in KEYS:
            for beats in (2, 3, 4):
                ex = compose(6, 7, key=key, beats=beats)
                self.assertEqual(check(ex), [], f"{key} {beats}/4")

    def test_same_seed_same_music(self):
        for level in LEVELS:
            self.assertEqual(to_musicxml(compose(level, 123)), to_musicxml(compose(level, 123)))

    def test_hands_together_only_from_level_3(self):
        with self.assertRaises(ValueError):
            compose(2, 1, hand="both")


class MusicXML(unittest.TestCase):
    def test_bars_are_full_and_the_file_parses(self):
        for level in LEVELS:
            for seed in range(10):
                ex = compose(level, seed)
                root = ET.fromstring(to_musicxml(ex).split("\n", 2)[2])
                measures = root.findall("./part/measure")
                self.assertEqual(len(measures), ex.bars)
                for m in measures:
                    by_staff = {}
                    for note in m.findall("note"):
                        if note.find("chord") is not None:
                            continue
                        staff = note.findtext("staff", "1")
                        by_staff[staff] = by_staff.get(staff, 0) + int(note.findtext("duration"))
                    for staff, total in by_staff.items():
                        self.assertEqual(total, ex.beats * 2, f"level {level} seed {seed} bar {m.get('number')} staff {staff}")

    def test_raised_seventh_gets_its_sharp(self):
        # Level 4's left hand plays G sharp and E on the dominant chord in A minor
        found = False
        for seed in range(20):
            ex = compose(4, seed, key="Am")
            if "V" not in ex.chords:
                continue
            xml = to_musicxml(ex)
            self.assertIn("<step>G</step><alter>1</alter>", xml)
            self.assertIn("<accidental>sharp</accidental>", xml)
            found = True
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
