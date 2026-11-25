"""Véhicules du joueur : caractéristiques, forme et options de personnalisation."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VehicleSpec:
    id: str
    name: str
    tagline: str
    price: int
    top_speed: float      # km/h
    accel: float          # 0..10
    handling: float       # 0..10
    armor: float          # 0..10
    nitro: float          # 0..10
    paint: str
    accent: str
    engine: str           # timbre moteur : v8, turbo, electric
    shape: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def top_ms(self) -> float:
        return self.top_speed / 3.6


# `shape` décrit la carrosserie générée par engine.models.cars
VEHICLES: tuple[VehicleSpec, ...] = (
    VehicleSpec("neon_gt", "NEON GT", "La lumière de départ", 0, 255, 5.0, 6.0, 5.5, 5.0,
                "#0FB5D6", "#00E5FF", "turbo",
                dict(L=4.50, W=1.94, H=1.24, nose=0.50, deck=0.86, cab=0.00, wing="lip", tail="bar",
                     head="slim", exhaust="twin", scoop=False, fin=0)),
    VehicleSpec("shadow_x", "SHADOW X", "Invisible jusqu'à l'impact", 800, 268, 5.6, 6.4, 5.2, 5.4,
                "#14161F", "#8B5CF6", "turbo",
                dict(L=4.56, W=1.98, H=1.20, nose=0.47, deck=0.84, cab=0.05, wing="duck", tail="claw",
                     head="blade", exhaust="center", scoop=False, fin=0)),
    VehicleSpec("phantom_rs", "PHANTOM RS", "Précision chirurgicale", 1800, 276, 6.2, 7.6, 4.6, 5.6,
                "#D9DEE8", "#FF3355", "turbo",
                dict(L=4.42, W=1.92, H=1.22, nose=0.50, deck=0.88, cab=-0.12, wing="gt", tail="round",
                     head="oval", exhaust="twin", scoop=False, fin=0)),
    VehicleSpec("thunder_v8", "THUNDER V8", "Couple brut, caractère intact", 3200, 282, 7.0, 5.0, 8.0, 5.0,
                "#C81E3A", "#FFC84A", "v8",
                dict(L=4.82, W=2.02, H=1.34, nose=0.68, deck=0.96, cab=-0.28, wing="duck", tail="triple",
                     head="muscle", exhaust="quad", scoop=True, fin=0)),
    VehicleSpec("cyber_r", "CYBER R", "Zéro émission, pleine tension", 5200, 288, 8.4, 7.0, 6.2, 7.2,
                "#8E99AD", "#00E5FF", "electric",
                dict(L=4.60, W=2.00, H=1.26, nose=0.46, deck=0.94, cab=0.10, wing="none", tail="frame",
                     head="bar", exhaust="none", scoop=False, fin=0, sharp=True)),
    VehicleSpec("inferno", "INFERNO", "Né pour brûler l'asphalte", 8000, 304, 7.8, 7.2, 6.0, 8.0,
                "#FF5A1F", "#FF3355", "v8",
                dict(L=4.62, W=2.06, H=1.16, nose=0.44, deck=0.86, cab=0.12, wing="gt", tail="flame",
                     head="blade", exhaust="center", scoop=True, fin=0)),
    VehicleSpec("velocity", "VELOCITY", "La ligne la plus courte", 12500, 326, 8.6, 8.0, 5.0, 8.4,
                "#6D3BEF", "#2CF5A0", "turbo",
                dict(L=4.74, W=2.04, H=1.12, nose=0.40, deck=0.84, cab=0.22, wing="long", tail="wave",
                     head="slim", exhaust="center", scoop=False, fin=1)),
    VehicleSpec("apex_one", "APEX ONE", "Le sommet. Rien au-dessus.", 20000, 345, 9.4, 9.0, 7.0, 9.4,
                "#0A0D16", "#FFC84A", "v8",
                dict(L=4.80, W=2.08, H=1.10, nose=0.39, deck=0.86, cab=0.28, wing="gt", tail="halo",
                     head="bar", exhaust="quad", scoop=True, fin=1)),
)
BY_ID = {v.id: v for v in VEHICLES}

PAINTS: tuple[tuple[str, str], ...] = (
    ("Cyan", "#0FB5D6"), ("Violet", "#6D3BEF"), ("Rouge", "#E0203F"), ("Blanc nacré", "#D9DEE8"),
    ("Noir obsidienne", "#0A0D16"), ("Argent", "#8E99AD"), ("Orange", "#FF5A1F"), ("Or", "#D99A1C"),
    ("Vert acide", "#3FD13A"), ("Bleu profond", "#1440C8"), ("Rose", "#F0418F"), ("Turquoise", "#0E9E8E"),
)
RIMS: tuple[str, ...] = ("Turbine", "Étoile", "Multibranche", "Holo")
LIGHTS: tuple[tuple[str, str], ...] = (
    ("Cyan", "#00E5FF"), ("Violet", "#8B5CF6"), ("Rouge", "#FF3355"), ("Blanc", "#FFFFFF"),
    ("Or", "#FFC84A"), ("Vert", "#2CF5A0"), ("Rose", "#FF4FB0"), ("Orange", "#FF7A2F"),
)
NITROS: tuple[tuple[str, str, str], ...] = (
    ("Plasma", "#00E5FF", "#3A6BFF"), ("Violette", "#C9A2FF", "#8B5CF6"),
    ("Incendie", "#FFD27A", "#FF3A1F"), ("Toxique", "#D8FF7A", "#1FD65F"), ("Rubis", "#FF9AB0", "#FF1F4B"),
)
TRAILS: tuple[str, ...] = ("Classique", "Double", "Pulsation", "Arc-en-ciel")
