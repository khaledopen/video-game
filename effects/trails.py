"""Traînées lumineuses : rubans construits à partir de l'historique des feux."""
from __future__ import annotations

import colorsys
from collections import deque

import numpy as np


class Trail:
    def __init__(self, length: float = 15.0, step: float = .45):
        self.length, self.step = length, step
        self.points: deque = deque(maxlen=64)       # (s, x, y)

    def clear(self):
        self.points.clear()

    def push(self, s, x, y):
        if not self.points or s - self.points[-1][0] >= self.step:
            self.points.append((s, x, y))
        while self.points and s - self.points[0][0] > self.length:
            self.points.popleft()

    def ribbon(self, head, s0, color, width, style=0, time=0., power=1.0):
        """Bande de triangles (x, y, z, r, g, b, a, u). `head` = point courant."""
        pts = list(self.points) + [head]
        n = len(pts)
        if n < 3:
            return None
        p = np.array(pts)
        t = np.clip(1 - (p[-1, 0] - p[:, 0]) / self.length, 0, 1)
        a = t ** 1.6 * power
        col = np.tile(np.asarray(color, float), (n, 1))
        if style == 2:                         # Pulsation
            a = a * (.45 + .75 * (np.sin(p[:, 0] * 1.4 - time * 18) * .5 + .5))
        elif style == 3:                       # Arc-en-ciel
            col = np.array([colorsys.hsv_to_rgb(((1 - v) * .75 + time * .35) % 1, .85, 1.0) for v in t]) ** 2.2
        w = width * (.35 + .65 * t)
        out = np.zeros((2 * n, 8), "f4")
        for k, side in ((0, -1), (1, 1)):
            out[k::2, 0] = p[:, 1] + side * w
            out[k::2, 1] = p[:, 2]
            out[k::2, 2] = p[:, 0] - s0
            out[k::2, 3:6] = col
            out[k::2, 6] = a
            out[k::2, 7] = side
        return out
