"""Système de particules vectorisé (tableaux NumPy, aucune allocation par particule)."""
from __future__ import annotations

import numpy as np

GLOW, SMOKE, SPARK, RING, STAR = range(5)


class Particles:
    """Positions dans le monde : x, y et distance absolue s."""

    def __init__(self, capacity: int = 1500, seed: int = 0):
        self.n = capacity
        self.rng = np.random.default_rng(seed)
        self.pos = np.zeros((capacity, 3))
        self.vel = np.zeros((capacity, 3))
        self.col = np.zeros((capacity, 3))
        self.alpha = np.zeros(capacity)
        self.life = np.zeros(capacity)
        self.max_life = np.ones(capacity)
        self.size = np.zeros((capacity, 2))      # début, fin
        self.kind = np.zeros(capacity)
        self.gravity = np.zeros(capacity)
        self.drag = np.zeros(capacity)
        self.stretch = np.zeros(capacity)
        self.next = 0
        self.budget = 1.0

    @property
    def count(self) -> int:
        return int((self.life > 0).sum())

    def clear(self):
        self.life[:] = 0

    def emit(self, n, pos, vel=(0, 0, 0), spread=(0, 0, 0), jitter=(0, 0, 0), color=(1, 1, 1), color2=None, life=(.3, .6), size=(.1, .02),
             kind=GLOW, gravity=0., drag=0., alpha=1., stretch=0.):
        n = int(n * self.budget + self.rng.random())
        if n <= 0:
            return
        n = min(n, self.n)
        idx = (self.next + np.arange(n)) % self.n
        self.next = (self.next + n) % self.n
        r = self.rng
        self.pos[idx] = np.asarray(pos) + (r.random((n, 3)) - .5) * 2 * np.asarray(jitter)
        self.vel[idx] = np.asarray(vel) + (r.random((n, 3)) - .5) * 2 * np.asarray(spread)
        c = np.asarray(color, float)
        if color2 is not None:
            t = r.random((n, 1))
            c = c * (1 - t) + np.asarray(color2, float) * t
        self.col[idx] = c
        lf = life[0] + (life[1] - life[0]) * r.random(n)
        self.life[idx] = self.max_life[idx] = lf
        k = .7 + .6 * r.random(n)
        self.size[idx, 0], self.size[idx, 1] = size[0] * k, size[1] * k
        self.kind[idx], self.gravity[idx], self.drag[idx] = kind, gravity, drag
        self.alpha[idx], self.stretch[idx] = alpha, stretch

    def update(self, dt: float):
        m = self.life > 0
        if not m.any():
            return
        self.life[m] -= dt
        self.vel[m, 1] -= self.gravity[m] * dt
        self.vel[m] *= np.exp(-self.drag[m] * dt)[:, None]
        self.pos[m] += self.vel[m] * dt
        low = m & (self.pos[:, 1] < .03) & (self.gravity > 0)
        self.pos[low, 1] = .03
        self.vel[low, 1] *= -.35

    def instances(self, s0: float, rel_speed: float = 0.0):
        """Retourne (additives, fumées) prêtes pour le GPU."""
        m = self.life > 0
        if not m.any():
            return None, None
        t = 1 - self.life[m] / self.max_life[m]
        out = np.zeros((len(t), 12), "f4")
        out[:, 0:2] = self.pos[m, :2]
        out[:, 2] = self.pos[m, 2] - s0
        out[:, 3] = self.size[m, 0] + (self.size[m, 1] - self.size[m, 0]) * t
        out[:, 4:7] = self.col[m]
        fade = np.minimum(1, (1 - t) * 1.8) * np.minimum(1, t * 12 + .3)
        out[:, 7] = self.alpha[m] * fade
        v = self.vel[m].copy()
        v[:, 2] -= rel_speed
        out[:, 8:11] = v * self.stretch[m][:, None]
        out[:, 11] = self.kind[m]
        near = (out[:, 2] > -9) & (out[:, 2] < 260)
        out = out[near]
        smoke = out[:, 11] == SMOKE
        return out[~smoke], out[smoke]
