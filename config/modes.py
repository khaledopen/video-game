"""Modes de jeu et réglages de difficulté."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    id: str
    name: str
    subtitle: str
    description: str
    color: str
    icon: str
    time_limit: float = 0.0        # secondes (0 = illimité)
    obstacle_rate: float = 1.0     # fréquence des obstacles
    obstacle_growth: float = 1.0   # vitesse de montée en difficulté
    traffic_rate: float = 1.0
    night: float = 0.0
    damage: float = 1.0
    coin_bonus: float = 1.0
    repairs: bool = True
    lethal: bool = True            # la voiture peut être détruite
    gesture: bool = False


MODES: tuple[Mode, ...] = (
    Mode("endless", "ENDLESS", "Survivre, encore et encore",
         "Autoroute infinie, univers qui s'enchaînent, trafic de plus en plus dense. Une seule barre de vie.",
         "#00E5FF", "infinity"),
    Mode("time_attack", "TIME ATTACK", "90 secondes, distance maximale",
         "Le chrono tourne. Les chocs ne détruisent pas la voiture mais coûtent de précieuses secondes.",
         "#FFC84A", "clock", time_limit=90.0, obstacle_rate=.8, traffic_rate=.9, damage=.8, lethal=False),
    Mode("survival", "SURVIVAL", "Le chaos augmente sans cesse",
         "Obstacles toujours plus nombreux, aucune réparation. Les pièces comptent double.",
         "#FF3355", "skull", obstacle_rate=1.9, obstacle_growth=2.4, traffic_rate=.75, coin_bonus=2.0, repairs=False),
    Mode("night", "NIGHT", "Seulement vos phares",
         "Éclairage public coupé : vous ne voyez que ce que vos phares révèlent. Score multiplié par 1,5.",
         "#8B5CF6", "moon", night=1.0, obstacle_rate=.8, traffic_rate=.85, coin_bonus=1.5),
    Mode("gesture", "GESTURE", "Conduire avec les mains",
         "La webcam suit vos mains : une main pour diriger, ou les deux comme un volant. Tout reste sur ce PC.",
         "#2CF5A0", "hand", obstacle_rate=.65, obstacle_growth=.7, traffic_rate=.75, damage=.8, gesture=True),
)
BY_ID = {m.id: m for m in MODES}
