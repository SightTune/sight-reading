"""The exercise writer keeps its rules at every level, and its MusicXML is well formed.

    python -m unittest discover -s tests
"""
import importlib.util
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


SAMPLE_SVG = """<svg viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
 <defs><g id="E0A4-x"><path transform="scale(1,-1)" d="M0 -39c0 -38 34 -57 73 -57c45 0 99 33 99 81s-38 57 -73 57c-50 0 -99 -33 -99 -81z"/></g></defs>
 <svg class="definition-scale" viewBox="0 0 4000 2000">
  <g class="page-margin" transform="translate(100, 100)">
   <path d="M0 400 L3000 400" stroke-width="13"/>
   <use xlink:href="#E0A4-x" transform="translate(500, 400) scale(0.72, 0.72)"/>
   <polygon points="600,300 900,300 900,340 600,340"/>
   <ellipse cx="1000" cy="400" rx="20" ry="20"/>
   <path d="M1200 300 C1300 200 1500 200 1600 300 S1800 400 1900 300 Q2000 250 2100 300 T2300 300 H2400 V350 h10 v10 l10 10 Z" stroke-width="5"/>
   <g class="tempo"><text x="10" y="80" font-size="0px"><tspan font-family="Leipzig" font-size="300px"></tspan><tspan font-size="200px">\xa0=\xa0(84)</tspan></text></g>
   <g class="mNum"><text y="200" text-anchor="middle" font-size="0px"><tspan font-size="150px">5</tspan></text></g>
  </g>
 </svg>
</svg>"""


def _pdf_objects(data: bytes):
    """Check a PDF's cross-reference table and return its object count."""
    import re
    xref = int(re.search(rb"startxref\n(\d+)\n%%EOF\n$", data).group(1))
    rows = data[xref:].split(b"\n")
    count = int(rows[1].split()[1])
    for i, row in enumerate(rows[3:3 + count - 1], 1):
        offset = int(row.split()[0])
        assert data[offset:offset + len(f"{i} 0 obj")] == f"{i} 0 obj".encode(), f"object {i} not at {offset}"
    return count


class PDF(unittest.TestCase):
    def exercise(self, svg, n=1):
        return {"n": n, "svg": svg, "key": "B♭ major", "time": "3/4", "hands": "hands together", "bars": 8,
                "tempo": 84, "melody_range": ["F♯4", "C5"]}

    def test_every_shape_draws_and_the_file_holds_together(self):
        from pdf import make_pdf, path_ops
        data = make_pdf("Test (set)", "Sam", "L5-1", 5, "summary", [self.exercise(SAMPLE_SVG, i) for i in range(1, 9)])
        self.assertTrue(data.startswith(b"%PDF-1.4\n"))
        self.assertTrue(data.endswith(b"%%EOF\n"))
        self.assertGreater(_pdf_objects(data), 8)
        self.assertIn(b"/URI (https://apps.apple.com/app/id6756153566)", data)
        self.assertEqual(data, make_pdf("Test (set)", "Sam", "L5-1", 5, "summary",
                                        [self.exercise(SAMPLE_SVG, i) for i in range(1, 9)]))
        ops = path_ops("M0 0 l10 0 h5 v5 c1 1 2 2 3 3 s4 4 5 5 q1 1 2 2 t3 3 z")
        self.assertEqual(ops[0], "0 0 m")
        self.assertEqual(ops[-1], "h")
        self.assertEqual(ops[1:4], ["10 0 l", "15 0 l", "15 5 l"])

    def test_paper_sizes(self):
        from pdf import make_pdf
        self.assertIn(b"/MediaBox [0 0 595.28 841.89]", make_pdf("t", None, "c", 1, "s", [self.exercise(SAMPLE_SVG)], "a4"))
        self.assertIn(b"/MediaBox [0 0 612 792]", make_pdf("t", None, "c", 1, "s", [self.exercise(SAMPLE_SVG)]))

    @unittest.skipUnless(importlib.util.find_spec("verovio"), "needs verovio")
    def test_a_real_engraved_set(self):
        import make_set
        from pdf import make_pdf
        exercises = []
        for i, level in enumerate(LEVELS, 1):
            ex = compose(level, i)
            exercises.append({"n": i, **ex.describe(), "svg": make_set.engrave(to_musicxml(ex))})
        data = make_pdf("Piano sight-reading", None, "L1-1", 1, "summary", exercises)
        self.assertGreater(_pdf_objects(data), 8)


if __name__ == "__main__":
    unittest.main()
