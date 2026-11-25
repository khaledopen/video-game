"""Palette officielle de NEON DRIVE (valeurs sRGB 0..1)."""
from __future__ import annotations


def hexc(code: str, a: float = 1.0) -> tuple[float, float, float, float]:
    code = code.lstrip("#")
    return (int(code[0:2], 16) / 255, int(code[2:4], 16) / 255, int(code[4:6], 16) / 255, a)


def rgb(code: str) -> tuple[float, float, float]:
    return hexc(code)[:3]


def alpha(c, a: float):
    return (c[0], c[1], c[2], a)


def mix(a, b, t: float):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def linear(c) -> tuple[float, float, float]:
    """sRGB vers linéaire (couleurs envoyées au rendu 3D HDR)."""
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c[:3])


BLACK = hexc("#05070D")
NIGHT = hexc("#0B1120")
CYAN = hexc("#00E5FF")
VIOLET = hexc("#8B5CF6")
RED = hexc("#FF3355")
WHITE = hexc("#FFFFFF")
CLEAR = (0.0, 0.0, 0.0, 0.0)
# Nuances dérivées pour l'interface
MUTED = hexc("#8FA3C4")
FAINT = hexc("#52627F")
GOLD = hexc("#FFC84A")
GREEN = hexc("#2CF5A0")
