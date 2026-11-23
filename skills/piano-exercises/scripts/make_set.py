"""Make a set of piano sight-reading exercises: a page to print or play, and MusicXML files.

    python make_set.py --level 3 [--count 10] [--keys C,G,Am] [--time 4/4,3/4]
                       [--hands mixed|right|left|both] [--bars 8] [--seed 4821]
                       [--title "..."] [--student "..."] [--out DIR]

Writes into DIR (default ./sight-reading-<set code>):
    sight-reading-<set code>.html   the set: engraved music, Listen and Count-in buttons, printable
    musicxml/NN.musicxml            each exercise, for notation software
    set.json                        what was made, and the set code that makes it again

Needs the verovio package (pip install verovio) to engrave the music.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sightread import KEYS, LEVELS, compose, to_musicxml  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def plan(level: int, count: int, keys, meters, hands: str, rng: random.Random):
    """(key, beats, hand) for each exercise, spread evenly over what was asked for."""
    lv = LEVELS[level]
    keys = keys or list(lv.keys)
    meters = meters or list(lv.meters)
    keys, meters = rng.sample(keys, len(keys)), rng.sample(meters, len(meters))
    out = []
    for i in range(count):
        k = keys[i % len(keys)]                          # every key before any repeats
        m = meters[(i + i // len(keys)) % len(meters)]   # and the time signatures turn over with them
        if hands == "mixed":
            hand = "left" if i % 3 == 2 else "right"
        else:
            hand = hands
        out.append((k, m, hand))
    return out


def engrave(xml: str) -> str:
    import verovio
    tk = verovio.toolkit()
    tk.setOptions({
        "pageWidth": 2100, "pageHeight": 60000, "adjustPageHeight": True,
        "breaks": "encoded" if "new-system" in xml else "auto",
        "scale": 40, "header": "none", "footer": "none", "svgViewBox": True,
        "pageMarginTop": 40, "pageMarginBottom": 40, "pageMarginLeft": 60, "pageMarginRight": 60,
        "spacingSystem": 14, "minLastJustification": 0,
    })
    if not tk.loadData(xml):
        raise RuntimeError("the engraver could not read an exercise")
    return tk.renderToSVG(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", type=int, required=True, choices=sorted(LEVELS))
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--keys", help="comma-separated: C,G,D,A,F,Bb,Eb,Am,Em,Bm,F#m,Dm,Gm,Cm")
    ap.add_argument("--time", help="comma-separated time signatures: 4/4,3/4,2/4")
    ap.add_argument("--hands", choices=["mixed", "right", "left", "both"])
    ap.add_argument("--bars", type=int, choices=[4, 8, 12, 16])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--title")
    ap.add_argument("--student", help="a name to print on the set, if the teacher wants one")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    try:
        import verovio  # noqa: F401
    except ImportError:
        sys.exit("The engraver is missing. Install it with: python -m pip install verovio")

    lv = LEVELS[args.level]
    keys = [k.strip() for k in args.keys.split(",")] if args.keys else None
    for k in keys or []:
        if k not in KEYS:
            ap.error(f"unknown key {k!r}; use one of {', '.join(KEYS)}")
    meters = [int(t.strip().split("/")[0]) for t in args.time.split(",")] if args.time else None
    for m in meters or []:
        if m not in (2, 3, 4):
            ap.error("time signatures: 2/4, 3/4 or 4/4")
    hands = args.hands or ("both" if lv.together else "mixed")
    if hands == "both" and not lv.together:
        ap.error(f"Level {args.level} is one hand at a time; hands together starts at Level 3")
    if not 1 <= args.count <= 40:
        ap.error("--count: 1 to 40")

    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(1000, 99999)
    code = f"L{args.level}-{seed}"
    rng = random.Random(seed)
    out = args.out or os.path.join(os.getcwd(), f"sight-reading-{code}")
    os.makedirs(os.path.join(out, "musicxml"), exist_ok=True)

    exercises = []
    for i, (key, beats, hand) in enumerate(plan(args.level, args.count, keys, meters, hands, rng), 1):
        ex = compose(args.level, seed * 100 + i, key=key, beats=beats, hand=hand, bars=args.bars)
        xml = to_musicxml(ex, f"Sight-reading {code}, No. {i}")
        with open(os.path.join(out, "musicxml", f"{i:02d}.musicxml"), "w", encoding="utf-8", newline="\n") as f:
            f.write(xml)
        exercises.append({"n": i, **ex.describe(), "svg": engrave(xml), "xml": xml,
                          "events": [[round(s, 3), round(d, 3), m] for s, d, m in ex.events()],
                          "beats": ex.beats})

    title = args.title or f"Piano sight-reading, Level {args.level}"
    page = render_page(title, args.student, code, lv, exercises)
    path = os.path.join(out, f"sight-reading-{code}.html")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    with open(os.path.join(out, "set.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"code": code, "level": args.level, "title": title, "hands": hands,
                   "exercises": [{k: v for k, v in e.items() if k not in ("svg", "xml", "events")} for e in exercises]},
                  f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"page": path, "folder": out, "code": code, "count": len(exercises),
                      "exercises": [{k: e[k] for k in ("n", "key", "time", "hands", "bars", "tempo")} for e in exercises]},
                     ensure_ascii=False, indent=1))


def render_page(title, student, code, lv, exercises) -> str:
    with open(os.path.join(HERE, "page.html"), encoding="utf-8") as f:
        template = f.read()
    cards = []
    for e in exercises:
        svg = base64.b64encode(e["svg"].encode("utf-8")).decode("ascii")
        xml = base64.b64encode(e["xml"].encode("utf-8")).decode("ascii")
        cards.append(
            f'<section class="ex" data-n="{e["n"]}">'
            f'<div class="ex-head"><h2>{e["n"]}</h2>'
            f'<div class="tools">'
            f'<button type="button" class="count" data-n="{e["n"]}">Count in</button>'
            f'<button type="button" class="listen" data-n="{e["n"]}">Listen</button>'
            f'<a class="xml" download="sight-reading-{code}-{e["n"]:02d}.musicxml" '
            f'href="data:application/vnd.recordare.musicxml+xml;base64,{xml}">MusicXML</a>'
            f'</div></div>'
            f'<img class="score" alt="Exercise {e["n"]}" src="data:image/svg+xml;base64,{svg}">'
            f'</section>')
    rows = "".join(
        f'<tr><td>{e["n"]}</td><td>{html.escape(e["key"])}</td><td>{e["time"]}</td><td>{e["hands"]}</td>'
        f'<td>{e["bars"]}</td><td>{e["tempo"]}</td><td>{" to ".join(e["melody_range"])}</td></tr>'
        for e in exercises)
    music = {e["n"]: {"tempo": e["tempo"], "beats": e["beats"], "notes": e["events"]} for e in exercises}
    return (template
            .replace("{{TITLE}}", html.escape(title))
            .replace("{{STUDENT}}", f'<p class="student">For {html.escape(student)}</p>' if student else "")
            .replace("{{LEVEL}}", str(lv.n))
            .replace("{{SUMMARY}}", html.escape(lv.summary))
            .replace("{{CODE}}", code)
            .replace("{{COUNT}}", str(len(exercises)))
            .replace("{{CARDS}}", "\n".join(cards))
            .replace("{{ROWS}}", rows)
            .replace("{{MUSIC}}", json.dumps(music, separators=(",", ":"))))


if __name__ == "__main__":
    main()
