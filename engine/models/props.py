"""Obstacles, bonus, pièces et éléments de décor procéduraux."""
from __future__ import annotations

import math

import numpy as np

from engine.mesh import (ACCENT, AMBER, BUILDING, CARBON, CHROME, CONCRETE, CONE, EMIT, FOLIAGE, HOLO, MATTE, PAINT,
                         ROCK, SIGN, STRIPE, TIRE, TRUNK, WOOD, MeshBuilder)


def _rock(seed: int, detail: int = 9, squash=.8, flat=False) -> MeshBuilder:
    rng = np.random.default_rng(seed)
    b = MeshBuilder()
    n, m = detail, detail + 3
    th = np.linspace(0, math.pi * .62, n)
    ph = np.linspace(0, 2 * math.pi, m)
    k = rng.random((3, 4))
    pts = np.zeros((n, m, 3))
    for i, t in enumerate(th):
        for j, p in enumerate(ph):
            r = 1 + .22 * math.sin(3 * p + k[0, 0] * 9) * math.sin(t * 3 + k[1, 0] * 9) + .16 * math.sin(5 * p + k[2, 0] * 9 + t * 4)
            y = math.cos(t) * squash
            if flat:
                y = min(y, .62 + .04 * math.sin(p * 3))
            pts[i, j] = (r * math.sin(t) ** .7 * math.cos(p), max(y, -.1) + .05, r * math.sin(t) ** .7 * math.sin(p))
    pts[:, -1] = pts[:, 0]
    b.grid(pts, ROCK, crease=28)
    return b


# -- obstacles ------------------------------------------------------------------
def barrier() -> np.ndarray:
    """Glissière lourde, 3,2 m de large, perpendiculaire à la route."""
    b = MeshBuilder()
    prof = [(-.36, 0), (-.36, .12), (-.17, .38), (-.12, .92), (.12, .92), (.17, .38), (.36, .12), (.36, 0)]
    for k in range(2):
        x0, x1 = -1.6 + k * 1.62, -.02 + k * 1.62
        b.grid(np.array([[(x, y, z) for z, y in prof] for x in np.linspace(x0, x1, 3)]), CONCRETE, crease=30)
        for x in (x0, x1):
            b.add([[(x, prof[0][1], prof[0][0]), (x, prof[i][1], prof[i][0]), (x, prof[i + 1][1], prof[i + 1][0])]
                   for i in range(1, 7)], CONCRETE)
    for i in range(5):                                    # chevrons lumineux vers le joueur
        x = -1.28 + i * .64
        b.quad((x - .18, .46, -.178), (x - .05, .46, -.178), (x + .08, .64, -.160), (x - .05, .64, -.160), EMIT)
        b.quad((x - .05, .64, -.160), (x + .08, .64, -.160), (x - .05, .82, -.144), (x - .18, .82, -.144), EMIT)
    for x in (-1.35, 0, 1.35):
        b.cylinder((x, 1.0, 0), .075, .16, "y", AMBER, 10)
        b.cylinder((x, .93, 0), .09, .04, "y", CARBON, 10)
    return b.build()


def cone() -> np.ndarray:
    b = MeshBuilder()
    b.box((0, .03, 0), (.46, .06, .46), CONE, taper=(.94, .94))
    ang = np.linspace(0, 2 * math.pi, 15)
    prof = [(.18, .06), (.055, .74), (.03, .76)]
    pts = np.array([[(r * math.cos(a), y, r * math.sin(a)) for r, y in prof] for a in ang])
    b.grid(pts, CONE, crease=60)
    return b.build()


def roadworks() -> np.ndarray:
    """Remorque à flèche lumineuse et balises."""
    b = MeshBuilder()
    b.box((0, .48, 0), (1.9, .16, 1.5), STRIPE)
    b.box((0, .70, .2), (1.2, .40, .9), CARBON, taper=(.9, .9))
    for sx in (1, -1):
        b.cylinder((sx * .95, .30, 0), .30, .18, "x", TIRE, 18, CHROME)
        b.tube([(sx * .55, .55, -.35), (sx * .55, 1.35, -.45)], .04, CHROME, 6)
    b.box((0, 1.95, -.45), (2.2, 1.25, .10), CARBON)
    b.box((0, 1.95, -.505), (2.28, 1.33, .04), MATTE)
    for x, y in [(-.75, 0), (-.5, .22), (-.5, -.22), (-.25, .44), (-.25, -.44), (-.5, 0), (-.25, 0), (0, 0), (.25, 0),
                 (.5, 0), (.75, 0)]:
        b.cylinder((x, 1.95 + y, -.55), .075, .06, "z", AMBER, 10)
    for i in range(6):
        x = -.95 + i * .38
        b.quad((x - .14, .42, -.76), (x + .06, .42, -.76), (x + .16, .62, -.76), (x - .04, .62, -.76), EMIT)
    for sx in (1, -1):
        b.cylinder((sx * 1.35, .42, -.3), .20, .84, "y", CONE, 14)
        b.cylinder((sx * 1.35, .92, -.3), .07, .12, "y", AMBER, 8)
    return b.build()


def debris() -> np.ndarray:
    rng = np.random.default_rng(4)
    b = MeshBuilder()
    for i in range(7):
        a, r = rng.random() * 6.28, rng.random() * .75
        b.box((math.cos(a) * r, .06 + rng.random() * .05, math.sin(a) * r),
              (.16 + rng.random() * .38, .04 + rng.random() * .08, .12 + rng.random() * .30),
              [CARBON, CHROME, STRIPE][i % 3], taper=(.7, .8), shift=(.05, -.03))
    b.torus((.25, .10, -.15), .27, .085, "y", TIRE, 20, 7)
    b.torus((-.45, .26, .25), .24, .08, "x", TIRE, 18, 7)
    b.tube([(-.7, .05, -.3), (-.2, .22, -.1), (.4, .08, .35)], .03, CHROME, 5)
    b.box((.05, .16, .3), (.3, .04, .05), EMIT)
    return b.build()


# -- pièces et bonus -----------------------------------------------------------------
def coin() -> np.ndarray:
    b = MeshBuilder()
    ang = [math.pi / 6 + math.pi / 3 * i for i in range(6)]
    out, inn = [(.42 * math.cos(a), .42 * math.sin(a)) for a in ang], [(.30 * math.cos(a), .30 * math.sin(a)) for a in ang]
    for i in range(6):
        j = (i + 1) % 6
        for z, s in ((.07, 1), (-.07, -1)):
            b.quad((*out[i], z * .55), (*out[j], z * .55), (*inn[j], z), (*inn[i], z), CHROME)
            b.quad((*inn[i], z), (*inn[j], z), (inn[j][0] * .9, inn[j][1] * .9, z * .4), (inn[i][0] * .9, inn[i][1] * .9, z * .4), CHROME)
        b.quad((*out[i], -.0385), (*out[j], -.0385), (*out[j], .0385), (*out[i], .0385), EMIT)
    for z in (.032, -.032):
        b.add([[(0, 0, z), (*inn[i], z), (*inn[(i + 1) % 6], z)] for i in range(6)], PAINT)
        zz = z * 1.9                                       # monogramme N
        b.quad((-.15, -.16, zz), (-.09, -.16, zz), (-.09, .16, zz), (-.15, .16, zz), EMIT)
        b.quad((.09, -.16, zz), (.15, -.16, zz), (.15, .16, zz), (.09, .16, zz), EMIT)
        b.quad((-.14, .16, zz), (-.06, .16, zz), (.14, -.16, zz), (.06, -.16, zz), EMIT)
    return b.build()


def _frame(b: MeshBuilder):
    """Capsule holographique commune aux bonus."""
    for y, r in ((.0, .62), (1.35, .34)):
        b.torus((0, y + .03, 0), r, .022, "y", ACCENT, 26, 5)
    for i in range(3):
        a = 2 * math.pi * i / 3
        b.tube([(math.cos(a) * .62, .03, math.sin(a) * .62), (math.cos(a + .4) * .50, .70, math.sin(a + .4) * .50),
                (math.cos(a + .8) * .34, 1.38, math.sin(a + .8) * .34)], .012, HOLO, 4)


def pickup(kind: str) -> np.ndarray:
    b = MeshBuilder()
    _frame(b)
    c = .72
    if kind == "nitro":
        bolt = [(.06, .40), (-.22, -.04), (-.02, -.04), (-.08, -.40), (.22, .08), (.02, .08)]
        pts = [(x, y + c) for x, y in bolt]
        for tri in ((0, 1, 2, 5), (5, 2, 3, 4)):
            b.extrude([pts[i] for i in tri], -.06, .06, EMIT)
    elif kind == "shield":
        o = [(0, -.38), (.28, -.10), (.28, .24), (0, .36), (-.28, .24), (-.28, -.10)]
        b.extrude([(x * .72, y * .72 + c) for x, y in o], -.04, .04, PAINT)
        ring = [(x, y + c, 0) for x, y in o]
        b.tube(ring, .045, EMIT, 6, closed=True)
    elif kind == "magnet":
        pts = [(.22 * math.cos(a), c - .06 - .22 * math.sin(a), 0) for a in np.linspace(0, math.pi, 12)]
        pts = [(.22, c + .16, 0)] + pts + [(-.22, c + .16, 0)]
        b.tube(pts, .085, PAINT, 8)
        for sx in (1, -1):
            b.cylinder((sx * .22, c + .24, 0), .088, .16, "y", EMIT, 12)
    elif kind == "repair":
        b.box((0, c, 0), (.18, .62, .14), EMIT)
        b.box((0, c, 0), (.62, .18, .13), EMIT)
        b.torus((0, c, 0), .42, .025, "z", CHROME, 24, 5)
    elif kind == "multi":
        pts = [((.40 if i % 2 == 0 else .17) * math.sin(i * math.pi / 5), c + (.40 if i % 2 == 0 else .17) * math.cos(i * math.pi / 5))
               for i in range(10)]
        for z in (.07, -.07):
            b.add([[(0, c, z * 1.6), (*pts[i], 0), (*pts[(i + 1) % 10], 0)] for i in range(10)], EMIT)
    else:                                                   # slow : sablier
        b.cylinder((0, c + .17, 0), .03, .32, "y", EMIT, 12, r2=.24)
        b.cylinder((0, c - .17, 0), .24, .32, "y", EMIT, 12, r2=.03)
        for y in (.35, -.35):
            b.cylinder((0, c + y, 0), .28, .05, "y", CHROME, 16)
    return b.build()


# -- décor urbain ------------------------------------------------------------------------
def building(kind: int) -> np.ndarray:
    """Volume unitaire (base 1 x 1, hauteur 1) mis à l'échelle par instance."""
    b = MeshBuilder()
    if kind == 0:
        b.box((0, .5, 0), (1, 1, 1), BUILDING)
    elif kind == 1:
        b.box((0, .33, 0), (1, .66, 1), BUILDING)
        b.box((0, .78, 0), (.74, .24, .74), BUILDING)
        b.box((0, .95, 0), (.42, .10, .42), BUILDING)
    elif kind == 2:
        b.box((-.22, .5, 0), (.52, 1.0, 1), BUILDING)
        b.box((.27, .38, 0), (.46, .76, .82), BUILDING)
    else:
        b.extrude([(-.5, 0), (.5, 0), (.5, .80), (-.5, 1.0)], -.5, .5, BUILDING)
    return b.build()


def antenna() -> np.ndarray:
    b = MeshBuilder()
    b.tube([(0, 0, 0), (0, 1, 0)], .02, CARBON, 5)
    b.box((0, 1.0, 0), (.08, .05, .08), EMIT)
    return b.build()


def sign_vertical() -> np.ndarray:
    """Enseigne 1 x 1 dans le plan XY, face au joueur (-z) et au dos."""
    b = MeshBuilder()
    b.quad((-.5, 0, -.5), (.5, 0, -.5), (.5, 1, -.5), (-.5, 1, -.5), SIGN)
    b.quad((.5, 0, .5), (-.5, 0, .5), (-.5, 1, .5), (.5, 1, .5), SIGN)
    b.box((0, .5, 0), (1.04, 1.03, .9), CARBON)
    return b.build()


def billboard() -> np.ndarray:
    b = MeshBuilder()
    for x in (-2.4, 2.4):
        b.tube([(x, 0, .2), (x, 7, .2)], .16, CARBON, 6)
    b.box((0, 7.2, .15), (9.0, 4.6, .35), CARBON)
    b.quad((-4.3, 5.1, -.06), (4.3, 5.1, -.06), (4.3, 9.3, -.06), (-4.3, 9.3, -.06), SIGN)
    b.box((0, 4.85, -.25), (8.6, .08, .5), ACCENT)
    return b.build()


def lamp_post() -> np.ndarray:
    """Lampadaire incurvé, côté gauche (bras vers +x)."""
    b = MeshBuilder()
    b.cylinder((0, .3, 0), .20, .6, "y", CARBON, 10)
    pts = [(0, .4, 0), (0, 5.6, 0), (.15, 6.8, 0), (.7, 7.6, 0), (1.7, 7.95, 0), (3.0, 8.0, 0)]
    b.tube(pts, .085, CARBON, 7)
    b.box((2.7, 7.93, 0), (1.5, .07, .28), EMIT)
    b.box((2.7, 8.0, 0), (1.6, .08, .36), CARBON)
    b.tube([(0.11, .7, 0), (0.11, 5.4, 0)], .022, ACCENT, 4)
    return b.build()


def gantry() -> np.ndarray:
    """Portique au-dessus de la route avec panneaux holographiques."""
    b = MeshBuilder()
    for sx in (1, -1):
        b.box((sx * 9.6, 3.6, 0), (.5, 7.2, .7), CARBON)
        b.box((sx * 9.32, 3.6, -.2), (.05, 6.6, .08), ACCENT)
    b.box((0, 7.4, 0), (19.8, .7, .8), CARBON)
    b.box((0, 7.02, -.3), (19.2, .06, .08), ACCENT)
    for i in range(12):
        x = -8.8 + i * 1.6
        b.tube([(x, 7.75, 0), (x + .8, 8.35, 0), (x + 1.6, 7.75, 0)], .05, CARBON, 4)
    for x in (-5.4, -1.8, 1.8, 5.4):
        b.box((x, 6.35, -.1), (2.5, 1.15, .18), CARBON)
        b.quad((x - 1.15, 5.85, -.21), (x + 1.15, 5.85, -.21), (x + 1.15, 6.85, -.21), (x - 1.15, 6.85, -.21), SIGN)
    return b.build()


def portal() -> np.ndarray:
    """Arche de changement d'univers."""
    b = MeshBuilder()
    for r, t, m in ((9.8, .30, CARBON), (9.45, .10, EMIT), (10.2, .07, ACCENT)):
        pts = [(r * math.cos(a), max(r * math.sin(a) * .92, 0), 0) for a in np.linspace(0, math.pi, 33)]
        b.tube(pts, t, m, 7)
    for i in range(9):
        a = math.pi * (i + .5) / 9
        b.box((9.8 * math.cos(a), 9.8 * math.sin(a) * .92, -.2), (.7, .5, .5), CHROME)
    return b.build()


def torii() -> np.ndarray:
    b = MeshBuilder()
    for sx in (1, -1):
        b.cylinder((sx * 10.2, 4.0, 0), .46, 8.0, "y", PAINT, 14, r2=.38)
        b.cylinder((sx * 10.2, .35, 0), .62, .7, "y", CARBON, 14)
        b.tube([(sx * 10.2, .9, -.5), (sx * 10.2, 7.6, -.45)], .03, ACCENT, 4)
    b.box((0, 6.9, 0), (21.6, .55, .5), PAINT)
    top = [[(x, 8.2 + .035 * (abs(x) / 11.8) ** 2 * 24 + dy, dz) for dy, dz in ((0, -.45), (.75, -.5), (.75, .5), (0, .45), (0, -.45))]
           for x in np.linspace(-11.8, 11.8, 15)]
    b.grid(np.array(top), PAINT, crease=40)
    b.tube([(x, 8.15 + .035 * (abs(x) / 11.8) ** 2 * 24, -.5) for x in np.linspace(-11.6, 11.6, 15)], .045, ACCENT, 4)
    b.box((0, 7.55, -.1), (1.6, 1.1, .25), CARBON)
    b.quad((-.7, 7.1, -.24), (.7, 7.1, -.24), (.7, 8.0, -.24), (-.7, 8.0, -.24), SIGN)
    return b.build()


def lantern() -> np.ndarray:
    b = MeshBuilder()
    ang = np.linspace(0, 2 * math.pi, 13)
    prof = [(.16, -.48), (.36, -.30), (.44, 0), (.36, .30), (.16, .48)]
    b.grid(np.array([[(r * math.cos(a), y, r * math.sin(a)) for r, y in prof] for a in ang]), EMIT, crease=80)
    for y in (.5, -.5):
        b.cylinder((0, y, 0), .18, .08, "y", CARBON, 10)
    return b.build()


def wires() -> np.ndarray:
    """Câbles et poteau pour les rues de Tokyo."""
    b = MeshBuilder()
    b.cylinder((0, 4.5, 0), .16, 9, "y", CONCRETE, 8)
    for y in (8.4, 7.6):
        b.box((0, y, 0), (2.4, .12, .12), CARBON)
        for x in (-1.0, .0, 1.0):
            b.tube([(x, y - 1.1 * math.sin(math.pi * t) + .1, t * 40) for t in np.linspace(0, 1, 7)], .02, MATTE, 3)
    b.box((.35, 6.4, 0), (.5, .8, .5), CARBON)
    return b.build()


# -- nature ---------------------------------------------------------------------------------
def cactus(kind: int) -> np.ndarray:
    b = MeshBuilder()

    def limb(pts, r):
        b.tube(pts, r, FOLIAGE, 9)
        b.merge(_dome(pts[-1], r))

    limb([(0, 0, 0), (0, 3.6, 0)], .34)
    limb([(0, 1.5, 0), (.75, 1.55, 0), (.95, 1.9, 0), (.95, 2.9, 0)], .22)
    if kind:
        limb([(0, 2.0, 0), (-.65, 2.05, .1), (-.82, 2.4, .1), (-.82, 3.2, .1)], .20)
    return b.build()


def _dome(p, r):
    b = MeshBuilder()
    th, ph = np.linspace(0, math.pi / 2, 4), np.linspace(0, 2 * math.pi, 10)
    b.grid(np.array([[(p[0] + r * math.cos(t) * math.cos(a), p[1] + r * math.sin(t), p[2] + r * math.cos(t) * math.sin(a))
                      for a in ph] for t in th]), FOLIAGE, crease=80)
    return b


def pine(kind: int) -> np.ndarray:
    b = MeshBuilder()
    b.cylinder((0, .8, 0), .20, 1.6, "y", TRUNK, 7, r2=.15)
    rng = np.random.default_rng(kind + 2)
    n = 5
    for i in range(n):
        y, r, h = 1.0 + i * 1.15, 1.75 - i * .30, 2.0 - i * .12
        ang = np.linspace(0, 2 * math.pi, 12)
        rr = r * (1 + .16 * np.cos(ang * 5 + rng.random() * 6))
        base = np.array([(a_r * math.cos(a), y - .12 * (k % 2), a_r * math.sin(a)) for k, (a, a_r) in enumerate(zip(ang, rr))])
        base[-1] = base[0]
        tip = np.array([0, y + h, 0])
        b.add([[base[k], base[k + 1], tip] for k in range(11)], FOLIAGE, crease=30)
        b.add([[base[k + 1], base[k], (0, y + .25, 0)] for k in range(11)], FOLIAGE)
    return b.build()


def rock(kind: int) -> np.ndarray:
    return _rock(kind * 7 + 1, squash=.75 + .2 * (kind % 2)).build()


def mesa() -> np.ndarray:
    return _rock(5, detail=12, squash=1.0, flat=True).build()


def power_pole() -> np.ndarray:
    b = MeshBuilder()
    b.cylinder((0, 4.2, 0), .17, 8.4, "y", WOOD, 8, r2=.12)
    for y in (7.8, 7.0):
        b.box((0, y, 0), (2.6, .16, .16), WOOD)
        for x in (-1.1, -.4, .4, 1.1):
            b.cylinder((x, y + .16, 0), .05, .16, "y", CHROME, 6)
    for x in (-1.1, 1.1):
        b.tube([(x, 8.0 - 1.3 * math.sin(math.pi * t), t * 50) for t in np.linspace(0, 1, 8)], .022, MATTE, 3)
    return b.build()


def marker_post() -> np.ndarray:
    b = MeshBuilder()
    b.box((0, .5, 0), (.14, 1.0, .06), CHROME, taper=(.8, 1))
    b.box((0, .80, -.035), (.10, .18, .02), EMIT)
    return b.build()


def ring() -> np.ndarray:
    """Anneau énergétique de tunnel."""
    b = MeshBuilder()

    def sup(a, rx, ry):
        c, s = math.cos(a), math.sin(a)
        return (math.copysign(abs(c) ** .62, c) * rx, s ** .62 * ry if s > 0 else 0.0, 0)

    ang = np.linspace(0, math.pi, 33)
    b.tube([sup(a, 10.2, 7.25) for a in ang], .22, CARBON, 6)
    b.tube([sup(a, 9.92, 7.0) for a in ang], .06, EMIT, 5)
    return b.build()


def drone() -> np.ndarray:
    b = MeshBuilder()
    b.box((0, 0, 0), (.9, .18, .6), CARBON, taper=(.6, .6))
    for sx in (1, -1):
        for sz in (1, -1):
            b.torus((sx * .75, .05, sz * .55), .32, .03, "y", ACCENT, 16, 5)
            b.tube([(0, 0, 0), (sx * .75, .05, sz * .55)], .035, CARBON, 4)
    b.box((0, -.08, -.28), (.3, .08, .06), EMIT)
    return b.build()


BUILDERS = {
    "barrier": barrier, "cone": cone, "roadworks": roadworks, "debris": debris, "coin": coin,
    **{f"pk_{k}": (lambda k=k: pickup(k)) for k in ("nitro", "shield", "magnet", "repair", "multi", "slow")},
    **{f"bld{i}": (lambda i=i: building(i)) for i in range(4)},
    "antenna": antenna, "sign": sign_vertical, "billboard": billboard, "lamp": lamp_post, "gantry": gantry,
    "portal": portal, "torii": torii, "lantern": lantern, "wires": wires,
    "cactus0": lambda: cactus(0), "cactus1": lambda: cactus(1), "pine0": lambda: pine(0), "pine1": lambda: pine(1),
    "rock0": lambda: rock(0), "rock1": lambda: rock(1), "mesa": mesa, "pole": power_pole, "marker": marker_post,
    "ring": ring, "drone": drone,
}
