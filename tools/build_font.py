"""Génère la police originale « Neon Drive Display » (assets/fonts/NeonDrive-Display.ttf).

Chaque glyphe est un squelette de polylignes aux coins coupés, épaissi en contours.
Usage : python tools/build_font.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fontTools.fontBuilder import FontBuilder          # noqa: E402
from fontTools.pens.ttGlyphPen import TTGlyphPen       # noqa: E402

from config.paths import FONTS                          # noqa: E402

UPM, CAP, STROKE, SIDE = 1000, 700, 118, 62

O = [(.22, 1), (.78, 1), (1, .80), (1, .20), (.78, 0), (.22, 0), (0, .20), (0, .80)]
G: dict[str, tuple[float, list]] = {
    "A": (560, [[(0, 0), (0, .72), (.26, 1), (.74, 1), (1, .72), (1, 0)], [(0, .36), (1, .36)]]),
    "B": (540, [[(0, 0), (0, 1), (.78, 1), (1, .85), (1, .67), (.82, .53), (0, .53)],
                [(.82, .53), (1, .39), (1, .15), (.78, 0), (0, 0)]]),
    "C": (520, [[(1, 1), (.22, 1), (0, .80), (0, .20), (.22, 0), (1, 0)]]),
    "D": (550, [[(0, 0), (0, 1), (.74, 1), (1, .77), (1, .23), (.74, 0), (0, 0)]]),
    "E": (490, [[(1, 1), (.20, 1), (0, .82), (0, .18), (.20, 0), (1, 0)], [(0, .5), (.86, .5)]]),
    "F": (480, [[(1, 1), (.20, 1), (0, .82), (0, 0)], [(0, .48), (.84, .48)]]),
    "G": (550, [[(1, 1), (.22, 1), (0, .80), (0, .20), (.22, 0), (1, 0), (1, .48), (.52, .48)]]),
    "H": (550, [[(0, 0), (0, 1)], [(1, 0), (1, 1)], [(0, .5), (1, .5)]]),
    "I": (0, [[(0, 0), (0, 1)]]),
    "J": (480, [[(1, 1), (1, .20), (.78, 0), (.22, 0), (0, .20), (0, .32)]]),
    "K": (540, [[(0, 0), (0, 1)], [(1, 1), (.42, .5), (1, 0)], [(0, .5), (.42, .5)]]),
    "L": (470, [[(0, 1), (0, .18), (.20, 0), (1, 0)]]),
    "M": (680, [[(0, 0), (0, 1), (.5, .46), (1, 1), (1, 0)]]),
    "N": (560, [[(0, 0), (0, 1), (1, 0), (1, 1)]]),
    "O": (560, [O + [O[0]]]),
    "P": (530, [[(0, 0), (0, 1), (.78, 1), (1, .82), (1, .58), (.78, .40), (0, .40)]]),
    "Q": (560, [O + [O[0]], [(.60, .30), (1.04, -.10)]]),
    "R": (540, [[(0, 0), (0, 1), (.78, 1), (1, .82), (1, .60), (.78, .42), (0, .42)], [(.50, .42), (1, 0)]]),
    "S": (520, [[(1, 1), (.20, 1), (0, .84), (0, .68), (.20, .52), (.80, .48), (1, .32), (1, .16), (.80, 0), (0, 0)]]),
    "T": (520, [[(0, 1), (1, 1)], [(.5, 1), (.5, 0)]]),
    "U": (550, [[(0, 1), (0, .20), (.22, 0), (.78, 0), (1, .20), (1, 1)]]),
    "V": (580, [[(0, 1), (.5, 0), (1, 1)]]),
    "W": (780, [[(0, 1), (.22, 0), (.5, .60), (.78, 0), (1, 1)]]),
    "X": (560, [[(0, 1), (1, 0)], [(0, 0), (1, 1)]]),
    "Y": (560, [[(0, 1), (.5, .48), (1, 1)], [(.5, .48), (.5, 0)]]),
    "Z": (530, [[(0, 1), (1, 1), (0, 0), (1, 0)]]),
    "0": (540, [O + [O[0]], [(.5, .42), (.5, .58)]]),
    "1": (230, [[(0, .80), (1, 1), (1, 0)]]),
    "2": (520, [[(0, 1), (.78, 1), (1, .84), (1, .62), (.80, .48), (.20, .44), (0, .30), (0, 0), (1, 0)]]),
    "3": (520, [[(0, 1), (.78, 1), (1, .85), (1, .66), (.80, .52), (.22, .52)], [(.80, .52), (1, .38), (1, .15), (.78, 0), (0, 0)]]),
    "4": (540, [[(.22, 1), (0, .30), (1, .30)], [(.80, .62), (.80, 0)]]),
    "5": (520, [[(1, 1), (0, 1), (0, .56), (.78, .56), (1, .40), (1, .16), (.78, 0), (0, 0)]]),
    "6": (530, [[(.92, 1), (.22, 1), (0, .80), (0, .18), (.22, 0), (.78, 0), (1, .18), (1, .38), (.78, .54), (0, .54)]]),
    "7": (510, [[(0, 1), (1, 1), (.34, 0)]]),
    "8": (530, [[(.20, .53), (0, .68), (0, .85), (.20, 1), (.80, 1), (1, .85), (1, .68), (.80, .53), (.20, .53),
                 (0, .38), (0, .16), (.20, 0), (.80, 0), (1, .16), (1, .38), (.80, .53)]]),
    "9": (530, [[(.08, 0), (.78, 0), (1, .20), (1, .82), (.78, 1), (.22, 1), (0, .82), (0, .62), (.22, .46), (1, .46)]]),
    "-": (300, [[(0, .45), (1, .45)]]), "_": (480, [[(0, -.12), (1, -.12)]]), "+": (420, [[(0, .46), (1, .46)], [(.5, .16), (.5, .76)]]),
    "=": (400, [[(0, .32), (1, .32)], [(0, .62), (1, .62)]]), "/": (380, [[(0, -.06), (1, 1.06)]]), "\\": (380, [[(0, 1.06), (1, -.06)]]),
    ".": (0, [[(0, 0), (0, .03)]]), ",": (60, [[(1, .06), (0, -.16)]]), ":": (0, [[(0, .16), (0, .20)], [(0, .68), (0, .72)]]),
    ";": (60, [[(1, .68), (1, .72)], [(1, .10), (0, -.12)]]), "!": (0, [[(0, 1), (0, .32)], [(0, 0), (0, .03)]]),
    "?": (460, [[(0, 1), (.78, 1), (1, .84), (1, .62), (.50, .44), (.50, .30)], [(.5, 0), (.5, .03)]]),
    "'": (0, [[(0, 1), (0, .78)]]), '"': (180, [[(0, 1), (0, .78)], [(1, 1), (1, .78)]]),
    "(": (160, [[(1, 1.06), (0, .80), (0, .20), (1, -.06)]]), ")": (160, [[(0, 1.06), (1, .80), (1, .20), (0, -.06)]]),
    "[": (160, [[(1, 1.06), (0, 1.06), (0, -.06), (1, -.06)]]), "]": (160, [[(0, 1.06), (1, 1.06), (1, -.06), (0, -.06)]]),
    "<": (380, [[(1, .86), (0, .46), (1, .06)]]), ">": (380, [[(0, .86), (1, .46), (0, .06)]]),
    "%": (620, [[(.06, 0), (.94, 1)], [(.02, .80), (.14, .80)], [(.86, .20), (.98, .20)]]),
    "#": (560, [[(.28, 0), (.36, 1)], [(.64, 0), (.72, 1)], [(0, .34), (1, .34)], [(0, .68), (1, .68)]]),
    "&": (560, [[(1, 0), (.20, .78), (.32, 1), (.60, 1), (.66, .80), (.06, .34), (.06, .12), (.24, 0), (.60, 0), (1, .44)]]),
    "*": (360, [[(0, .66), (1, .66)], [(.2, .90), (.8, .42)], [(.8, .90), (.2, .42)]]),
    "×": (380, [[(0, .74), (1, .18)], [(0, .18), (1, .74)]]), "·": (0, [[(0, .44), (0, .48)]]),
    "’": (0, [[(0, 1), (0, .78)]]), "…": (520, [[(0, 0), (0, .03)], [(.5, 0), (.5, .03)], [(1, 0), (1, .03)]]),
    "–": (420, [[(0, .45), (1, .45)]]), "—": (640, [[(0, .45), (1, .45)]]), "°": (190, [[(0, .72), (0, 1), (1, 1), (1, .72), (0, .72)]]),
    "→": (560, [[(0, .45), (1, .45)], [(.62, .78), (1, .45), (.62, .12)]]), "←": (560, [[(1, .45), (0, .45)], [(.38, .78), (0, .45), (.38, .12)]]),
    "↑": (420, [[(.5, 0), (.5, .95)], [(0, .62), (.5, .95), (1, .62)]]), "↓": (420, [[(.5, 0), (.5, .95)], [(0, .33), (.5, 0), (1, .33)]]),
    "«": (420, [[(.45, .80), (0, .46), (.45, .12)], [(1, .80), (.55, .46), (1, .12)]]),
    "»": (420, [[(0, .80), (.45, .46), (0, .12)], [(.55, .80), (1, .46), (.55, .12)]]),
}
MARK = {"acute": [[(-.10, 1.16), (.14, 1.33)]], "grave": [[(-.14, 1.33), (.10, 1.16)]],
        "circ": [[(-.20, 1.16), (0, 1.32), (.20, 1.16)]], "diaer": [[(-.20, 1.22), (-.20, 1.26)], [(.20, 1.22), (.20, 1.26)]],
        "cedil": [[(.02, -.02), (.08, -.14), (-.08, -.22)]]}
ACCENTS = {"É": ("E", "acute"), "È": ("E", "grave"), "Ê": ("E", "circ"), "Ë": ("E", "diaer"), "À": ("A", "grave"), "Â": ("A", "circ"),
           "Î": ("I", "circ"), "Ï": ("I", "diaer"), "Ô": ("O", "circ"), "Ö": ("O", "diaer"), "Ù": ("U", "grave"), "Û": ("U", "circ"),
           "Ü": ("U", "diaer"), "Ç": ("C", "cedil")}


def stroke(line, w, closed=False):
    """Contours d'une polyligne épaissie (onglets limités), sens horaire."""
    n = len(line)
    pts = line[:-1] if closed else line
    m = len(pts)
    left, right = [], []
    for i in range(m):
        p = pts[i]
        prev = pts[i - 1] if (closed or i > 0) else None
        nxt = pts[(i + 1) % m] if (closed or i < m - 1) else None

        def norm(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1
            return dx / ln, dy / ln
        d0 = norm(prev, p) if prev else norm(p, nxt)
        d1 = norm(p, nxt) if nxt else d0
        n0, n1 = (-d0[1], d0[0]), (-d1[1], d1[0])
        mx, my = n0[0] + n1[0], n0[1] + n1[1]
        ln2 = mx * mx + my * my
        k = 2 / ln2 if ln2 > 1e-6 else 1
        k = min(k, 2.2)
        off = (mx * k * w / 2, my * k * w / 2) if ln2 > 1e-6 else (n0[0] * w / 2, n0[1] * w / 2)
        left.append((p[0] + off[0], p[1] + off[1]))
        right.append((p[0] - off[0], p[1] - off[1]))
    poly = left + right[::-1]
    return [poly if _area(poly) < 0 else poly[::-1]]


def split_sharp(pts, half):
    """Coupe la polyligne aux angles aigus ; les bouts se recouvrent."""
    out, cur = [], [pts[0]]
    for i in range(1, len(pts) - 1):
        a, p, b = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (p[0] - a[0], p[1] - a[1]), (b[0] - p[0], b[1] - p[1])
        l0, l1 = math.hypot(*d0) or 1, math.hypot(*d1) or 1
        if (d0[0] * d1[0] + d0[1] * d1[1]) / (l0 * l1) < -.05:
            cur.append((p[0] + d0[0] / l0 * half, p[1] + d0[1] / l0 * half))
            out.append(cur)
            cur = [(p[0] - d1[0] / l1 * half, p[1] - d1[1] / l1 * half)]
        else:
            cur.append(p)
    cur.append(pts[-1])
    out.append(cur)
    return out


def clip_y(poly, lim, sign):
    """Garde la partie du polygone où sign * (y - lim) >= 0."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        dp, dq = sign * (p[1] - lim), sign * (q[1] - lim)
        if dp >= 0:
            out.append(p)
        if dp * dq < 0:
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out or poly


def _area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2


def build(path: Path, weight: int, name: str) -> None:
    glyphs, widths, cmap = {}, {}, {}

    def make(gname, w, lines):
        pen = TTGlyphPen(None)
        half = weight / 2
        for line in lines:
            pts = [(SIDE + half + x * w, half + y * (CAP - weight)) for x, y in line]
            closed = len(line) > 2 and line[0] == line[-1]
            # bouts droits prolongés d'une demi-graisse
            if not closed and len(pts) >= 2:
                for i, j in ((0, 1), (-1, -2)):
                    dx, dy = pts[i][0] - pts[j][0], pts[i][1] - pts[j][1]
                    ln = math.hypot(dx, dy) or 1
                    pts[i] = (pts[i][0] + dx / ln * half, pts[i][1] + dy / ln * half)
            # Une boucle fermée est tracée en segments : le remplissage non nul unit les contours
            if closed:
                ext = pts + [pts[1]]
                segs = [[ext[k], ext[k + 1], ext[k + 2]] for k in range(0, len(pts) - 1)]
            else:
                segs = [s for s in split_sharp(pts, half)]
            inside = all(0 <= y <= 1 for _, y in line)
            for seg in segs:
                for poly in stroke(seg, weight, False):
                    if inside:
                        poly = clip_y(clip_y(poly, 0, 1), CAP, -1)
                    q = [(round(a), round(b)) for a, b in poly]
                    pen.moveTo(q[0])
                    for v in q[1:]:
                        pen.lineTo(v)
                    pen.closePath()
        glyphs[gname] = pen.glyph()
        widths[gname] = (round(w + weight + 2 * SIDE), 0)

    order = [".notdef", "space"]
    make(".notdef", 400, [[(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]])
    glyphs["space"] = TTGlyphPen(None).glyph()
    widths["space"] = (330, 0)
    cmap[32] = cmap[0xA0] = cmap[0x202F] = "space"
    for ch, (w, lines) in G.items():
        gname = f"g{ord(ch):04X}"
        make(gname, w, lines)
        order.append(gname)
        cmap[ord(ch)] = gname
        if ch.isalpha():
            cmap[ord(ch.lower())] = gname
    for ch, (base, mark) in ACCENTS.items():
        w, lines = G[base]
        cx = .5 if w else 0
        span = 520
        extra = [[(cx + (x * span / w if w else 0), y) for x, y in line] for line in MARK[mark]]
        if not w:                                    # I : largeur nulle, on décale en absolu
            w2 = 240
            lines = [[(.5, y) for _, y in line] for line in lines]
            extra = [[(.5 + x * span / w2, y) for x, y in line] for line in MARK[mark]]
            w = w2
        gname = f"g{ord(ch):04X}"
        make(gname, w, lines + extra)
        order.append(gname)
        cmap[ord(ch)] = cmap[ord(ch.lower())] = gname
    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({g: (widths[g][0], 0) for g in order})
    metrics = {}
    for g in order:
        gl = fb.font["glyf"][g]
        metrics[g] = (widths[g][0], getattr(gl, "xMin", 0) or 0)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=950, descent=-250)
    fb.setupNameTable({"familyName": "Neon Drive", "styleName": name,
                       "copyright": "Police originale du projet NEON DRIVE, licence OFL 1.1."})
    fb.setupOS2(sTypoAscender=950, sTypoDescender=-250, usWinAscent=980, usWinDescent=260, sCapHeight=CAP)
    fb.setupPost()
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(path))
    print("OK", path.name, len(order), "glyphes")


if __name__ == "__main__":
    build(FONTS / "NeonDrive-Display.ttf", STROKE, "Display")
    build(FONTS / "NeonDrive-Light.ttf", 66, "Light")
