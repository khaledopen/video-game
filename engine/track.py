"""Tracé infini : courbure et relief calculés analytiquement le long de la distance."""
from __future__ import annotations

import math

import numpy as np

LANES = 4
LANE_W = 3.6
ROAD_HALF = 8.6                # bord de la chaussée (glissière)
DRIVE_HALF = 7.9               # limite latérale du centre d'un véhicule au contact
Z_BACK, Z_RANGE, SAMPLES = 30.0, 760.0, 320
WRAP = 19200.0


def lane_x(lane: float) -> float:
    return (lane - (LANES - 1) / 2) * LANE_W


def nearest_lane(x: float) -> int:
    return max(0, min(LANES - 1, round(x / LANE_W + (LANES - 1) / 2)))


# (courbure maximale, relief, longueur caractéristique) par environnement
PROFILE = {0: (.0016, .7, 1.0), 1: (.0011, 1.0, 1.3), 2: (.0017, .5, .9), 3: (.0024, 1.5, .85), 4: (.0019, .8, .9),
           5: (0.0, 0.0, 1.0)}


class Track:
    def __init__(self, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.phase = rng.random(6) * 2 * math.pi
        self.z = np.linspace(-Z_BACK, Z_RANGE - Z_BACK, SAMPLES)
        self.dz = self.z[1] - self.z[0]
        self.i0 = Z_BACK / self.dz
        self.amp, self.relief, self.scale = PROFILE[0]
        self._target = PROFILE[0]
        self.table = np.zeros((SAMPLES, 2), "f4")

    def set_environment(self, index: int, instant: bool = False) -> None:
        self._target = PROFILE[index]
        if instant:
            self.amp, self.relief, self.scale = self._target

    def update(self, dt: float) -> None:
        k = 1 - math.exp(-.6 * dt)
        self.amp += (self._target[0] - self.amp) * k
        self.relief += (self._target[1] - self.relief) * k

    def curvature(self, s):
        p = self.phase
        v = .62 * np.sin(s / 205. + p[0]) + .48 * np.sin(s / 473. + p[1]) + .18 * np.sin(s / 93. + p[2])
        v = np.sign(v) * np.maximum(np.abs(v) - .16, 0) * 1.25
        ramp = np.clip((s - 60.) / 260., 0, 1)            # départ en ligne droite
        return self.amp * v * ramp

    def height(self, s):
        p = self.phase
        ramp = np.clip((s - 40.) / 300., 0, 1)
        return self.relief * ramp * (5.0 * np.sin(s / 160. + p[3]) + 2.2 * np.sin(s / 71. + p[4]) + 7. * np.sin(s / 390. + p[5]))

    def slope(self, s: float) -> float:
        return float((self.height(np.float64(s + 2.)) - self.height(np.float64(s - 2.))) / 4.)

    def bend_table(self, s: float) -> np.ndarray:
        """Décalages (x, y) de la route pour chaque profondeur, tangents au joueur."""
        z = self.z
        k = self.curvature(s + z)
        head = np.cumsum((k[1:] + k[:-1]) * .5) * self.dz
        head = np.concatenate([[0.], head])
        head -= np.interp(0., z, head)
        x = np.cumsum((head[1:] + head[:-1]) * .5) * self.dz
        x = np.concatenate([[0.], x])
        x -= np.interp(0., z, x)
        y = self.height(s + z) - float(self.height(np.float64(s))) - self.slope(s) * z
        self.table[:, 0], self.table[:, 1] = x, y
        return self.table

    def offset(self, z: float) -> tuple[float, float]:
        f = (z + Z_BACK) / self.dz
        i = int(max(0, min(SAMPLES - 2, f)))
        t = f - i
        a, b = self.table[i], self.table[i + 1]
        return float(a[0] + (b[0] - a[0]) * t), float(a[1] + (b[1] - a[1]) * t)
