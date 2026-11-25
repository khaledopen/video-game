"""Niveaux du pilote, récompenses et succès."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from database.store import Store
from entities.world import World

RANKS = ((1, "ROOKIE"), (5, "STREET RACER"), (10, "NIGHT RUNNER"), (16, "NEON ACE"), (24, "PHANTOM"), (35, "APEX LEGEND"))


def xp_for(level: int) -> int:
    """Expérience nécessaire pour passer du niveau `level` au suivant."""
    return int(320 * level**1.25)


def level_from_xp(xp: float) -> tuple[int, float, int]:
    """(niveau, expérience dans le niveau, expérience requise)."""
    level = 1
    while xp >= xp_for(level):
        xp -= xp_for(level)
        level += 1
    return level, xp, xp_for(level)


def rank(level: int) -> str:
    return [n for lv, n in RANKS if level >= lv][-1]


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    reward: int
    test: Callable[[dict], bool]      # reçoit le contexte (partie + totaux)
    icon: str = "star"


A = Achievement
ACHIEVEMENTS: tuple[Achievement, ...] = (
    A("first_run", "PREMIER CONTACT", "Terminer une première partie", 50, lambda c: c["games"] >= 1, "flag"),
    A("km5", "EN ROUTE", "Parcourir 5 km en une partie", 100, lambda c: c["distance"] >= 5000, "road"),
    A("km10", "LONGUE DISTANCE", "Parcourir 10 km en une partie", 250, lambda c: c["distance"] >= 10000, "road"),
    A("km20", "HORS LIMITE", "Parcourir 20 km en une partie", 600, lambda c: c["distance"] >= 20000, "road"),
    A("total100", "GLOBE-TROTTER", "Cumuler 100 km", 400, lambda c: c["total_distance"] >= 100_000, "road"),
    A("score25", "LUMINEUX", "Atteindre 25 000 points", 150, lambda c: c["score"] >= 25_000, "star"),
    A("score75", "INCANDESCENT", "Atteindre 75 000 points", 400, lambda c: c["score"] >= 75_000, "star"),
    A("score200", "SUPERNOVA", "Atteindre 200 000 points", 1200, lambda c: c["score"] >= 200_000, "star"),
    A("speed250", "CLUB 250", "Dépasser 250 km/h", 80, lambda c: c["top_speed"] >= 250, "speed"),
    A("speed330", "MUR DU SON", "Dépasser 330 km/h", 300, lambda c: c["top_speed"] >= 330, "speed"),
    A("speed400", "HYPERVITESSE", "Dépasser 400 km/h", 900, lambda c: c["top_speed"] >= 400, "speed"),
    A("coins100", "COLLECTIONNEUR", "Ramasser 100 pièces en une partie", 120, lambda c: c["coins"] >= 100, "coin"),
    A("coins300", "PLUIE D'OR", "Ramasser 300 pièces en une partie", 450, lambda c: c["coins"] >= 300, "coin"),
    A("near10", "AU MILLIMÈTRE", "10 frôlements en une partie", 150, lambda c: c["near_misses"] >= 10, "bolt"),
    A("combo8", "SANG-FROID", "Combo de 8 frôlements", 350, lambda c: c["best_combo"] >= 8, "bolt"),
    A("perfect3", "SANS UNE ÉGRATIGNURE", "3 km sans le moindre choc", 250, lambda c: c["perfect"] >= 3000, "shield"),
    A("dodge100", "INTOUCHABLE", "Éviter 100 obstacles en une partie", 200, lambda c: c["dodged"] >= 100, "shield"),
    A("world5", "TOUR DU MONDE", "Traverser les 5 univers en une partie", 500, lambda c: c["environments"] >= 5, "globe"),
    A("night5", "VISION NOCTURNE", "5 km en mode Night", 250, lambda c: c["mode"] == "night" and c["distance"] >= 5000, "moon"),
    A("survival5", "CHAOS MAÎTRISÉ", "5 km en mode Survival", 350, lambda c: c["mode"] == "survival" and c["distance"] >= 5000, "skull"),
    A("gesture2", "CHEF D'ORCHESTRE", "2 km en mode Gesture", 250, lambda c: c["mode"] == "gesture" and c["distance"] >= 2000, "hand"),
    A("garage3", "PETITE ÉCURIE", "Posséder 3 véhicules", 150, lambda c: c["owned"] >= 3, "car"),
    A("garage8", "COLLECTION COMPLÈTE", "Posséder les 8 véhicules", 2000, lambda c: c["owned"] >= 8, "car"),
    A("games25", "HABITUÉ", "Jouer 25 parties", 300, lambda c: c["games"] >= 25, "flag"),
)
ACH_BY_ID = {a.id: a for a in ACHIEVEMENTS}


@dataclass
class RunResult:
    score: int
    best: int                  # meilleur score précédent du mode
    record: bool
    coins: int
    xp: int
    level_before: int
    level_after: int
    level_bonus: int
    xp_into: float
    xp_need: int
    achievements: list = field(default_factory=list)
    bonus_coins: int = 0


def context(store: Store, world: World | None = None) -> dict:
    t = store.totals()
    c = dict(games=t["games"], total_distance=t["distance"], owned=len(store.unlocked()), score=0, distance=0, top_speed=0, coins=0,
             near_misses=0, best_combo=0, perfect=0, dodged=0, environments=0, mode="")
    if world is not None:
        s = world.stats
        c.update(score=s.score, distance=s.distance, top_speed=s.top_speed, coins=s.coins, near_misses=s.near_misses, best_combo=s.best_combo,
                 perfect=s.perfect, dodged=s.dodged, environments=len(s.environments), mode=world.mode.id)
    return c


def check_achievements(store: Store, world: World | None = None) -> list[Achievement]:
    """Débloque les succès atteints et verse leurs pièces."""
    ctx, done, new = context(store, world), store.achievements(), []
    for a in ACHIEVEMENTS:
        if a.id not in done and a.test(ctx) and store.unlock_achievement(a.id):
            store.add("coins", a.reward)
            new.append(a)
    return new


def finish_run(store: Store, world: World) -> RunResult:
    """Enregistre la partie et calcule toutes les récompenses."""
    s, mode = world.stats, world.mode
    score = int(s.score)
    best = store.best(mode.id)
    store.add_run(mode.id, world.env.id, world.player.spec.id, score, s.distance, s.time, s.top_speed, s.coins, s.dodged, s.near_misses, s.level)
    store.add("coins", s.coins)
    xp = int(s.distance / 25 + score / 140 + s.near_misses * 6 + s.dodged)
    before, _, _ = level_from_xp(store.get("xp"))
    after, into, need = level_from_xp(store.add("xp", xp))
    bonus = sum(60 + 20 * lv for lv in range(before + 1, after + 1))
    if bonus:
        store.add("coins", bonus)
    ach = check_achievements(store, world)
    return RunResult(score, best, score > best and score > 0, s.coins, xp, before, after, bonus, into, need, ach, sum(a.reward for a in ach))
