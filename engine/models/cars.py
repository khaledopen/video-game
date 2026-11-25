"""Carrosseries procédurales des huit voitures du joueur et de leurs roues.

Chaque carrosserie est un « loft » : des sections transversales calculées le long
de la voiture, avec passages de roues creusés, puis habillée de détails (vitrage,
feux, diffuseur, aileron, rétroviseurs, échappements).
"""
from __future__ import annotations

import math

import numpy as np

from engine.mesh import (ACCENT, CARBON, CHROME, GLASS, HEAD, HOLO, MATTE, PAINT, PLATE, RIM,
                         STRIPE, TAIL, TIRE, MeshBuilder)

WHEEL_R = 0.345
ARCH_R = 0.405


def _curve(xs, ys, sharp=False):
    """Interpolation cubique monotone (PCHIP), ou linéaire pour les lignes anguleuses."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if sharp:
        return lambda x: np.interp(x, xs, ys)
    h, d = np.diff(xs), np.diff(ys) / np.diff(xs)
    m = np.zeros_like(ys)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        x = np.clip(x, xs[0], xs[-1])
        i = np.clip(np.searchsorted(xs, x, side="right") - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        return ((2 * t**3 - 3 * t**2 + 1) * ys[i] + (t**3 - 2 * t**2 + t) * h[i] * m[i]
                + (-2 * t**3 + 3 * t**2) * ys[i + 1] + (t**3 - t**2) * h[i] * m[i + 1])
    return f


class CarModel:
    """Maillage de carrosserie + position des points utiles (roues, feux, échappements)."""

    def __init__(self, shape: dict):
        s = self.s = shape
        self.L, self.W, self.H = s["L"], s["W"], s["H"]
        self.hl, self.hw = self.L / 2, self.W / 2
        self.sharp = s.get("sharp", False)
        self.zf, self.zr = self.hl - 0.93, -self.hl + 0.88
        nose, deck, cab = s["nose"], s["deck"], s["cab"]
        hl = self.hl
        sh = self.sharp
        zs = [-hl, -hl * .93, -hl * .5, cab + 1.1, hl * .80, hl * .96, hl]
        self.top = _curve(zs, [deck - .07, deck, deck + .01, deck - .03 - max(0, .85 - nose) * .06,
                               nose + .12, nose + .03, nose - .07], sh)
        self.shoulder_base = _curve([-hl, -hl * .6, 0, hl * .62, hl * .93, hl],
                                    [deck - .11, deck - .05, deck - .12, nose + .20, nose + .05, nose - .05], sh)
        self.width = _curve([-hl, -hl * .9, self.zr, -.15, self.zf, hl * .86, hl],
                            [.90, .955, 1.0, .93, .985, .93, .74], sh)
        self.floor = _curve([-hl, -hl * .9, -hl * .7, hl * .7, hl * .97, hl], [.33, .27, .17, .15, .16, .22], sh)
        self.b = MeshBuilder()
        self._body()
        self._cabin()
        self._rear()
        self._front()
        self._details()
        self.mesh = self.b.build()
        self.triangles = self.b.triangles

    # -- carrosserie ----------------------------------------------------------
    def ws(self, z):
        return self.hw * self.width(z)

    def ys(self, z):
        bump = .055 * np.exp(-((z - self.zr) / .55) ** 2) + .075 * np.exp(-((z - self.zf) / .48) ** 2)
        return self.shoulder_base(z) + bump

    def arch(self, z):
        y = np.zeros_like(z)
        for za in (self.zf, self.zr):
            d2 = ARCH_R**2 - (z - za) ** 2
            y = np.maximum(y, np.where(d2 > 0, WHEEL_R - .01 + np.sqrt(np.maximum(d2, 0)), 0))
        return y

    def _body(self):
        hl = self.hl
        stations = set(np.linspace(-hl, hl, 30).round(3))
        for za in (self.zf, self.zr):
            stations |= set((za + ARCH_R * np.sin(np.linspace(-math.pi / 2, math.pi / 2, 13)) * .9995).round(4))
            stations |= {round(za - ARCH_R - .003, 4), round(za + ARCH_R + .003, 4)}
        z = np.array(sorted(x for x in stations if -hl <= x <= hl))
        w, ys, yt, yb, ar = self.ws(z), self.ys(z), self.top(z), self.floor(z), self.arch(z)
        ya = np.maximum(yb, ar)
        wi = np.minimum(w - .30, w)
        inset = .055 * np.exp(-((z - (self.zr + .75)) / .42) ** 2)          # prise d'air latérale
        ymid = ya + (ys - ya) * .48
        pts = np.stack([
            np.stack([0 * z, yb, z], -1),
            np.stack([wi, yb, z], -1),
            np.stack([wi, np.maximum(yb, ar), z], -1),
            np.stack([w * .985, ya, z], -1),
            np.stack([w - inset * .5, ya + (ys - ya) * .16, z], -1),
            np.stack([w * 1.0 - inset, ymid, z], -1),
            np.stack([w * .992, ya + (ys - ya) * .82, z], -1),
            np.stack([w * .945, ys, z], -1),
            np.stack([w * .74, ys + (yt - ys) * .55, z], -1),
            np.stack([w * .38, yt, z], -1),
            np.stack([0 * z, yt + .012, z], -1),
        ], axis=1)
        mats = np.full((len(z) - 1, 10), PAINT, float)
        mats[:, 0] = CARBON
        mats[:, 1] = MATTE
        mats[:, 2] = MATTE
        zc = (z[:-1] + z[1:]) / 2
        sill = (np.abs(zc - (self.zf + self.zr) / 2) < (self.zf - self.zr) / 2 - ARCH_R)
        mats[sill, 3] = CARBON
        intake = (zc > self.zr + ARCH_R + .04) & (zc < self.zr + ARCH_R + .48)
        mats[intake, 4] = CARBON
        self.b.grid(pts, mats, crease=14 if self.sharp else 38)
        for k in (0, -1):                                                     # faces avant / arrière
            ring = pts[k]
            mid = np.array([0, (ring[0, 1] + ring[-1, 1]) / 2, ring[0, 2]])
            self.b.add([[mid, ring[i], ring[i + 1]] for i in range(len(ring) - 1)], PAINT)
        self.b.mirror_x()

    def _cabin(self):
        s, b = self.s, MeshBuilder()
        cab, H, W = s["cab"], self.H, self.W
        zf, z1, z0 = cab + 1.18, cab + .22, cab - .50
        zb = max(cab - 1.62, -self.hl + .34)
        z = np.unique(np.concatenate([np.linspace(zb, z0, 9), np.linspace(z0, z1, 6), np.linspace(z1, zf, 8)]))
        base = self.top(z)
        yr = _curve([zb, zb + .12, z0, (z0 + z1) / 2, z1, zf],
                    [0, .10, .965, 1.0, .965, 0], self.sharp)(z)
        y = base - .015 + (H - base) * yr
        wb = W * .5 * _curve([zb, z0, z1, zf], [.62, .80, .80, .70])(z)
        wr = W * .5 * _curve([zb, z0, z1, zf], [.48, .565, .575, .62])(z)
        k = np.clip(yr * 1.3, 0, 1)
        wr = wb + (wr - wb) * k
        pts = np.stack([
            np.stack([wb, base - .05, z], -1),
            np.stack([wb + (wr - wb) * .80, base + (y - base) * .80, z], -1),
            np.stack([wb + (wr - wb) * .94, base + (y - base) * .93, z], -1),
            np.stack([wr * .93, y - .006, z], -1),
            np.stack([wr * .5, y + .006 * k, z], -1),
            np.stack([0 * z, y + .012 * k, z], -1),
        ], 1)
        zc = (z[:-1] + z[1:]) / 2
        mats = np.full((len(z) - 1, 5), GLASS, float)
        mats[:, 1:3] = PAINT
        roof = (zc > z0 + .02) & (zc < z1 - .02)
        mats[roof, 3:] = CARBON if s["wing"] in ("gt", "long") else PAINT
        pillar = (zc > z0 - .16) & (zc < z0 + .02)
        mats[pillar, 0] = PAINT
        if s.get("fin") or s["cab"] > .04:                                    # moteur central : lames de capot
            rear = zc < zb + .62
            mats[rear, 3:] = CARBON
        b.grid(pts, mats, crease=14 if self.sharp else 42)
        b.mirror_x()
        self.b.merge(b)
        if s["cab"] > .04:
            for i in range(4):
                zz = zb + .16 + i * .13
                yy = float(np.interp(zz, z, y)) + .022
                self.b.box((0, yy, zz), (W * .40, .016, .05), CARBON, shift=(0, .02))
        self.cab_z = (z0 + z1) / 2

    # -- poupe ------------------------------------------------------------------
    def _tubes(self, lines, mat, r, z):
        for line in lines:
            for sx in (1, -1):
                self.b.tube([(sx * x, y, z) for x, y in line], r, mat, 6)

    def _rear(self):
        s, b, hl = self.s, self.b, self.hl
        w, y1, y0 = float(self.ws(-hl)), float(self.ys(-hl)), float(self.floor(-hl))
        z = -hl - .012
        ph = y1 - y0
        panel = [(-w * .93, y0 + ph * .40), (-w * .88, y0 + ph * .16), (w * .88, y0 + ph * .16),
                 (w * .93, y0 + ph * .40), (w * .90, y1 - ph * .10), (-w * .90, y1 - ph * .10)]
        b.extrude(panel, z, -hl + .02, CARBON)
        zt, yc = z - .016, y0 + ph * .66
        kind, r = s["tail"], .017
        half = w * .86
        if kind == "bar":
            self._tubes([[(0, yc), (half * .78, yc), (half, yc + .045), (half * .99, yc - .10), (half * .72, yc - .13)]], TAIL, r, zt)
        elif kind == "claw":
            for i in range(4):
                x = half * (.98 - i * .13)
                self._tubes([[(x, yc + .085), (x - .10, yc - .02), (x - .09, yc - .10)]], TAIL, r * .95, zt)
            self._tubes([[(0, yc + .085), (half * .52, yc + .085)]], TAIL, r * .5, zt)
        elif kind == "round":
            for sx in (1, -1):
                for x in (half * .86, half * .56):
                    b.torus((sx * x, yc - .01, zt), .082, r * .95, "z", TAIL, 22, 6)
                    b.cylinder((sx * x, yc - .01, zt + .005), .038, .02, "z", TAIL, 14)
        elif kind == "triple":
            for sx in (1, -1):
                for i in range(3):
                    x = half * (.94 - i * .21)
                    b.box((sx * x, yc, zt), (.085, .19, .03), TAIL, taper=(.85, 1))
            b.box((0, yc, zt + .004), (half * .72, .13, .02), CHROME)
        elif kind == "frame":
            self._tubes([[(0, yc + .10), (half, yc + .10), (half, yc - .10), (0, yc - .10)]], TAIL, r * .8, zt)
            self._tubes([[(half * .6, yc + .10), (half * .6, yc - .10)]], TAIL, r * .6, zt)
        elif kind == "flame":
            self._tubes([[(half * .14, yc - .02), (half * .42, yc - .07), (half * .50, yc + .05), (half * .70, yc - .06),
                          (half * .78, yc + .07), (half, yc + .02)],
                         [(half * .46, yc - .12), (half * .99, yc - .10)]], TAIL, r, zt)
        elif kind == "wave":
            xs = np.linspace(0, 1, 16)
            self._tubes([[(half * x, yc + .06 * math.sin(x * 7.5 + 1.2)) for x in xs],
                         [(half * x, yc + .06 * math.sin(x * 7.5 + 1.2) - .075) for x in xs[4:]]], TAIL, r * .8, zt)
        else:                                                                  # halo
            b.torus((0, yc, zt), .11, r * .85, "z", TAIL, 30, 6)
            b.torus((0, yc, zt), .065, r * .4, "z", ACCENT, 24, 6)
            self._tubes([[(.11, yc), (half * .72, yc), (half * .86, yc + .06), (half, yc + .06)],
                         [(half * .72, yc - .012), (half * .9, yc - .09)]], TAIL, r * .8, zt)
        b.box((0, y0 + ph * .27, z - .012), (.42, .085, .018), PLATE)
        # diffuseur
        dw = w * .84
        b.quad((-dw, y0 + .03, -hl - .005), (dw, y0 + .03, -hl - .005), (dw * .96, .15, -hl + .62), (-dw * .96, .15, -hl + .62), CARBON)
        for i in range(7):
            x = (i - 3) / 3 * dw * .82
            b.extrude([(-hl - .02, y0 + .035), (-hl + .45, y0 - .02), (-hl + .45, .14), (-hl + .01, y0 - .10)],
                      x - .009, x + .009, CARBON, "x")
        self._tubes([[(0, y0 + .028), (dw, y0 + .028)]], ACCENT, .008, z - .006)
        # échappements
        ex, ye = s["exhaust"], y0 + .085
        pos = {"twin": [w * .62, -w * .62], "quad": [w * .70, w * .53, -w * .53, -w * .70],
               "center": [.10, -.10], "none": []}[ex]
        self.exhausts = [(x, ye, -hl - .08) for x in pos] or [(w * .5, ye, -hl - .02), (-w * .5, ye, -hl - .02)]
        for x in pos:
            b.cylinder((x, ye, -hl - .02), .058, .12, "z", CHROME, 18, MATTE, caps=(False, True))
            b.cylinder((x, ye, -hl - .025), .047, .11, "z", MATTE, 18)
            b.torus((x, ye, -hl - .08), .053, .007, "z", CHROME, 20, 6)
        self._wing(w, y1)
        self.tail_points = [(half * .9, yc, zt - .03), (-half * .9, yc, zt - .03)]

    def _wing(self, w, y1):
        b, hl, kind = self.b, self.hl, self.s["wing"]
        deck = float(self.top(-hl * .93))
        if kind in ("lip", "duck"):
            h = .055 if kind == "lip" else .12
            xs = np.linspace(-w * .92, w * .92, 13)
            rows = []
            for x in xs:
                e = 1 - (abs(x) / w) ** 4 * .6
                yb = deck - .075 - .045 * (abs(x) / w) ** 2
                rows.append([(x, yb + .05, -hl + .30), (x, yb + .06 + h * e * .55, -hl + .07),
                             (x, yb + .05 + h * e, -hl - .045), (x, yb + .035 + h * e, -hl - .05),
                             (x, yb, -hl - .004)])
            b.grid(np.array(rows), CARBON if kind == "duck" else PAINT, crease=35)
        elif kind in ("gt", "long"):
            span, hh = w * .99, (.27 if kind == "gt" else .20)
            yw, zc = deck + hh, -hl + (.14 if kind == "gt" else .02)
            chord = .34 if kind == "gt" else .46
            xs = np.linspace(-span, span, 11)
            rows = []
            for x in xs:
                dip = .035 * (1 - (x / span) ** 2)
                y = yw - dip
                rows.append([(x, y, zc + chord / 2), (x, y + .030, zc + chord * .2), (x, y + .050, zc - chord * .35),
                             (x, y + .075, zc - chord / 2), (x, y + .062, zc - chord / 2), (x, y + .012, zc),
                             (x, y - .006, zc + chord / 2)])
            b.grid(np.array(rows), CARBON, crease=50)
            for sx in (1, -1):
                b.extrude([(zc - chord * .62, yw - .10), (zc + chord * .52, yw - .07), (zc + chord * .52, yw + .05),
                           (zc - chord * .62, yw + .13)], sx * span - .010, sx * span + .010, PAINT, "x")
                x = sx * w * .52
                b.extrude([(zc - .10, deck - .10), (zc + .22, deck - .08), (zc + .10, yw - .01), (zc - .03, yw - .01)],
                          x - .012, x + .012, CARBON, "x")
            b.tube([(-span, yw + .068, zc - chord / 2 - .006), (0, yw + .033, zc - chord / 2 - .006),
                    (span, yw + .068, zc - chord / 2 - .006)], .008, ACCENT, 5)
        if self.s.get("fin"):
            z0 = self.s["cab"] - .55
            b.extrude([(z0, self.H - .03), (-hl + .30, deck + .02), (-hl + .16, deck + .20), (z0 - .5, self.H - .02)],
                      -.011, .011, CARBON, "x")

    # -- proue --------------------------------------------------------------------
    def _front(self):
        b, s, hl = self.b, self.s, self.hl
        nose = s["nose"]
        w = float(self.ws(hl))
        # lame et bouclier
        pts = [(-w * 1.12, hl - .34), (-w * .96, hl + .00), (-w * .45, hl + .085), (w * .45, hl + .085),
               (w * .96, hl + .00), (w * 1.12, hl - .34)]
        lo, hi = [(x, .125, z) for x, z in pts], [(x, .150, z) for x, z in pts]
        for i in range(len(pts) - 1):
            b.quad(lo[i], lo[i + 1], hi[i + 1], hi[i], CARBON)
        b.add([[hi[0], hi[i], hi[i + 1]] for i in range(1, 5)], CARBON)
        b.add([[lo[0], lo[i], lo[i + 1]] for i in range(1, 5)], CARBON)
        b.extrude([(-w * .52, .22), (w * .52, .22), (w * .64, nose - .20 + .06), (-w * .64, nose - .20 + .06)],
                  hl - .02, hl + .012, MATTE)
        for sx in (1, -1):
            b.extrude([(sx * w * .60, .24), (sx * w * .92, .28), (sx * w * .90, nose - .14), (sx * w * .70, nose - .16)],
                      hl - .06, hl + .006, CARBON)
        b.tube([(-w * .60, nose - .125, hl + .016), (w * .60, nose - .125, hl + .016)], .008, ACCENT, 5)
        # phares posés sur la surface du capot
        kind = s["head"]

        def on(x_frac, z, up=.012):
            ww = float(self.ws(z))
            ys, yt = float(self.ys(z)), float(self.top(z))
            x = ww * x_frac
            if x_frac > .74:
                y = ys + (x_frac - .945) / (.74 - .945) * ((ys + (yt - ys) * .55) - ys)
            else:
                y = ys + (yt - ys) * (.55 + (.74 - x_frac) / .36 * .45)
            return (x, y + up, z)

        for sx in (1, -1):
            def line(pairs, r, mat=HEAD):
                b.tube([(sx * p[0], p[1], p[2]) for p in (on(*q) for q in pairs)], r, mat, 6)
            if kind == "slim":
                line([(.62, hl - .10), (.80, hl - .20), (.90, hl - .46)], .020)
                line([(.60, hl - .18), (.76, hl - .30)], .012)
            elif kind == "blade":
                line([(.55, hl - .10), (.88, hl - .26), (.93, hl - .62)], .018)
                line([(.80, hl - .22), (.72, hl - .46)], .014)
            elif kind == "oval":
                p = on(.78, hl - .34, .01)
                b.torus((sx * p[0], p[1], p[2]), .085, .016, "z", HEAD, 20, 6)
                b.cylinder((sx * p[0], p[1], p[2] - .01), .06, .05, "z", GLASS, 16)
                b.cylinder((sx * p[0], p[1], p[2] + .01), .028, .05, "z", HEAD, 12)
            elif kind == "muscle":
                for x in (.60, .84):
                    b.torus((sx * w * x, nose - .085, hl + .005), .062, .013, "z", HEAD, 18, 6)
                    b.cylinder((sx * w * x, nose - .085, hl + .002), .05, .03, "z", HEAD, 14)
            else:
                line([(.10, hl - .03), (.56, hl - .05), (.82, hl - .16), (.90, hl - .34)], .014)
        if kind == "bar":
            p = on(.10, hl - .03)
            b.tube([(-p[0], p[1], p[2]), p], .014, HEAD, 6)
        self.head_points = [(w * .75, nose - .05, hl), (-w * .75, nose - .05, hl)]

    def _details(self):
        b, s = self.b, self.s
        # rétroviseurs
        zmir = s["cab"] + .72
        for sx in (1, -1):
            x, y = sx * float(self.ws(np.float64(zmir))) * .95, float(self.ys(np.float64(zmir))) + .13
            b.box((x + sx * .02, y, zmir), (.17, .10, .12), PAINT, taper=(.9, .7), shift=(0, -.01))
            b.tube([(x - sx * .10, y - .10, zmir + .02), (x, y - .02, zmir)], .014, CARBON, 5)
            b.box((x + sx * .02, y, zmir - .064), (.13, .07, .008), CHROME)
        # bas de caisse + liseré lumineux
        z0, z1 = self.zr + ARCH_R + .04, self.zf - ARCH_R - .04
        zz = np.linspace(z0, z1, 6)
        for sx in (1, -1):
            w = self.ws(zz)
            b.grid(np.array([[(sx * (a - .02), .20, z), (sx * (a + .045), .165, z), (sx * (a + .045), .145, z),
                              (sx * (a - .10), .14, z)] for a, z in zip(w, zz)]), CARBON)
            b.tube([(sx * (a + .05), .155, z) for a, z in zip(w, zz)], .009, ACCENT, 5)
        # nervures du capot
        zh = np.linspace(s["cab"] + 1.16, self.hl - .22, 8)
        for sx in (1, -1):
            b.tube([(sx * float(self.ws(z)) * .36, float(self.top(z)) + .004, z) for z in zh], .012, PAINT, 6)
        # ouïes de capot
        for sx in (1, -1):
            for i in range(3):
                z = self.hl - .95 - i * .10
                if z < s["cab"] + 1.2:
                    break
                y = float(self.top(np.float64(z)))
                b.box((sx * float(self.ws(np.float64(z))) * .50, y + .004, z), (.20, .012, .035), CARBON)
        if s["scoop"]:
            if s["head"] == "muscle":
                z = self.hl - 1.25
                y = float(self.top(np.float64(z)))
                b.box((0, y + .055, z), (.52, .11, .62), PAINT, taper=(.82, .72), shift=(0, -.06))
                b.box((0, y + .060, z + .30), (.38, .05, .04), MATTE)
            else:
                z = s["cab"] - .42
                b.box((0, self.H + .035, z), (.34, .11, .55), CARBON, taper=(.7, .55), shift=(0, -.08))
                b.box((0, self.H + .035, z + .255), (.22, .06, .03), MATTE)
        # bandes décoratives sur le capot pour les modèles à caractère
        if s["tail"] in ("triple", "round"):
            for x in (-.16, .16):
                rows = [[(x - .075, float(self.top(z)) + .0155, z), (x + .075, float(self.top(z)) + .0155, z)]
                        for z in np.linspace(s["cab"] + 1.14, self.hl - .06, 12)]
                b.grid(np.array(rows), STRIPE)
        b.tube([(0, self.H - .02, self.cab_z - .28), (0, self.H + .07, self.cab_z - .36)], .010, CARBON, 5)

    @property
    def wheels(self):
        """(x, y, z, braque) des quatre roues."""
        xf = float(self.ws(np.float64(self.zf))) - .135
        xr = float(self.ws(np.float64(self.zr))) - .145
        return [(xf, WHEEL_R, self.zf, True), (-xf, WHEEL_R, self.zf, True),
                (xr, WHEEL_R, self.zr, False), (-xr, WHEEL_R, self.zr, False)]


# -- roues ------------------------------------------------------------------------
def _lathe(b, profile, mat, seg=28):
    ang = np.linspace(0, 2 * math.pi, seg + 1)
    pts = np.array([[(x, r * math.sin(a), r * math.cos(a)) for x, r in profile] for a in ang])
    b.grid(pts, mat, crease=48)


def wheel(style: int) -> np.ndarray:
    """Roue de rayon 1 (axe x, face extérieure vers +x)."""
    b = MeshBuilder()
    _lathe(b, [(-.42, .70), (-.44, .86), (-.38, .97), (-.2, 1.0), (.2, 1.0), (.38, .97), (.44, .86), (.40, .73)], TIRE)
    _lathe(b, [(.40, .73), (.41, .70), (.33, .66), (-.1, .64), (-.42, .70)], RIM)
    b.cylinder((.10, 0, 0), .46, .06, "x", CHROME, 24)           # disque de frein
    b.box((.12, .30, .28), (.14, .30, .22), ACCENT)              # étrier
    b.cylinder((.30, 0, 0), .13, .12, "x", RIM, 14, CARBON)
    if style == 0:                                                # Turbine
        for i in range(12):
            a = 2 * math.pi * i / 12
            p = [(r * math.cos(a + t), r * math.sin(a + t)) for r, t in ((.10, 0), (.68, .30), (.68, .46), (.12, .30))]
            b.add([[(.33, p[0][1], p[0][0]), (.39, p[1][1], p[1][0]), (.31, p[2][1], p[2][0])],
                   [(.33, p[0][1], p[0][0]), (.31, p[2][1], p[2][0]), (.27, p[3][1], p[3][0])]], RIM)
    elif style == 1:                                              # Étoile à 5 branches doubles
        for i in range(5):
            for off in (-.13, .13):
                a = 2 * math.pi * i / 5 + off
                c, s = math.cos(a), math.sin(a)
                q = [(r * c - w * s, r * s + w * c) for r, w in ((.08, -.055), (.70, -.04), (.70, .04), (.08, .055))]
                b.quad(*[(x, p[1], p[0]) for p, x in zip(q, (.36, .40, .40, .36))], RIM)
                for e in ((0, 1), (2, 3)):
                    p, r = q[e[0]], q[e[1]]
                    b.quad((.38, p[1], p[0]), (.40, r[1], r[0]), (.24, r[1], r[0]), (.24, p[1], p[0]), RIM)
    elif style == 2:                                              # Multibranche fin
        for i in range(10):
            for off in (-.10, .10):
                a0, a1 = 2 * math.pi * i / 10, 2 * math.pi * i / 10 + off * 1.6
                b.tube([(.33, .10 * math.sin(a0), .10 * math.cos(a0)), (.38, .69 * math.sin(a1), .69 * math.cos(a1))],
                       .026, RIM, 5)
    else:                                                         # Holo : anneaux lumineux
        b.torus((.36, 0, 0), .60, .030, "x", ACCENT, 30, 6)
        b.torus((.36, 0, 0), .36, .020, "x", ACCENT, 24, 6)
        for i in range(6):
            a = 2 * math.pi * i / 6
            c, s = math.cos(a), math.sin(a)
            q = [(r * c - w * s, r * s + w * c) for r, w in ((.12, -.10), (.68, -.03), (.68, .03), (.12, .10))]
            b.quad(*[(.35, p[1], p[0]) for p in q], RIM)
    return b.build()
