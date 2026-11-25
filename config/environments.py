"""Univers graphiques : lumière, brouillard, humidité, décor et couleurs."""
from __future__ import annotations

from dataclasses import dataclass

CITY, DESERT, TOKYO, MOUNTAIN, TUNNEL, STUDIO = range(6)


@dataclass(frozen=True)
class Environment:
    index: int
    id: str
    name: str
    subtitle: str
    sun_dir: tuple            # vers la source
    sun_col: tuple            # linéaire HDR
    amb_sky: tuple
    amb_gnd: tuple
    fog: tuple
    fog_density: float
    wet: float                # 0 sec .. 1 trempé
    lamp: tuple               # couleur des lampadaires
    lamp_power: float
    edge: tuple               # couleur du liseré de route
    edge2: tuple
    rain: float
    dust: float
    headlight: float
    accent: str               # couleur d'interface
    grip: float = 1.0


ENVIRONMENTS: tuple[Environment, ...] = (
    Environment(CITY, "neon_city", "NEON CITY", "Mégalopole, 02:14",
                (-.35, .55, .6), (.28, .25, .6), (.10, .13, .30), (.05, .04, .10),
                (.030, .030, .085), .0042, .62, (.35, .75, 1.0), 1.0,
                (0.0, .78, 1.0), (.35, .12, 1.0), 0.0, 0.0, .9, "#00E5FF"),
    Environment(DESERT, "desert_highway", "DESERT HIGHWAY", "Dernières lueurs du couchant",
                (-.22, .16, .96), (2.0, .80, .32), (.30, .18, .25), (.20, .10, .07),
                (.50, .19, .15), .0026, 0.0, (1.0, .6, .3), 0.0,
                (1.0, .42, .10), (1.0, .10, .28), 0.0, 1.0, .25, "#FF9A4A"),
    Environment(TOKYO, "rainy_tokyo", "RAINY TOKYO", "Averse sur la voie express",
                (.2, .8, .4), (.16, .16, .30), (.10, .10, .21), (.07, .04, .10),
                (.050, .035, .085), .0060, 1.0, (1.0, .45, .75), .9,
                (1.0, .12, .45), (0.0, .75, 1.0), 1.0, 0.0, 1.0, "#FF4FB0", .92),
    Environment(MOUNTAIN, "mountain_road", "MOUNTAIN ROAD", "Col de l'aube",
                (.45, .42, .78), (1.45, 1.12, .85), (.24, .31, .45), (.10, .12, .10),
                (.36, .46, .60), .0018, .08, (1.0, .85, .6), 0.0,
                (.75, .9, 1.0), (.25, .7, 1.0), 0.0, 0.25, .35, "#7CC4FF"),
    Environment(TUNNEL, "cyber_tunnel", "CYBER TUNNEL", "Accélérateur souterrain",
                (0.0, 1.0, .1), (.25, .3, .5), (.09, .11, .20), (.05, .06, .11),
                (.012, .016, .04), .0046, .75, (.55, .35, 1.0), 1.2,
                (.45, .2, 1.0), (0.0, .85, 1.0), 0.0, 0.0, .8, "#8B5CF6"),
    Environment(STUDIO, "studio", "STUDIO", "",
                (-.4, .8, -.45), (.85, .90, 1.05), (.12, .14, .23), (.05, .05, .09),
                (.010, .014, .030), .012, .9, (.4, .7, 1.0), 0.0,
                (0.0, .8, 1.0), (.5, .2, 1.0), 0.0, 0.0, .6, "#00E5FF"),
)
PLAYABLE = ENVIRONMENTS[:5]
BY_ID = {e.id: e for e in ENVIRONMENTS}
