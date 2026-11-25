"""Décor infini et déterministe : chaque emplacement est recalculé à partir de son index."""
from __future__ import annotations

import math

import numpy as np

from config.environments import CITY, DESERT, MOUNTAIN, TOKYO, TUNNEL, Environment
from engine.mathx import hash01
from engine.renderer import INST, Renderer

NEON = np.array([[0, .80, 1.0], [.45, .16, 1.0], [1.0, .06, .22], [1.0, .12, .55], [.10, .35, 1.0], [.0, 1.0, .55]])


def _rows(n: int) -> np.ndarray:
    a = np.zeros((n, INST), "f4")
    a[:, 6:15] = 1.0
    a[:, 16] = 1.0
    return a


def _slots(s: float, step: float, back: float, far: float):
    i0, i1 = math.floor((s - back) / step), math.floor((s + far) / step)
    return np.arange(i0, i1 + 1)


class Scenery:
    def __init__(self, renderer: Renderer):
        self.r = renderer

    def queue(self, env: Environment, s: float, time: float) -> None:
        far = self.r.quality.far
        fn = {CITY: self._city, TOKYO: self._tokyo, DESERT: self._desert, MOUNTAIN: self._mountain, TUNNEL: self._tunnel}.get(env.index)
        if fn:
            fn(env, s, far, time)

    # -- outils ---------------------------------------------------------------------
    def _put(self, name, idx, step, s, x, y=0.0, sx=1.0, sy=1.0, sz=1.0, yaw=0.0, c1=None, c2=None, seed=0.0, jitter=0.0, mask=None):
        n = len(idx)
        a = _rows(n)
        a[:, 0] = x
        a[:, 1] = y
        a[:, 2] = idx * step - s + jitter
        a[:, 3] = yaw
        a[:, 6], a[:, 7], a[:, 8] = sx, sy, sz
        if c1 is not None:
            a[:, 9:12] = c1
        if c2 is not None:
            a[:, 12:15] = c2
        a[:, 18] = seed
        if mask is not None:
            a = a[mask]
        if len(a):
            self.r.queue(name, a)

    def _towers(self, s, far, step, near, depth_rows, hmin, hmax, salt, width):
        dens = self.r.quality.density
        for row_i in range(depth_rows):
            stp = step * (1 + .35 * row_i)
            idx = _slots(s, stp, 25, far)
            for side in (-1, 1):
                q = idx * 2 + (side > 0)
                h = [hash01(q, salt + row_i * 10 + k) for k in range(8)]
                w = width * (.7 + .6 * h[0]) * (1 + .4 * row_i)
                height = hmin + (hmax - hmin) * h[1] ** 2.1 * (1 + .55 * row_i)
                x = side * (near + row_i * 34 + w / 2 + h[2] * 8)
                kind = (h[3] * 4).astype(int)
                c1, c2 = NEON[(h[4] * 6).astype(int) % 6], NEON[(h[5] * 6).astype(int) % 6]
                keep = h[6] < (dens if row_i else 1.0)
                for k in range(4):
                    m = keep & (kind == k)
                    if m.any():
                        self._put(f"bld{k}", idx, stp, s, x, 0., w, height, stp * (.62 + .25 * h[7]), math.pi if side > 0 and k == 3 else 0., c1, c2, h[6], mask=m)
                tall = keep & (height > hmin + (hmax - hmin) * .45) & (h[7] > .5)
                if tall.any():
                    self._put("antenna", idx, stp, s, x, height * .98, 3., 14., 3., 0., np.array([1., .05, .1]), None, 0., mask=tall)

    # -- univers -----------------------------------------------------------------------
    def _city(self, env, s, far, t):
        self._towers(s, far, 24., 17., 3, 16., 92., 1., 15.)
        idx = _slots(s, 40., 20, min(far, 420))
        for side in (-1, 1):
            a_yaw = 0. if side < 0 else math.pi
            self._put("lamp", idx, 40., s, side * 9.6, yaw=a_yaw, c1=np.array(env.lamp) * 1.5, c2=env.edge if side < 0 else env.edge2)
        idx = _slots(s, 48., 20, min(far, 460))
        for side in (-1, 1):
            q = idx * 2 + (side > 0)
            h = [hash01(q, 50. + k) for k in range(5)]
            ch = 7 + 11 * h[0]
            self._put("sign", idx, 48., s, side * (13.2 + 2.2 * h[1]), 5 + 9 * h[2], 2.6 + 2.0 * h[3], ch, .5, 0.,
                      NEON[(h[3] * 6).astype(int)], NEON[(h[4] * 6).astype(int)], h[4], 18 * h[2], mask=h[1] < .78)
        idx = _slots(s, 210., 20, far)
        h = hash01(idx, 71.)
        self._put("billboard", idx, 210., s, np.where(h > .5, 17., -17.), 0, 1, 1, 1, np.where(h > .5, .28, -.28),
                  NEON[(h * 6).astype(int)], NEON[((h * 13) % 6).astype(int)], h, 60.)
        idx = _slots(s, 330., 20, far)
        h = hash01(idx, 81.)
        self._put("gantry", idx, 330., s, 0., c1=NEON[(h * 6).astype(int)], c2=np.array(env.edge), seed=h, jitter=150.)
        idx = _slots(s, 95., 10, min(far, 330))
        h, k = hash01(idx, 91.), hash01(idx, 92.)
        self._put("drone", idx, 95., s, np.sin(t * .5 + h * 20) * 11, 11 + 4 * k + np.sin(t * 1.3 + k * 9) * .6, 1.2, 1.2, 1.2,
                  c1=np.array([1., .1, .15]), c2=NEON[(h * 6).astype(int)], jitter=np.sin(t * .31 + k * 12) * 18)

    def _tokyo(self, env, s, far, t):
        self._towers(s, far, 19., 14.5, 2, 12., 54., 5., 12.)
        idx = _slots(s, 13., 20, min(far, 300))
        for side in (-1, 1):
            q = idx * 2 + (side > 0)
            h = [hash01(q, 130. + k) for k in range(6)]
            hgt = 4 + 9 * h[0]
            self._put("sign", idx, 13., s, side * (11.4 + 1.5 * h[1]), 3.2 + 10 * h[2] ** 1.4, 1.5 + 1.6 * h[3], hgt, .35, 0.,
                      NEON[(h[4] * 6).astype(int)], NEON[(h[5] * 6).astype(int)], h[4] * .9, 6 * h[2], mask=h[1] < .62 * self.r.quality.density + .1)
        idx = _slots(s, 40., 45, min(far, 320))
        self._put("wires", idx, 40., s, -10.2)
        self._put("lamp", idx, 40., s, 9.6, yaw=math.pi, c1=np.array(env.lamp) * 1.4, c2=env.edge)
        idx = _slots(s, 8., 10, min(far, 170))
        h = hash01(idx, 160.)
        hang = 5.4 + .25 * np.sin(t * 1.6 + h * 9)
        self._put("lantern", idx, 8., s, -9.5 + .3 * np.sin(t + h * 20), hang, .9, .9, .9, 0, np.array([1.0, .16, .06]) * .8, mask=h < .8)
        idx = _slots(s, 380., 20, far)
        self._put("torii", idx, 380., s, 0., c1=np.array([.55, .03, .03]), c2=np.array([1., .12, .12]), seed=.1, jitter=170.)
        h = hash01(idx, 171.)
        self._put("gantry", idx, 380., s, 0., c1=NEON[(h * 6).astype(int)], c2=np.array(env.edge2), seed=h, jitter=350.)

    def _desert(self, env, s, far, t):
        d = self.r.quality.density
        idx = _slots(s, 50., 55, min(far, 520))
        self._put("pole", idx, 50., s, 12.5)
        idx = _slots(s, 7., 10, min(far, 360))
        for side in (-1, 1):
            q = idx * 2 + (side > 0)
            h = [hash01(q, 200. + k) for k in range(6)]
            x = side * (11.5 + 70 * h[0] ** 1.8)
            sc = .55 + .95 * h[1]
            y = self._dune(x, idx * 7. + 4 * h[2])
            for k in (0, 1):
                self._put(f"cactus{k}", idx, 7., s, x, y - .2, sc, sc, sc, h[3] * 6.28, np.array([.10, .16, .055]), None, h[4], 4 * h[2],
                          (h[5] < .16 * d) & ((h[4] > .5) == bool(k)))
                rs = .4 + 1.5 * h[3] ** 2
                self._put(f"rock{k}", idx, 7., s, x, y - .15, rs * 1.2, rs, rs, h[1] * 6.28, np.array([.42, .20, .11]), None, h[2], 4 * h[2],
                          (h[5] > .16) & (h[5] < .16 + .30 * d) & ((h[4] > .5) == bool(k)))
        idx = _slots(s, 85., 40, far)
        for side in (-1, 1):
            q = idx * 2 + (side > 0)
            h = [hash01(q, 240. + k) for k in range(5)]
            w = 14 + 26 * h[0]
            self._put("mesa", idx, 85., s, side * (75 + 110 * h[1]), -2., w, 16 + 34 * h[2], w * .9, h[3] * 6.28,
                      np.array([.50, .21, .11]), None, h[4], 0., h[3] < .85)
        idx = _slots(s, 420., 20, far)
        h = hash01(idx, 260.)
        self._put("billboard", idx, 420., s, np.where(h > .5, 16., -16.), -.3, .9, .9, .9, np.where(h > .5, .3, -.3),
                  np.array([1., .35, .08]), np.array([1., .08, .3]), h, 120.)
        self._markers(s, far, np.array([1., .4, .1]))

    @staticmethod
    def _dune(x, s):
        return np.clip((np.abs(x) - 12) / 60, 0, 1) * 1.2

    def _markers(self, s, far, col):
        idx = _slots(s, 25., 10, min(far, 260))
        for side in (-1, 1):
            self._put("marker", idx, 25., s, side * 9.35, c1=col)

    def _mountain(self, env, s, far, t):
        d = self.r.quality.density
        idx = _slots(s, 4.2, 10, min(far, 430))
        for side in (-1, 1):
            q = idx * 2 + (side > 0)
            h = [hash01(q, 300. + k) for k in range(6)]
            ax = 13.6 + (62 if side < 0 else 34) * h[0] ** 1.3
            x = side * ax
            if side < 0:
                u = np.clip((ax - 11.2) / 88, 0, 1)
                y = np.clip((ax - 9.2) / 9, 0, 1) * 3.2 + (u * u * (3 - 2 * u)) ** 1.1 * 52
            else:
                u = np.clip((ax - 10.2) / 29, 0, 1)
                y = -(u * u * (3 - 2 * u)) * 12.5
            sc = .9 + 1.1 * h[1]
            tint = np.stack([.030 + .030 * h[2], .075 + .05 * h[2], .038 + .02 * h[3]], 1)
            for k in (0, 1):
                self._put(f"pine{k}", idx, 4.2, s, x, y - .5, sc, sc * (.9 + .4 * h[3]), sc, h[4] * 6.28, tint, None, h[2], 3 * h[5],
                          (h[5] < .72 * d) & ((h[4] > .5) == bool(k)))
                rs = .5 + 1.9 * h[3] ** 2
                self._put(f"rock{k}", idx, 4.2, s, x * .96, y - .4, rs * 1.2, rs, rs, h[1] * 6.28, np.array([.20, .20, .205]), None, h[2], 2 * h[5],
                          (h[5] > .86) & ((h[4] > .5) == bool(k)))
        self._markers(s, far, np.array([.9, .95, 1.]))
        idx = _slots(s, 520., 20, far)
        self._put("gantry", idx, 520., s, 0., c1=np.array([.1, .6, 1.]), c2=np.array([.4, .8, 1.]), seed=.6, jitter=240.)

    def _tunnel(self, env, s, far, t):
        idx = _slots(s, 60., 20, min(far, 480))
        h = hash01(idx, 400.)
        self._put("ring", idx, 60., s, 0., c1=np.where((idx % 2 == 0)[:, None], np.array(env.edge), np.array(env.edge2)))
        idx = _slots(s, 180., 20, far)
        h = hash01(idx, 410.)
        self._put("gantry", idx, 180., s, 0., -.9, .98, .92, 1., c1=NEON[(h * 6).astype(int)], c2=np.array(env.edge2), seed=h, jitter=90.)
