"""Obstacles, pièces et bonus posés sur la route."""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.track import LANES, lane_x

# type : (demi-largeur, demi-longueur, solide, dégâts)
SPECS = {
    "barrier": (1.60, .38, True, 30.0),
    "cone": (.24, .24, False, 4.0),
    "roadworks": (1.55, .85, True, 32.0),
    "puddle": (1.35, 2.6, False, 0.0),
    "debris": (.85, .70, False, 11.0),
}


@dataclass
class Obstacle:
    kind: str
    s: float
    x: float
    half_w: float
    half_l: float
    solid: bool
    damage: float
    lanes: set = field(default_factory=set)
    seed: float = 0.0
    dead: bool = False          # plus de collision
    passed: bool = False
    touched: bool = False
    # cône ou débris projeté
    fly: tuple | None = None
    y: float = 0.0
    rot: float = 0.0


def make_obstacle(kind: str, s: float, x: float, seed: float = 0.0) -> Obstacle:
    hw, hl, solid, dmg = SPECS[kind]
    lanes = {l for l in range(LANES) if abs(lane_x(l) - x) < hw + .35} if solid else set()
    return Obstacle(kind, s, x, hw, hl, solid, dmg, lanes, seed)


@dataclass
class Coin:
    s: float
    x: float
    y: float = .78
    value: int = 1
    phase: float = 0.0
    taken: bool = False


@dataclass
class Pickup:
    kind: str
    s: float
    x: float
    phase: float = 0.0
    taken: bool = False


PICKUP_KINDS = ("nitro", "shield", "magnet", "repair", "multi", "slow")
PICKUP_COLORS = {"nitro": "#00E5FF", "shield": "#4AA8FF", "magnet": "#FF3355", "repair": "#2CF5A0", "multi": "#FFC84A", "slow": "#8B5CF6"}
PICKUP_NAMES = {"nitro": "NITRO", "shield": "BOUCLIER", "magnet": "AIMANT", "repair": "RÉPARATION", "multi": "SCORE ×2", "slow": "RALENTI TRAFIC"}
