"""Véhicules de la circulation : berlines, sportives, utilitaires, bus et camions."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.mesh import (ACCENT, AMBER, CARBON, CHROME, GLASS, HEAD, MATTE, PAINT, PLATE, STRIPE,
                         TAIL, MeshBuilder)
from engine.models.cars import CarModel


@dataclass
class TrafficModel:
    mesh: np.ndarray
    length: float
    width: float
    height: float
    wheels: list            # (x, rayon, z)
    tails: list             # (x, y, z)


def _car(shape) -> TrafficModel:
    m = CarModel(shape)
    return TrafficModel(m.mesh, m.L, m.W, m.H, [(x, r, z) for x, r, z, _ in m.wheels], m.tail_points)


def sedan() -> TrafficModel:
    return _car(dict(L=4.62, W=1.84, H=1.44, nose=.72, deck=.98, cab=-.10, wing="none", tail="bar", head="slim",
                     exhaust="twin", scoop=False, fin=0))


def compact() -> TrafficModel:
    return _car(dict(L=4.02, W=1.78, H=1.50, nose=.76, deck=1.02, cab=-.18, wing="lip", tail="round", head="oval",
                     exhaust="none", scoop=False, fin=0))


def coupe() -> TrafficModel:
    return _car(dict(L=4.48, W=1.92, H=1.28, nose=.56, deck=.90, cab=-.05, wing="duck", tail="claw", head="blade",
                     exhaust="twin", scoop=False, fin=0))


def roadster() -> TrafficModel:
    return _car(dict(L=4.50, W=1.96, H=1.20, nose=.48, deck=.86, cab=.10, wing="gt", tail="wave", head="bar",
                     exhaust="center", scoop=False, fin=0))


def _shell(b: MeshBuilder, stations, mat, crease=35, bevel=.10):
    """Coque à section rectangulaire adoucie. stations : (z, y0, y1, demi-largeur)."""
    rows = []
    for z, y0, y1, w in stations:
        r = min(bevel, (y1 - y0) * .3)
        rows.append([(0, y0, z), (w * .97, y0, z), (w, y0 + r, z), (w, (y0 + y1) / 2, z), (w * .99, y1 - r, z),
                     (w * .99 - r * .8, y1, z), (0, y1 + .01, z)])
    pts = np.array(rows)
    b.grid(pts, mat, crease=crease)
    for k in (0, -1):
        mid = np.array([0, (pts[k, 0, 1] + pts[k, -1, 1]) / 2, pts[k, 0, 2]])
        b.add([[mid, pts[k, i], pts[k, i + 1]] for i in range(6)], mat)


def van() -> TrafficModel:
    L, W, H = 5.3, 2.02, 2.30
    b = MeshBuilder()
    hl, hw = L / 2, W / 2
    _shell(b, [(-hl, .38, H - .06, hw * .96), (-hl + .12, .32, H, hw), (hl - 1.75, .30, H, hw), (hl - 1.30, .30, H - .10, hw),
               (hl - .62, .30, 1.30, hw * .98), (hl - .10, .30, 1.08, hw * .92), (hl, .36, .92, hw * .84)], PAINT)
    b.mirror_x()
    c = MeshBuilder()
    c.quad((0, 1.36, hl - .66), (hw * .86, 1.36, hl - .67), (hw * .83, H - .17, hl - 1.26), (0, H - .15, hl - 1.25), GLASS)
    c.quad((hw + .004, 1.32, hl - 1.00), (hw + .004, 1.32, hl - 1.90), (hw + .004, H - .34, hl - 1.90), (hw + .004, H - .34, hl - 1.36), GLASS)
    for z in (-hl + 1.0, -hl + 2.3):
        c.box((hw + .004, 1.2, z), (.012, 1.5, .02), CARBON)
    c.box((hw + .012, .62, 0), (.02, .10, L * .62), CARBON)
    c.box((hw + .02, .50, -.2), (.012, .025, L * .55), ACCENT)
    c.box((hw + .12, 1.40, hl - .98), (.18, .28, .10), CARBON)
    c.box((hw * .84, 1.35, -hl - .015), (.13, .62, .05), TAIL)
    c.box((hw * .62, .92, hl - .01), (.34, .12, .10), HEAD)
    c.quad((.06, 1.28, -hl - .008), (hw * .66, 1.28, -hl - .008), (hw * .62, H - .28, -hl + .01), (.06, H - .28, -hl + .01), GLASS)
    c.mirror_x()
    b.merge(c)
    b.box((0, 1.25, -hl - .012), (.024, 1.7, .02), CARBON)
    b.box((0, .44, -hl - .06), (W * .94, .18, .16), CARBON)
    b.box((0, .72, -hl - .02), (.5, .11, .02), PLATE)
    b.box((0, H + .03, -hl + .05), (.9, .05, .06), TAIL)
    b.box((0, .55, hl + .02), (W * .62, .26, .06), MATTE)
    for z in (-1.2, -.3, .6):
        b.box((0, H + .05, z), (W * .86, .04, .05), CHROME)
    return TrafficModel(b.build(), L, W, H, [(hw - .14, .37, hl - 1.02), (-hw + .14, .37, hl - 1.02),
                                             (hw - .14, .37, -hl + 1.02), (-hw + .14, .37, -hl + 1.02)],
                        [(hw * .84, 1.35, -hl - .06), (-hw * .84, 1.35, -hl - .06)])


def bus() -> TrafficModel:
    L, W, H = 11.0, 2.52, 3.15
    b = MeshBuilder()
    hl, hw = L / 2, W / 2
    _shell(b, [(-hl, .44, H - .22, hw * .95), (-hl + .20, .36, H, hw), (hl - .50, .34, H, hw), (hl - .10, .34, H - .22, hw * .97),
               (hl, .40, 1.4, hw * .94)], PAINT, bevel=.22)
    b.mirror_x()
    c = MeshBuilder()
    c.box((hw + .004, 2.05, -.1), (.012, 1.05, L - 1.1), GLASS)
    for i in range(9):
        c.box((hw + .012, 2.05, -hl + 1.0 + i * 1.18), (.014, 1.05, .07), CARBON)
    c.box((hw + .012, 1.02, 0), (.016, .06, L - .8), ACCENT)
    c.box((hw + .012, 2.78, 0), (.016, .035, L - .8), ACCENT)
    c.box((hw * .86, 1.12, -hl - .02), (.20, .80, .06), TAIL)
    c.box((hw * .80, H - .40, -hl + .02), (.20, .09, .05), TAIL)
    c.box((hw * .70, .85, hl + .01), (.42, .16, .08), HEAD)
    c.box((hw + .16, 2.2, hl - .25), (.18, .50, .10), CARBON)
    c.mirror_x()
    b.merge(c)
    b.quad((-hw * .84, 1.72, -hl - .012), (hw * .84, 1.72, -hl - .012), (hw * .82, 2.62, -hl + .004), (-hw * .82, 2.62, -hl + .004), GLASS)
    b.quad((-hw * .88, 1.45, hl + .012), (hw * .88, 1.45, hl + .012), (hw * .86, 2.75, hl - .06), (-hw * .86, 2.75, hl - .06), GLASS)
    b.box((0, 2.80, -hl + .01), (1.25, .20, .05), AMBER)
    b.box((0, .95, -hl - .02), (1.7, .72, .03), CARBON)
    for i in range(6):
        b.box((0, .70 + i * .10, -hl - .04), (1.55, .022, .03), MATTE)
    b.box((0, .48, -hl - .06), (W * .95, .20, .16), CARBON)
    b.box((0, .50, -hl - .15), (.5, .11, .02), PLATE)
    b.box((0, H + .14, -1.6), (1.7, .28, 2.6), PAINT, taper=(.86, .9))
    b.box((0, H + .10, 2.0), (1.2, .20, 1.5), CARBON, taper=(.86, .9))
    return TrafficModel(b.build(), L, W, H, [(hw - .16, .48, hl - 2.3), (-hw + .16, .48, hl - 2.3),
                                             (hw - .16, .48, -hl + 2.6), (-hw + .16, .48, -hl + 2.6)],
                        [(hw * .86, 1.12, -hl - .08), (-hw * .86, 1.12, -hl - .08)])


def truck() -> TrafficModel:
    L, W, H = 13.2, 2.56, 3.85
    b = MeshBuilder()
    hl, hw = L / 2, W / 2
    zt0, zt1 = -hl, hl - 3.1
    b.box((0, 2.42, (zt0 + zt1) / 2), (W, 2.80, zt1 - zt0), PAINT)                  # remorque
    b.box((0, .96, (zt0 + zt1) / 2), (W * .55, .18, zt1 - zt0 - .3), CARBON)
    c = MeshBuilder()
    for k in range(8):                                                               # nervures latérales
        c.box((hw + .01, 2.42, zt0 + .7 + k * 1.2), (.03, 2.6, .05), CHROME)
    c.box((hw + .02, 1.05, (zt0 + zt1) / 2), (.03, .05, zt1 - zt0), ACCENT)
    c.box((hw + .02, 3.79, (zt0 + zt1) / 2), (.03, .05, zt1 - zt0), ACCENT)
    c.box((hw - .05, .62, (zt0 + zt1) / 2 + .6), (.05, .50, 4.2), CARBON)            # carénage
    # poupe : portes, barres, gabarit lumineux
    c.box((hw * .5, 2.42, zt0 - .012), (hw * .94, 2.62, .02), STRIPE)
    c.box((hw * .5, 2.42, zt0 - .022), (hw * .86, 2.50, .02), PAINT)
    for x in (.28, .62):
        c.tube([(hw * x, 1.08, zt0 - .06), (hw * x, 3.72, zt0 - .06)], .022, CHROME, 6)
        c.box((hw * x + .06, 1.75, zt0 - .07), (.20, .05, .04), CHROME)
    c.box((hw - .05, 2.42, zt0 - .025), (.06, 2.74, .03), ACCENT)
    c.box((hw * .78, .80, zt0 - .05), (.40, .17, .07), TAIL)
    c.box((hw * .40, .80, zt0 - .05), (.20, .10, .06), AMBER)
    c.box((hw * .82, 3.80, zt0 - .02), (.28, .06, .05), TAIL)
    c.mirror_x()
    b.merge(c)
    b.box((0, 3.80, zt0 - .02), (W * .55, .05, .03), ACCENT)
    b.box((0, .78, zt0 - .02), (W * .98, .26, .08), CARBON)
    b.box((0, .48, zt0 - .02), (W * .90, .10, .10), CHROME)
    b.box((0, .62, zt0 - .07), (.5, .11, .02), PLATE)
    d = MeshBuilder()                                                                # cabine
    _shell(d, [(hl - 2.75, .55, 3.45, hw * .96), (hl - .85, .50, 3.50, hw * .96), (hl - .30, .45, 2.75, hw * .95),
               (hl - .04, .42, 1.6, hw * .95), (hl, .46, 1.2, hw * .92)], PAINT, bevel=.18)
    d.quad((0, 1.95, hl - .10), (hw * .84, 1.95, hl - .12), (hw * .82, 2.72, hl - .30), (0, 2.72, hl - .28), GLASS)
    d.box((hw * .965, 2.25, hl - 1.2), (.02, .75, 1.05), GLASS)
    d.box((hw * .70, .95, hl + .01), (.40, .22, .08), HEAD)
    d.box((hw * .97, .95, hl - 1.6), (.02, .05, 2.0), ACCENT)
    d.box((hw + .14, 2.35, hl - .38), (.20, .62, .12), CARBON)
    d.mirror_x()
    b.merge(d)
    b.box((0, 1.15, hl + .015), (W * .55, .70, .05), MATTE)
    b.box((0, 3.60, hl - 1.8), (W * .8, .40, 1.7), PAINT, taper=(.85, .6), shift=(0, -.2))
    wheels = []
    for z in (hl - 1.1, hl - 3.6, -hl + 1.3, -hl + 2.5, -hl + 3.7):
        wheels += [(hw - .18, .50, z), (-hw + .18, .50, z)]
    return TrafficModel(b.build(), L, W, H, wheels, [(hw * .78, .80, zt0 - .1), (-hw * .78, .80, zt0 - .1)])


MODELS = {"sedan": sedan, "compact": compact, "coupe": coupe, "roadster": roadster, "van": van, "bus": bus,
          "truck": truck}
