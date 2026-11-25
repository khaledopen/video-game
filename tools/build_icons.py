"""Dessine les icônes vectorielles du jeu : atlas blanc teintable + icône de l'application.

Usage : python tools/build_icons.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw, ImageFilter          # noqa: E402

from config.paths import ICONS                          # noqa: E402

S = 512            # dessin suréchantillonné
OUT = 128
W = 34             # épaisseur du trait


class Pen:
    def __init__(self):
        self.im = Image.new("L", (S, S), 0)
        self.d = ImageDraw.Draw(self.im)

    def p(self, pts):
        return [(x * S, y * S) for x, y in pts]

    def line(self, pts, w=W, closed=False, fill=255):
        q = self.p(pts)
        if closed:
            q = q + [q[0], q[1]]
        self.d.line(q, fill=fill, width=w, joint="curve")
        if not closed:
            for x, y in (q[0], q[-1]):
                self.d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=fill)

    def poly(self, pts, fill=255):
        self.d.polygon(self.p(pts), fill=fill)

    def circ(self, x, y, r, w=W, fill=255):
        b = ((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S)
        if w:
            self.d.ellipse(b, outline=fill, width=w)
        else:
            self.d.ellipse(b, fill=fill)

    def arc(self, x, y, r, a0, a1, w=W, fill=255):
        n = 40
        self.line([(x + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), y + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)], w, fill=fill)

    def rect(self, x0, y0, x1, y1, w=W, r=.04, fill=255):
        b = (x0 * S, y0 * S, x1 * S, y1 * S)
        if w:
            self.d.rounded_rectangle(b, r * S, outline=fill, width=w)
        else:
            self.d.rounded_rectangle(b, r * S, fill=fill)


def star(p, cx, cy, r, r2, n=5, rot=-90):
    p.poly([(cx + (r if i % 2 == 0 else r2) * math.cos(math.radians(rot + i * 180 / n)), cy + (r if i % 2 == 0 else r2) * math.sin(math.radians(rot + i * 180 / n))) for i in range(2 * n)])


def draw(name: str, p: Pen):
    if name == "nitro" or name == "bolt":
        p.poly([(.58, .08), (.22, .56), (.46, .56), (.40, .92), (.78, .40), (.53, .40)])
    elif name == "shield":
        p.line([(.5, .10), (.84, .22), (.84, .52), (.5, .90), (.16, .52), (.16, .22)], closed=True)
        p.line([(.36, .48), (.47, .60), (.66, .36)])
    elif name == "magnet":
        p.arc(.5, .52, .28, 0, 180, 80)
        p.line([(.22, .52), (.22, .20)], 80)
        p.line([(.78, .52), (.78, .20)], 80)
        p.d.rectangle((.10 * S, .28 * S, .90 * S, .33 * S), fill=0)
    elif name == "repair":
        p.rect(.40, .14, .60, .86, 0)
        p.rect(.14, .40, .86, .60, 0)
    elif name == "multi":
        p.line([(.14, .34), (.40, .70)], 46)
        p.line([(.40, .34), (.14, .70)], 46)
        p.line([(.54, .36), (.60, .26), (.78, .26), (.84, .38), (.54, .74), (.86, .74)], 44)
    elif name == "slow":
        p.line([(.22, .12), (.78, .12)])
        p.line([(.22, .88), (.78, .88)])
        p.line([(.28, .14), (.28, .28), (.72, .72), (.72, .86)])
        p.line([(.72, .14), (.72, .28), (.28, .72), (.28, .86)])
        p.poly([(.36, .84), (.64, .84), (.5, .66)])
    elif name == "coin":
        p.line([(.5 + .38 * math.cos(math.radians(30 + 60 * i)), .5 + .38 * math.sin(math.radians(30 + 60 * i))) for i in range(6)], closed=True)
        p.line([(.38, .66), (.38, .34), (.62, .66), (.62, .34)], 40)
    elif name == "infinity":
        pts = [(.5 + .36 * math.sin(t), .5 + .20 * math.sin(t) * math.cos(t) * 1.9) for t in [i * math.tau / 80 for i in range(81)]]
        p.line(pts, 44)
    elif name == "clock":
        p.circ(.5, .54, .34)
        p.line([(.5, .54), (.5, .34)])
        p.line([(.5, .54), (.64, .60)])
        p.line([(.42, .08), (.58, .08)])
        p.line([(.5, .08), (.5, .18)])
    elif name == "skull":
        p.arc(.5, .44, .33, 150, 390)
        p.line([(.22, .60), (.34, .68), (.34, .86), (.66, .86), (.66, .68), (.78, .60)])
        p.circ(.38, .46, .075, 0)
        p.circ(.62, .46, .075, 0)
        p.line([(.5, .60), (.5, .64)], 26)
        p.line([(.5, .76), (.5, .86)], 24)
    elif name == "moon":
        p.circ(.48, .5, .36, 0)
        p.d.ellipse((.36 * S, .06 * S, .98 * S, .68 * S), fill=0)
        star(p, .72, .28, .12, .045, 4)
    elif name == "hand":
        for x, y in ((.30, .20), (.43, .12), (.56, .14), (.69, .24)):
            p.line([(x, y), (x, .52)], 52)
        p.line([(.16, .50), (.30, .66)], 52)
        p.poly([(.26, .48), (.74, .48), (.74, .74), (.62, .92), (.40, .92), (.24, .70)])
    elif name == "star":
        star(p, .5, .53, .44, .19)
    elif name == "flag":
        p.line([(.22, .10), (.22, .92)])
        p.rect(.22, .14, .84, .56, 26, .01)
        for i in range(4):
            for j in range(3):
                if (i + j) % 2 == 0:
                    p.rect(.24 + i * .15, .15 + j * .135, .39 + i * .15, .285 + j * .135, 0, 0)
    elif name == "road":
        p.line([(.38, .12), (.14, .90)])
        p.line([(.62, .12), (.86, .90)])
        for a, b in ((.14, .28), (.40, .58), (.70, .90)):
            p.line([(.5, a), (.5, b)], 30)
    elif name == "speed":
        p.arc(.5, .60, .38, 160, 380)
        p.line([(.5, .60), (.70, .36)])
        p.circ(.5, .60, .07, 0)
    elif name == "globe":
        p.circ(.5, .5, .38)
        p.d.ellipse((.32 * S, .12 * S, .68 * S, .88 * S), outline=255, width=26)
        p.line([(.14, .5), (.86, .5)], 26)
    elif name == "car":
        p.line([(.08, .62), (.10, .50), (.28, .46), (.40, .32), (.66, .32), (.78, .46), (.92, .50), (.93, .62)])
        p.line([(.08, .62), (.18, .62)])
        p.line([(.40, .62), (.60, .62)])
        p.line([(.82, .62), (.93, .62)])
        p.circ(.29, .64, .10)
        p.circ(.71, .64, .10)
    elif name == "lock":
        p.rect(.20, .44, .80, .88, 0, .07)
        p.arc(.5, .40, .20, 180, 360)
        p.line([(.30, .40), (.30, .48)])
        p.line([(.70, .40), (.70, .48)])
        p.circ(.5, .64, .07, 0, 0)
    elif name == "play":
        p.poly([(.28, .14), (.84, .50), (.28, .86)])
    elif name == "garage":
        p.line([(.10, .44), (.5, .14), (.90, .44)])
        p.line([(.18, .42), (.18, .88)])
        p.line([(.82, .42), (.82, .88)])
        for y in (.54, .68, .82):
            p.line([(.30, y), (.70, y)], 30)
    elif name == "trophy":
        p.line([(.30, .12), (.70, .12), (.68, .42), (.5, .58), (.32, .42)], closed=True)
        p.arc(.26, .28, .13, 90, 270, 28)
        p.arc(.74, .28, .13, -90, 90, 28)
        p.line([(.5, .58), (.5, .78)])
        p.line([(.32, .86), (.68, .86)], 44)
    elif name == "chart":
        for x, y in ((.20, .62), (.40, .40), (.60, .52), (.80, .20)):
            p.line([(x, .86), (x, y)], 60)
    elif name == "gear":
        for i in range(8):
            a = math.radians(i * 45)
            p.line([(.5 + .26 * math.cos(a), .5 + .26 * math.sin(a)), (.5 + .39 * math.cos(a), .5 + .39 * math.sin(a))], 62)
        p.circ(.5, .5, .30, 0)
        p.circ(.5, .5, .12, 0, 0)
    elif name == "exit":
        p.arc(.5, .54, .34, -55, 235)
        p.line([(.5, .10), (.5, .48)])
    elif name == "pause":
        p.rect(.22, .16, .42, .84, 0)
        p.rect(.58, .16, .78, .84, 0)
    elif name == "heart":
        p.line([(.08, .52), (.28, .52), (.38, .26), (.54, .78), (.64, .46), (.72, .52), (.92, .52)])
    elif name == "grid":
        for x in (.14, .55):
            for y in (.14, .55):
                p.rect(x, y, x + .31, y + .31)
    elif name == "keyboard":
        p.rect(.08, .24, .92, .78)
        for x in (.24, .37, .50, .63, .76):
            p.line([(x, .40), (x, .41)], 34)
        p.line([(.32, .61), (.68, .61)], 30)
    elif name == "camera":
        p.rect(.10, .26, .68, .76)
        p.poly([(.72, .46), (.92, .32), (.92, .70), (.72, .56)])
        p.circ(.39, .51, .11, 28)
    elif name == "sound":
        p.poly([(.10, .38), (.26, .38), (.46, .18), (.46, .82), (.26, .62), (.10, .62)])
        p.arc(.50, .5, .15, -50, 50, 30)
        p.arc(.50, .5, .31, -50, 50, 30)
    elif name == "screen":
        p.rect(.08, .16, .92, .70)
        p.line([(.5, .70), (.5, .86)])
        p.line([(.32, .87), (.68, .87)])
    elif name == "check":
        p.line([(.16, .52), (.40, .76), (.84, .26)], 56)
    elif name == "arrow":
        p.line([(.36, .14), (.72, .5), (.36, .86)], 50)
    elif name == "home":
        p.line([(.10, .50), (.5, .14), (.90, .50)])
        p.line([(.20, .46), (.20, .86), (.80, .86), (.80, .46)])
    elif name == "retry":
        p.arc(.5, .52, .34, -50, 220)
        p.poly([(.58, .06), (.86, .22), (.60, .42)])
    elif name == "paint":
        p.line([(.5, .10), (.78, .50)])
        p.line([(.5, .10), (.22, .50)])
        p.arc(.5, .60, .30, -20, 200)
        p.circ(.5, .62, .12, 0)
    elif name == "rim":
        p.circ(.5, .5, .40)
        p.circ(.5, .5, .08, 0)
        for i in range(5):
            a = math.radians(i * 72 - 90)
            p.line([(.5, .5), (.5 + .36 * math.cos(a), .5 + .36 * math.sin(a))], 38)
    elif name == "light":
        p.circ(.5, .5, .16, 0)
        for i in range(8):
            a = math.radians(i * 45)
            p.line([(.5 + .26 * math.cos(a), .5 + .26 * math.sin(a)), (.5 + .42 * math.cos(a), .5 + .42 * math.sin(a))], 30)
    elif name == "trail":
        for y, x0 in ((.28, .34), (.50, .12), (.72, .28)):
            p.line([(x0, y), (.88, y)], 36)
    elif name == "flame":
        p.poly([(.50, .06), (.70, .34), (.80, .58), (.72, .82), (.50, .94), (.28, .82), (.20, .58), (.34, .42), (.40, .50)])
        p.poly([(.50, .56), (.62, .72), (.56, .86), (.44, .86), (.38, .72)], 0)


NAMES = ("nitro shield magnet repair multi slow coin infinity clock skull moon hand star flag road speed bolt globe car lock play garage trophy chart "
         "gear exit pause heart grid keyboard camera sound screen check arrow home retry paint rim light trail flame").split()


def main():
    cols = 8
    rows = math.ceil(len(NAMES) / cols)
    atlas = Image.new("RGBA", (cols * OUT, rows * OUT), (255, 255, 255, 0))
    meta = {}
    for i, n in enumerate(NAMES):
        p = Pen()
        draw(n, p)
        m = p.im.resize((OUT - 12, OUT - 12), Image.LANCZOS)
        cell = Image.new("L", (OUT, OUT), 0)
        cell.paste(m, (6, 6))
        rgba = Image.merge("RGBA", [Image.new("L", (OUT, OUT), 255)] * 3 + [cell])
        x, y = (i % cols) * OUT, (i // cols) * OUT
        atlas.paste(rgba, (x, y))
        meta[n] = [x / atlas.width, y / atlas.height, (x + OUT) / atlas.width, (y + OUT) / atlas.height]
    ICONS.mkdir(parents=True, exist_ok=True)
    atlas.save(ICONS / "icons.png", optimize=True)
    (ICONS / "icons.json").write_text(json.dumps(meta, indent=1))
    # icône d'application : N biseauté sur hexagone
    n = 512
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    hexa = [(n / 2 + n * .46 * math.cos(math.radians(30 + 60 * i)), n / 2 + n * .46 * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    ImageDraw.Draw(im).polygon(hexa, fill=(9, 14, 28, 255))
    glow = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(hexa + hexa[:2], fill=(0, 229, 255, 255), width=20, joint="curve")
    for a, b, c in (((.33, .70), (.33, .30), (0, 229, 255)), ((.33, .30), (.67, .70), (90, 160, 255)), ((.67, .70), (.67, .30), (139, 92, 246))):
        gd.line([(a[0] * n, a[1] * n), (b[0] * n, b[1] * n)], fill=(*c, 255), width=52)
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(26)))
    im = Image.alpha_composite(im, glow)
    im.save(ICONS / "app.png")
    im.save(ICONS / "app.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(len(NAMES), "icônes")


if __name__ == "__main__":
    main()
