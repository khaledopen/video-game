"""Détection des collisions : boîtes orientées (théorème des axes séparateurs)."""
from __future__ import annotations

import math


def corners(x, s, hw, hl, yaw):
    c, n = math.cos(yaw), math.sin(yaw)
    return [(x + c * a + n * b, s - n * a + c * b) for a, b in ((-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl))]


def obb_overlap(ax, as_, ahw, ahl, ayaw, bx, bs, bhw, bhl, byaw):
    """Retourne (profondeur, normale x, normale s) de A vers l'extérieur de B, ou None."""
    dx, ds = ax - bx, as_ - bs
    reach = math.hypot(ahw, ahl) + math.hypot(bhw, bhl)
    if dx * dx + ds * ds > reach * reach:
        return None
    best = None
    for yaw in (ayaw, byaw):
        c, n = math.cos(yaw), math.sin(yaw)
        for ux, us in ((c, -n), (n, c)):
            ca, na, cb, nb = math.cos(ayaw), math.sin(ayaw), math.cos(byaw), math.sin(byaw)
            ra = ahw * abs(ca * ux - na * us) + ahl * abs(na * ux + ca * us)
            rb = bhw * abs(cb * ux - nb * us) + bhl * abs(nb * ux + cb * us)
            d = dx * ux + ds * us
            pen = ra + rb - abs(d)
            if pen <= 0:
                return None
            if best is None or pen < best[0]:
                sg = 1.0 if d >= 0 else -1.0
                best = (pen, ux * sg, us * sg)
    return best


def circle_hit(ax, as_, hw, hl, px, ps, r) -> bool:
    """Cercle (pièce, bonus) contre rectangle aligné."""
    dx, ds = max(0.0, abs(px - ax) - hw), max(0.0, abs(ps - as_) - hl)
    return dx * dx + ds * ds < r * r
