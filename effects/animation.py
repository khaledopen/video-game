"""Animations : courbes d'accélération, ressorts, secousses de caméra, ralenti."""
from __future__ import annotations

import math

from engine.mathx import clamp, damp


def ease_out(t):
    return 1 - (1 - clamp(t)) ** 3


def ease_in(t):
    return clamp(t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 4 * t**3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_back(t):
    t = clamp(t) - 1
    return 1 + 2.4 * t**3 + 1.4 * t**2


def stagger(t, index, delay=.06, dur=.45):
    """Progression décalée pour l'apparition d'une liste."""
    return ease_out((t - index * delay) / dur)


class Spring:
    """Valeur élastique (survols, compteurs)."""

    def __init__(self, value=0.0, stiffness=260.0, damping=22.0):
        self.v, self.t, self.d = value, value, 0.0
        self.k, self.c = stiffness, damping

    def update(self, dt):
        dt = min(dt, 1 / 30)
        for _ in range(2):
            self.d += ((self.t - self.v) * self.k - self.d * self.c) * dt / 2
            self.v += self.d * dt / 2
        return self.v


class Counter:
    """Compteur qui rattrape sa cible en douceur."""

    def __init__(self, value=0.0, rate=9.0):
        self.v, self.rate = value, rate

    def update(self, target, dt):
        self.v = damp(self.v, target, self.rate, dt)
        if abs(self.v - target) < .6:
            self.v = target
        return self.v


class CameraShake:
    """Secousse à bruit continu ; l'amplitude décroît avec le carré du traumatisme."""

    def __init__(self):
        self.trauma = 0.0
        self.t = 0.0

    def add(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt):
        self.t += dt
        self.trauma = max(0.0, self.trauma - dt * 1.5)

    def sample(self, speed: float = 0.0):
        """(dx, dy, roulis) : secousse d'impact + vibration légère liée à la vitesse."""
        a = self.trauma**2
        t = self.t
        n = lambda f, p: math.sin(t * f + p) * .6 + math.sin(t * f * 1.73 + p * 2.1) * .4
        v = speed**3
        return (a * .55 * n(41, 1) + v * .010 * n(63, 2), a * .42 * n(37, 4) + v * .012 * n(71, 5), a * .045 * n(29, 8) + v * .0012 * n(53, 3))


class TimeWarp:
    """Ralenti cinématographique avec retour progressif."""

    def __init__(self):
        self.scale, self.hold, self.target = 1.0, 0.0, 1.0

    def trigger(self, scale, duration):
        if scale <= self.target or self.hold <= 0:
            self.target, self.hold = scale, duration

    def update(self, dt):
        self.hold -= dt
        if self.hold <= 0:
            self.target = 1.0
        self.scale = damp(self.scale, self.target, 16 if self.target < self.scale else 4.5, dt)
        return self.scale
