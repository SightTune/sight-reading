"""Write a set of exercises as a printable PDF, using only Python's standard library.

The engraver's SVG uses a small set of shapes: paths, glyphs placed with <use>, polygons
(beams), ellipses (dots) and a little text (tempo, fingering, bar numbers). This module
draws those as PDF vector graphics and sets the text in the PDF's built-in Times fonts,
so the PDF needs nothing installed and looks the same on every printer.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
import zlib

SVG = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
PAPER = {"letter": (612.0, 792.0), "a4": (595.28, 841.89)}
MARGIN = 54.0
FONT = {"regular": "F1", "bold": "F2", "italic": "F3"}
BASE_FONT = {"F1": "Times-Roman", "F2": "Times-Bold", "F3": "Times-Italic"}

# Times-Roman advance widths (per 1000 units of font size) for printable ASCII; the bold and
# italic faces are close enough for line breaking and centring short numbers.
_W = [250, 333, 408, 500, 500, 833, 778, 333, 333, 333, 500, 564, 250, 333, 250, 278,
      500, 500, 500, 500, 500, 500, 500, 500, 500, 500, 278, 278, 564, 564, 564, 444,
      921, 722, 667, 667, 722, 611, 556, 722, 722, 333, 389, 722, 611, 889, 722, 722,
      556, 722, 667, 556, 611, 722, 722, 944, 722, 722, 611, 333, 278, 333, 469, 500,
      333, 444, 500, 444, 500, 444, 333, 500, 500, 278, 278, 500, 278, 778, 500, 500,
      500, 500, 333, 389, 278, 500, 500, 722, 500, 500, 444, 480, 200, 480, 541]
WIDTH = {chr(32 + i): w for i, w in enumerate(_W)}
WIDTH.update({"\xa0": 250, "\xb7": 250, "’": 333, "—": 1000, "–": 500})

# Characters the built-in fonts don't have, written the way musicians type them
PLAIN = str.maketrans({"♯": "#", "♭": "b", "\U0001d12a": "x", "\U0001d12b": "bb", "♮": ""})


def text_width(s: str, size: float) -> float:
    return sum(WIDTH.get(ch, 500) for ch in s.translate(PLAIN)) * size / 1000


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def pdf_text(s: str) -> str:
    """A PDF literal string in the fonts' WinAnsi encoding."""
    b = s.translate(PLAIN).encode("cp1252", "replace").decode("latin-1")
    return "(" + b.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


# ---------------------------------------------------------------- SVG to PDF drawing

_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate)\s*\(([^)]*)\)")
_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtZzAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _cm(transform: str) -> list[str]:
    """One `cm` per SVG transform, in order: PDF concatenates them the way SVG nests them."""
    out = []
    for name, args in _TRANSFORM.findall(transform or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "translate":
            m = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            m = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            m = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                out.append(f"1 0 0 1 {num(v[1])} {num(v[2])} cm")
                out.append(" ".join(num(x) for x in m) + " cm")
                out.append(f"1 0 0 1 {num(-v[1])} {num(-v[2])} cm")
                continue
        else:
            m = tuple(v[:6])
        out.append(" ".join(num(x) for x in m) + " cm")
    return out


def path_ops(d: str) -> list[str]:
    """SVG path data as PDF path operators (absolute coordinates)."""
    toks = _TOKEN.findall(d)
    out: list[str] = []
    i, cmd = 0, None
    x = y = sx = sy = 0.0
    c2 = q1 = None  # the last cubic second control point (for S) and quadratic control point (for T)

    def take(n):
        nonlocal i
        if i + n > len(toks) or any(t.isalpha() for t in toks[i:i + n]):
            raise ValueError("path data ends early")
        vals = [float(t) for t in toks[i:i + n]]
        i += n
        return vals

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                out.append("h")
                x, y, c2, q1 = sx, sy, None, None
                continue
        elif cmd is None:
            raise ValueError("path data starts without a command")
        rel = cmd.islower()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        c = cmd.upper()
        if c == "M":
            a, b = take(2)
            x, y = ox + a, oy + b
            sx, sy = x, y
            out.append(f"{num(x)} {num(y)} m")
            cmd = "l" if rel else "L"
            c2 = q1 = None
        elif c == "L":
            a, b = take(2)
            x, y = ox + a, oy + b
            out.append(f"{num(x)} {num(y)} l")
            c2 = q1 = None
        elif c == "H":
            (a,) = take(1)
            x = ox + a
            out.append(f"{num(x)} {num(y)} l")
            c2 = q1 = None
        elif c == "V":
            (b,) = take(1)
            y = oy + b
            out.append(f"{num(x)} {num(y)} l")
            c2 = q1 = None
        elif c in "CS":
            if c == "C":
                x1, y1, x2, y2, x3, y3 = take(6)
                x1, y1 = ox + x1, oy + y1
            else:
                x2, y2, x3, y3 = take(4)
                x1, y1 = (2 * x - c2[0], 2 * y - c2[1]) if c2 else (x, y)
            x2, y2, x3, y3 = ox + x2, oy + y2, ox + x3, oy + y3
            out.append(" ".join(num(v) for v in (x1, y1, x2, y2, x3, y3)) + " c")
            c2, q1 = (x2, y2), None
            x, y = x3, y3
        elif c in "QT":
            if c == "Q":
                qx, qy, x3, y3 = take(4)
                qx, qy = ox + qx, oy + qy
            else:
                x3, y3 = take(2)
                qx, qy = (2 * x - q1[0], 2 * y - q1[1]) if q1 else (x, y)
            x3, y3 = ox + x3, oy + y3
            pts = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x3 + 2 / 3 * (qx - x3), y3 + 2 / 3 * (qy - y3), x3, y3)
            out.append(" ".join(num(v) for v in pts) + " c")
            q1, c2 = (qx, qy), None
            x, y = x3, y3
        elif c == "A":  # not used by the engraver; drawn as a straight line to the end point
            *_, a, b = take(7)
            x, y = ox + a, oy + b
            out.append(f"{num(x)} {num(y)} l")
            c2 = q1 = None
        else:
            raise ValueError(f"unknown path command {cmd!r}")
    return out


def _ellipse(cx, cy, rx, ry) -> list[str]:
    k = 0.5523
    return [f"{num(cx + rx)} {num(cy)} m",
            f"{num(cx + rx)} {num(cy + k * ry)} {num(cx + k * rx)} {num(cy + ry)} {num(cx)} {num(cy + ry)} c",
            f"{num(cx - k * rx)} {num(cy + ry)} {num(cx - rx)} {num(cy + k * ry)} {num(cx - rx)} {num(cy)} c",
            f"{num(cx - rx)} {num(cy - k * ry)} {num(cx - k * rx)} {num(cy - ry)} {num(cx)} {num(cy - ry)} c",
            f"{num(cx + k * rx)} {num(cy - ry)} {num(cx + rx)} {num(cy - k * ry)} {num(cx + rx)} {num(cy)} c", "h"]


def _points(s: str) -> list[float]:
    return [float(v) for v in re.split(r"[\s,]+", (s or "").strip()) if v]


def _size(v) -> float:
    try:
        return float(str(v).replace("px", ""))
    except ValueError:
        return 0.0


class Drawing:
    """Draws one engraved SVG into a list of PDF operators. SVG coordinates (y down) are kept;
    the caller sets a flipped matrix before drawing."""

    def __init__(self, root: ET.Element):
        self.ops: list[str] = []
        self.defs: dict[str, ET.Element] = {}
        for defs in root.iter(SVG + "defs"):
            for el in defs.iter():
                if el.get("id"):
                    self.defs[el.get("id")] = el

    def draw(self, el: ET.Element, font: str = "regular", viewport=None):
        tag = el.tag[len(SVG):] if el.tag.startswith(SVG) else el.tag
        classes = set((el.get("class") or "").split())
        if (tag in ("defs", "desc", "style", "title", "metadata") or "placeholder" in classes
                or el.get("visibility") == "hidden" or el.get("display") == "none"):
            return
        if classes & {"tempo", "fing", "reh", "ending"}:
            font = "bold"
        elif classes & {"dir", "dynam", "mNum"}:
            font = "italic"
        cms = _cm(el.get("transform"))
        if cms:
            self.ops.append("q")
            self.ops.extend(cms)
        if tag == "svg":
            self._svg(el, font, viewport)
        elif tag in ("g", "a", "symbol"):
            for child in el:
                self.draw(child, font, viewport)
        elif tag == "use":
            ref = self.defs.get((el.get(XLINK_HREF) or el.get("href") or "").lstrip("#"))
            if ref is not None:
                dx, dy = _size(el.get("x", 0)), _size(el.get("y", 0))
                self.ops.append("q")
                if dx or dy:
                    self.ops.append(f"1 0 0 1 {num(dx)} {num(dy)} cm")
                for child in ref:
                    self.draw(child, font, viewport)
                self.ops.append("Q")
        elif tag == "path":
            self._shape(el, path_ops(el.get("d", "")))
        elif tag in ("polygon", "polyline"):
            p = _points(el.get("points"))
            ops = [f"{num(p[0])} {num(p[1])} m"] + [f"{num(a)} {num(b)} l" for a, b in zip(p[2::2], p[3::2])]
            self._shape(el, ops + (["h"] if tag == "polygon" else []), stroke_only=tag == "polyline")
        elif tag == "rect":
            x, y, w, h = (_size(el.get(k, 0)) for k in ("x", "y", "width", "height"))
            self._shape(el, [f"{num(x)} {num(y)} {num(w)} {num(h)} re"])
        elif tag in ("ellipse", "circle"):
            r = _size(el.get("r", 0))
            rx, ry = _size(el.get("rx", r)), _size(el.get("ry", r))
            self._shape(el, _ellipse(_size(el.get("cx", 0)), _size(el.get("cy", 0)), rx, ry))
        elif tag == "line":
            x1, y1, x2, y2 = (_size(el.get(k, 0)) for k in ("x1", "y1", "x2", "y2"))
            self._shape(el, [f"{num(x1)} {num(y1)} m", f"{num(x2)} {num(y2)} l"], stroke_only=True)
        elif tag == "text":
            self._text(el, font)
        if cms:
            self.ops.append("Q")

    def _svg(self, el, font, viewport):
        """A nested <svg>: map its viewBox onto its viewport (default: the parent's), centred."""
        vb = _points(el.get("viewBox"))
        if len(vb) == 4 and viewport:
            vw = _size(el.get("width")) or viewport[0]
            vh = _size(el.get("height")) or viewport[1]
            s = min(vw / vb[2], vh / vb[3])
            ox = _size(el.get("x", 0)) + (vw - vb[2] * s) / 2
            oy = _size(el.get("y", 0)) + (vh - vb[3] * s) / 2
            self.ops += ["q", f"{num(s)} 0 0 {num(s)} {num(ox - vb[0] * s)} {num(oy - vb[1] * s)} cm"]
            for child in el:
                self.draw(child, font, (vb[2], vb[3]))
            self.ops.append("Q")
        else:
            for child in el:
                self.draw(child, font, viewport)

    def _shape(self, el, ops, stroke_only=False):
        if not ops:
            return
        sw = el.get("stroke-width")
        fill_none = el.get("fill") == "none"
        styled = sw or el.get("stroke-linecap") or el.get("stroke-linejoin")
        if styled:
            self.ops.append("q")
            if sw:
                self.ops.append(f"{num(_size(sw))} w")
            if el.get("stroke-linecap") in ("round", "square"):
                self.ops.append({"round": "1 J", "square": "2 J"}[el.get("stroke-linecap")])
            if el.get("stroke-linejoin") in ("round", "bevel"):
                self.ops.append({"round": "1 j", "bevel": "2 j"}[el.get("stroke-linejoin")])
        self.ops.extend(ops)
        if stroke_only or fill_none:
            self.ops.append("S")
        elif sw:
            self.ops.append("B")   # filled and outlined: lines, stems, slurs
        else:
            self.ops.append("f")   # glyphs, beams, dots
        if styled:
            self.ops.append("Q")

    def _text(self, el, font):
        runs = []  # (text, size, smufl)

        def walk(node, size, family):
            size = _size(node.get("font-size", size)) or size
            family = node.get("font-family", family)
            if node.text and node.text.strip():
                runs.append((node.text.strip("\n\t "), size, family == "Leipzig"))
            for child in node:
                walk(child, size, family)
                if child.tail and child.tail.strip():
                    runs.append((child.tail.strip("\n\t "), size, family == "Leipzig"))

        walk(el, 0.0, None)
        runs = [r for r in runs if r[1] > 0]
        if not runs:
            return
        width = sum(0.32 * s if smufl else text_width(t, s) for t, s, smufl in runs)
        x, y = _size(el.get("x", 0)), _size(el.get("y", 0))
        anchor = el.get("text-anchor", "start")
        x -= width / 2 if anchor == "middle" else width if anchor == "end" else 0
        for t, s, smufl in runs:
            if smufl:
                self._metronome_note(t, x, y, s)
                x += 0.32 * s
            else:
                self.ops.append(f"BT /{FONT[font]} {num(s)} Tf 1 0 0 -1 {num(x)} {num(y)} Tm {pdf_text(t)} Tj ET")
                x += text_width(t, s)

    def _metronome_note(self, t, x, y, s):
        """The note in a tempo mark (SMuFL metNoteQuarterUp or HalfUp), drawn as a notehead and stem."""
        hollow = "" in t
        a = math.radians(-20)
        cx = x + 0.15 * s
        self.ops += ["q", f"1 0 0 1 {num(cx)} {num(y)} cm",
                     f"{num(math.cos(a))} {num(math.sin(a))} {num(-math.sin(a))} {num(math.cos(a))} 0 0 cm"]
        self.ops += _ellipse(0, 0, 0.15 * s, 0.1 * s)
        if hollow:
            self.ops += [f"{num(0.025 * s)} w", "S"]
        else:
            self.ops.append("f")
        self.ops.append("Q")
        self.ops.append(f"{num(x + 0.275 * s)} {num(y - 0.86 * s)} {num(0.03 * s)} {num(0.82 * s)} re f")


def score_height(svg: str, width: float) -> float:
    root = ET.fromstring(svg)
    vb = _points(root.get("viewBox"))
    return vb[3] * width / vb[2] if len(vb) == 4 else _size(root.get("height")) * width / _size(root.get("width"))


def score_ops(svg: str, x: float, top: float, width: float) -> tuple[list[str], float]:
    """PDF operators that draw one engraved SVG `width` points wide with its top edge at
    `top` (PDF coordinates); returns them and the height used."""
    root = ET.fromstring(svg)
    vb = _points(root.get("viewBox"))
    if len(vb) != 4:
        vb = [0, 0, _size(root.get("width")), _size(root.get("height"))]
    s = width / vb[2]
    d = Drawing(root)
    d.ops = ["q", f"{num(s)} 0 0 {num(-s)} {num(x - vb[0] * s)} {num(top + vb[1] * s)} cm"]
    for child in root:
        d.draw(child, "regular", (vb[2], vb[3]))
    d.ops.append("Q")
    return d.ops, vb[3] * s


# ---------------------------------------------------------------- page layout

class Pages:
    def __init__(self, paper: str, footer: str):
        self.w, self.h = PAPER[paper]
        self.footer = footer
        self.pages: list[list[str]] = []
        self.links: list[list[tuple]] = []
        self.new()

    def new(self):
        self.pages.append([])
        self.links.append([])
        self.y = self.h - MARGIN

    @property
    def ops(self):
        return self.pages[-1]

    def room(self, need: float):
        if self.y - need < MARGIN + 18:
            self.new()

    def text(self, s, size, font="regular", x=None):
        self.ops.append(f"BT /{FONT[font]} {num(size)} Tf {num(MARGIN if x is None else x)} {num(self.y)} Td {pdf_text(s)} Tj ET")

    def line(self, s, size, font="regular", lead=1.35):
        self.room(size * lead)
        self.y -= size
        self.text(s, size, font)
        self.y -= size * (lead - 1)

    def paragraph(self, s, size, font="regular", lead=1.35, indent=0.0):
        width = self.w - 2 * MARGIN - indent
        words, cur = s.split(), ""
        lines = []
        for w in words:
            trial = f"{cur} {w}".strip()
            if text_width(trial, size) * 1.03 > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        for ln in lines:
            self.room(size * lead)
            self.y -= size
            self.text(ln, size, font, MARGIN + indent)
            self.y -= size * (lead - 1)

    def link(self, label: str, url: str, size: float, lead=1.35):
        """A line of text that opens `url` when clicked in a PDF viewer."""
        self.room(size * lead)
        self.y -= size
        self.ops.append(f"q 0.1 0.25 0.6 rg BT /F1 {num(size)} Tf {num(MARGIN)} {num(self.y)} Td {pdf_text(label)} Tj ET Q")
        self.links[-1].append((MARGIN, self.y - size * 0.25, MARGIN + text_width(label, size), self.y + size * 0.8, url))
        self.y -= size * (lead - 1)

    def rule(self, gap=4.0, width=0.5, gray=0.75):
        self.ops.append(f"q {num(gray)} G {num(width)} w {num(MARGIN)} {num(self.y - gap)} m {num(self.w - MARGIN)} {num(self.y - gap)} l S Q")
        self.y -= gap * 2

    def finish(self) -> list[tuple[bytes, list[tuple]]]:
        n = len(self.pages)
        out = []
        for i, (ops, links) in enumerate(zip(self.pages, self.links), 1):
            foot = f"{self.footer} \xb7 page {i} of {n}"
            ops = ops + [f"q 0.35 g BT /F1 8 Tf {num(MARGIN)} {num(MARGIN - 22)} Td {pdf_text(foot)} Tj ET Q"]
            out.append(("\n".join(ops).encode("latin-1"), links))
        return out


def make_pdf(title: str, student: str | None, code: str, level: int, summary: str, exercises: list[dict],
             paper: str = "letter") -> bytes:
    """The set as a PDF: the exercises first, then the teacher's page on a page of its own."""
    p = Pages(paper, f"Set {code} \xb7 made with SightTune's free sight-reading plugin, sighttune.com")
    width = p.w - 2 * MARGIN

    p.line(title, 20, "bold", 1.3)
    p.line(f"Level {level} \xb7 {len(exercises)} exercise{'s' if len(exercises) != 1 else ''} \xb7 set {code}", 10.5)
    if student:
        p.line(f"For {student}", 12, "italic")
    p.y -= 6
    p.line("Before you play each one", 10, "bold")
    for i, tip in enumerate([
            "Take 30 seconds to look: the key signature, the time signature, where each hand starts, and any rhythm to count.",
            "Count one bar out loud at a speed you can keep all the way through.",
            "Keep going. Don't stop to fix a wrong note; the next beat matters more.",
            "Then listen to it, and play it once more."], 1):
        p.paragraph(f"{i}.  {tip}", 9.5, lead=1.3, indent=4)
    p.y -= 8

    for e in exercises:
        p.room(20 + score_height(e["svg"], width))
        p.y -= 14
        p.text(str(e["n"]), 13, "bold")
        p.y -= 4
        ops, height = score_ops(e["svg"], MARGIN, p.y, width)
        p.ops.extend(ops)
        p.y -= height + 16

    p.new()
    p.line("Teacher's page", 16, "bold", 1.4)
    p.paragraph(f"Level {level}: {summary}", 10)
    p.y -= 6
    cols = [("No.", 0), ("Key", 34), ("Time", 130), ("Hands", 175), ("Bars", 265), ("Beats a minute", 305), ("Melody range", 390)]

    def header():
        p.y -= 10
        for label, dx in cols:
            p.text(label, 9.5, "bold", MARGIN + dx)
        p.rule(4, 0.6, 0.55)

    header()
    for e in exercises:
        if p.y - 18 < MARGIN + 18:
            p.new()
            header()
        p.y -= 10
        cells = [str(e["n"]), e["key"], e["time"], e["hands"], str(e["bars"]), str(e["tempo"]),
                 " to ".join(e["melody_range"])]
        for (label, dx), cell in zip(cols, cells):
            p.text(cell, 9.5, "regular", MARGIN + dx)
        p.rule(4, 0.4, 0.8)
    p.y -= 8
    p.paragraph(f"Every exercise is new, written by rule for this set. Set {code} always writes the same music, "
                "so you can make it again or share the code.", 9.5)
    p.y -= 14
    p.line("Reading on an iPad", 10.5, "bold")
    p.paragraph(IPAD_STEPS, 9.5)
    p.link(f"Get SightTune on the App Store: {APP_STORE[len('https://'):]}", APP_STORE, 9.5)
    return _write(p.finish(), p.w, p.h, title)


APP_STORE = "https://apps.apple.com/app/id6756153566"
IPAD_STEPS = ("Open this PDF on an iPad, tap Share, then SightTune: it turns the pages as your eyes reach the end "
              "of each one. From an iPhone, the same steps send the set to SightTune on your iPad.")


def _write(contents: list[tuple[bytes, list[tuple]]], w: float, h: float, title: str) -> bytes:
    n = len(contents)
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        ("<< /Type /Pages /Kids [" + " ".join(f"{7 + 2 * i} 0 R" for i in range(n)) + f"] /Count {n} >>").encode(),
    ]
    for ref in ("F1", "F2", "F3"):
        objs.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{BASE_FONT[ref]} /Encoding /WinAnsiEncoding >>".encode())
    objs.append(f"<< /Title {pdf_text(title)} /Producer (SightTune sight-reading) >>".encode("latin-1"))
    for i, (data, links) in enumerate(contents):
        annots = ""
        if links:
            annots = " /Annots [" + " ".join(
                f"<< /Type /Annot /Subtype /Link /Rect [{num(x1)} {num(y1)} {num(x2)} {num(y2)}] /Border [0 0 0] "
                f"/A << /S /URI /URI {pdf_text(url)} >> >>" for x1, y1, x2, y2, url in links) + "]"
        objs.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {num(w)} {num(h)}] "
                     f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >>{annots} /Contents {8 + 2 * i} 0 R >>").encode())
        z = zlib.compress(data, 9)
        objs.append(f"<< /Length {len(z)} /Filter /FlateDecode >>\nstream\n".encode() + z + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
