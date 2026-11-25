"""Accès à l'atlas d'icônes (assets/icons)."""
from __future__ import annotations

import json

from config.paths import ICONS

_meta: dict = {}


def load(canvas) -> None:
    global _meta
    _meta = json.loads((ICONS / "icons.json").read_text())
    canvas.load_image("icons", path=ICONS / "icons.png")


def draw(c, name: str, x: float, y: float, size: float, color, rot: float = 0.0) -> None:
    uv = _meta.get(name)
    if uv:
        c.draw_image("icons", x - size / 2, y - size / 2, size, size, color, uv=uv, rot=rot)
