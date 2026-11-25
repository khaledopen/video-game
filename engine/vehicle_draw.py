"""Mise en file des véhicules (carrosserie, roues, décalcomanies lumineuses)."""
from __future__ import annotations

import math

from config.palette import linear, rgb
from engine.renderer import Renderer, row


class Look:
    """Apparence d'une voiture du joueur."""

    def __init__(self, vid: str, paint: str, light: str, rim: int = 0):
        self.vid, self.rim = vid, rim
        self.paint = linear(rgb(paint))
        self.light = linear(rgb(light))


def _wheels(r: Renderer, rim: int, wheels, pos, yaw, spin, steer, radius, light):
    c, s = math.cos(yaw), math.sin(yaw)
    rows = []
    for w in wheels:
        x, y, z = w[0], w[1], w[2]
        turn = steer if len(w) > 3 and w[3] else 0.0
        side = 1 if x > 0 else -1
        rows.append(row((pos[0] + c * x + s * z, pos[1] + y, pos[2] - s * x + c * z), yaw + turn, spin, 0.,
                        (side * radius, radius, radius), (1, 1, 1), light))
    r.queue(f"wheel:{rim}", rows)


def draw_player(r: Renderer, look: Look, pos, yaw=0., pitch=0., roll=0., spin=0., steer=0., brake=0., flash=0., lights=1.,
                decals: list | None = None, glow: float = 1.0):
    m = r.car_model(look.vid)
    r.queue(f"car:{look.vid}", [row(pos, yaw, pitch, roll, c1=look.paint, c2=look.light, brake=brake, flash=flash, lights=lights)])
    _wheels(r, look.rim, m.wheels, pos, yaw, spin, steer, .345, look.light)
    if decals is not None:
        shadow(decals, pos, yaw, m.W, m.L)
        decals.append([pos[0], pos[2], m.W * .95, m.L * .68, *(v * .30 * glow for v in look.light), 0, 1, yaw])


def shadow(decals: list, pos, yaw, w, length, strength=.72):
    decals.append([pos[0], pos[2], w * .66, length * .60, 0, 0, 0, strength, 0, yaw])


def draw_traffic(r: Renderer, kind: str, pos, yaw, roll, spin, paint, accent, brake, seed, decals, near: bool, glow: bool, flash=0.):
    m = r.traffic_model(kind)
    r.queue(f"trf:{kind}", [row(pos, yaw, 0., roll, c1=paint, c2=accent, brake=brake, flash=flash, seed=seed)])
    if near:
        rad = m.wheels[0][1]
        _wheels(r, int(seed * 3), m.wheels, pos, yaw, spin, 0., rad, accent)
    shadow(decals, pos, yaw, m.width, m.length)
    if glow:
        decals.append([pos[0], pos[2], m.width * .92, m.length * .60, *(v * .20 for v in accent), 0, 1, yaw])
