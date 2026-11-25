"""IA de la circulation : suivi, changements de voie, évitement et règle d'équité."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from engine.mathx import approach, clamp, damp
from engine.track import LANES, lane_x, nearest_lane

# type : (longueur, largeur, hauteur, masse, vitesses km/h, dégâts)
KINDS = {
    "sedan": (4.62, 1.84, 1.44, 1.0, (88, 122), 20),
    "compact": (4.02, 1.78, 1.50, .85, (80, 112), 18),
    "coupe": (4.48, 1.92, 1.28, 1.0, (105, 150), 21),
    "roadster": (4.50, 1.96, 1.20, 1.0, (118, 168), 22),
    "van": (5.30, 2.02, 2.30, 1.5, (78, 105), 24),
    "bus": (11.0, 2.52, 3.15, 3.2, (70, 92), 32),
    "truck": (13.2, 2.56, 3.85, 4.5, (66, 88), 36),
}
WEIGHTS = {"sedan": 30, "compact": 20, "coupe": 14, "roadster": 8, "van": 14, "bus": 6, "truck": 10}
PAINTS = {
    "sedan": ("#B8C4D8", "#2A3347", "#7A1C2C", "#1D3F78", "#D9DEE8", "#4B5566"),
    "compact": ("#E0B42A", "#2FA37A", "#D9DEE8", "#3E6FD1", "#C0392B"),
    "coupe": ("#FF5A1F", "#6D3BEF", "#14161F", "#0FB5D6", "#C81E3A"),
    "roadster": ("#F0418F", "#0FB5D6", "#FFC84A", "#E9EDF5", "#3FD13A"),
    "van": ("#D9DEE8", "#8E99AD", "#1F5F8B", "#E07A1F"),
    "bus": ("#1440C8", "#C81E3A", "#0E9E8E", "#6D3BEF"),
    "truck": ("#8E99AD", "#1F2A44", "#7A1C2C", "#D9DEE8"),
}
ACCENTS = ((0, .75, 1.0), (.45, .18, 1.0), (1.0, .05, .18), (1.0, .42, .05), (.1, 1.0, .5))
# comportement : (facteur vitesse, fréquence de changement de voie, distance de sécurité, accélération)
BEHAVIOURS = {"calm": (.92, .25, 1.5, 2.2), "normal": (1.0, .7, 1.15, 3.2), "hurried": (1.10, 1.6, .85, 4.4),
              "erratic": (1.02, 2.4, .95, 4.0)}


@dataclass
class Vehicle:
    kind: str
    s: float
    lane: int
    v: float
    behaviour: str
    paint: str
    accent: tuple
    seed: float
    length: float = 4.5
    width: float = 1.9
    height: float = 1.4
    mass: float = 1.0
    hit_damage: float = 20.0
    x: float = 0.0
    want_v: float = 28.0
    target_lane: int = 0
    vx: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    spin: float = 0.0
    brake: float = 0.0
    blink: float = 0.0          # -1 / 0 / 1 clignotant
    think: float = 0.0
    commit: float = 0.0         # délai d'annonce avant changement de voie
    cooldown: float = 0.0       # plus de collision pendant ce délai
    hit: float = 0.0            # véhicule percuté : en perdition
    push: float = 0.0
    passed: bool = False
    near_gap: float = 99.0
    stalled: bool = False
    yield_t: float = 0.0
    yield_dv: float = 0.0

    @property
    def rear(self):
        return self.s - self.length / 2

    @property
    def front(self):
        return self.s + self.length / 2

    def lanes(self) -> set[int]:
        """Voies réellement occupées (deux pendant un changement de voie)."""
        out = {nearest_lane(self.x - self.width * .42), nearest_lane(self.x + self.width * .42)}
        if self.commit <= 0:
            out.add(self.target_lane)
        return out


def make_vehicle(rng: random.Random, kind: str, s: float, lane: int, difficulty: float, stalled=False) -> Vehicle:
    L, W, H, mass, (v0, v1), dmg = KINDS[kind]
    r = rng.random()
    heavy = kind in ("bus", "truck", "van")
    if heavy:
        beh = "calm" if r < .7 else "normal"
    else:
        beh = "calm" if r < .30 - .15 * difficulty else "normal" if r < .72 - .18 * difficulty else "hurried" if r < .90 else "erratic"
    v = rng.uniform(v0, v1) / 3.6 * BEHAVIOURS[beh][0]
    if stalled:
        v = 0.0
    return Vehicle(kind, s, lane, v, beh, rng.choice(PAINTS[kind]), rng.choice(ACCENTS), rng.random(), L, W, H, mass, dmg,
                   x=lane_x(lane), want_v=v, target_lane=lane, think=rng.random() * 1.5, stalled=stalled)


class TrafficAI:
    """Met à jour tous les véhicules ; aucune dépendance au rendu."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.fair_t = 0.0

    def update(self, dt, vehicles: list[Vehicle], obstacles, player, slow: float, curvature_fn=None):
        vehicles.sort(key=lambda a: a.s)
        self.fair_t -= dt
        if self.fair_t <= 0:
            self.fair_t = .15
            self._keep_passable(vehicles, obstacles, player)
        n = len(vehicles)
        for i, a in enumerate(vehicles):
            a.cooldown = max(0.0, a.cooldown - dt)
            a.yield_t = max(0.0, a.yield_t - dt)
            if a.stalled:
                a.v = 0.0
                a.blink = 2.0
                continue
            if a.hit > 0:
                self._lost_control(a, dt)
                continue
            beh = BEHAVIOURS[a.behaviour]
            # véhicule de devant dans les voies occupées
            lead_gap, lead_v = 999.0, 99.0
            lanes = a.lanes()
            for j in range(i + 1, n):
                b = vehicles[j]
                gap = b.rear - a.front
                if gap > 90:
                    break
                if lanes & b.lanes():
                    lead_gap, lead_v = gap, b.v
                    break
            if player.alive and player.s > a.s:
                gap = player.s - player.length / 2 - a.front
                if gap < lead_gap and nearest_lane(player.x) in lanes:
                    lead_gap, lead_v = gap, player.v
            danger = None
            for o in obstacles:
                if not o.solid:
                    continue
                gap = o.s - o.half_l - a.front
                if -1 < gap < 130 and abs(o.x - a.x) < o.half_w + a.width / 2 + .25:
                    if danger is None or gap < danger:
                        danger = gap
            if danger is not None and danger < lead_gap:
                lead_gap, lead_v = danger - 4.0, 0.0
            # vitesse désirée (modèle de suivi)
            want = a.want_v * slow
            if a.yield_t > 0:
                want = max(6.0, want + a.yield_dv)
            safe = 5.0 + a.v * beh[2]
            acc = beh[3] if a.v < want else -3.5
            if lead_gap < safe:
                closing = a.v - lead_v
                acc = min(acc, -2.0 - 7.0 * clamp((safe - lead_gap) / safe) - max(0.0, closing) ** 2 / max(2.0, 2.2 * lead_gap))
            acc = max(acc, -14.0)
            a.v = max(0.0, a.v + acc * dt)
            if acc > 0:
                a.v = min(a.v, max(want, a.v - 3.5 * dt))
            a.brake = damp(a.brake, 1.0 if acc < -2.2 else 0.0, 8, dt)
            # décision de changement de voie
            a.think -= dt
            if a.think <= 0 and a.lane == a.target_lane:
                a.think = (.9 + self.rng.random() * 1.6) / beh[1]
                blocked = lead_gap < safe * 1.4 and lead_v < want - 1.0
                if danger is not None and danger < 110:
                    self._try_change(a, vehicles, obstacles, player, urgent=True)
                    a.think = .25
                elif blocked or (a.behaviour == "erratic" and self.rng.random() < .55) or self.rng.random() < .06:
                    self._try_change(a, vehicles, obstacles, player)
            if a.commit > 0:
                a.commit -= dt
            # déplacement latéral
            tx = lane_x(a.target_lane)
            if a.commit <= 0 and abs(tx - a.x) > .02:
                vmax = (2.1 if a.mass > 1.4 else 3.0) * (1.25 if a.behaviour in ("hurried", "erratic") else 1.0)
                a.vx = approach(a.vx, clamp((tx - a.x) * 1.9, -vmax, vmax), 6.5 * dt)
            else:
                a.vx = damp(a.vx, 0.0, 8, dt)
            a.x += a.vx * dt
            if abs(tx - a.x) < .12:
                a.lane = a.target_lane
                a.blink = 0.0
            a.yaw = damp(a.yaw, math.atan2(a.vx, max(a.v, 10.0)), 8, dt)
            a.roll = damp(a.roll, clamp(-a.vx * .016, -.06, .06), 5, dt)
            a.s += a.v * dt
            a.spin = (a.spin + a.v / .36 * dt) % (2 * math.pi)

    def _lost_control(self, a: Vehicle, dt):
        a.hit = max(0.0, a.hit - dt)
        a.v = max(0.0, a.v - (5.5 + 3.0 / a.mass) * dt)
        a.x += a.push * dt
        a.push = damp(a.push, 0.0, 1.8, dt)
        a.x = clamp(a.x, -7.4, 7.4)
        a.yaw += a.push * .16 * dt / a.mass
        a.roll = damp(a.roll, clamp(a.push * .03, -.16, .16), 6, dt)
        a.brake = 1.0
        a.s += a.v * dt
        a.spin = (a.spin + a.v / .36 * dt) % (2 * math.pi)
        a.blink = 2.0
        if a.hit <= 0:
            a.lane = a.target_lane = nearest_lane(a.x)
            a.want_v = max(13.0, a.want_v * .7)
            a.blink = 0.0

    def _try_change(self, a: Vehicle, vehicles, obstacles, player, urgent=False) -> bool:
        options = [l for l in (a.lane - 1, a.lane + 1) if 0 <= l < LANES]
        self.rng.shuffle(options)
        for lane in options:
            if self._lane_free(a, lane, vehicles, obstacles, player, urgent):
                a.target_lane = lane
                a.blink = 1.0 if lane > a.lane else -1.0
                a.commit = .25 if urgent else .65
                return True
        return False

    def _lane_free(self, a: Vehicle, lane: int, vehicles, obstacles, player, urgent) -> bool:
        x = lane_x(lane)
        ahead, behind = (9.0, 8.0) if urgent else (16.0, 13.0)
        for b in vehicles:
            if b is a or lane not in b.lanes():
                continue
            if b.rear - a.front < ahead + max(0.0, a.v - b.v) * 1.4 and a.rear - b.front < behind + max(0.0, b.v - a.v) * 1.6:
                return False
        for o in obstacles:
            if o.solid and abs(o.x - x) < o.half_w + a.width / 2 + .2 and -6 < o.s - a.s < 90:
                return False
        # jamais de queue-de-poisson au joueur
        if player.alive:
            gap = a.rear - (player.s + player.length / 2)
            if abs(player.x - x) < 2.6 and gap > -a.length - player.length - 4:
                if gap < 10 + max(0.0, player.v - a.v) * 1.5:
                    return False
        # ne pas fermer la dernière voie ouverte
        open_lanes = set(range(LANES)) - occupied_lanes(vehicles, obstacles, a.s - 24, a.s + 24, ignore=a)
        return bool(open_lanes - {lane})

    def _keep_passable(self, vehicles, obstacles, player):
        """Garantit un passage : si quatre voies se ferment, un véhicule cède."""
        horizon = player.s + 420
        ahead = [a for a in vehicles if player.s - 5 < a.s < horizon]
        for a in ahead:
            lo, hi = a.s - 17, a.s + 17
            if len(occupied_lanes(ahead, obstacles, lo, hi)) < LANES:
                continue
            group = [b for b in ahead if b.front > lo and b.rear < hi and not b.stalled and b.hit <= 0]
            if not group:
                continue
            first, last = max(group, key=lambda b: b.s), min(group, key=lambda b: b.s)
            first.yield_t, first.yield_dv = .7, 7.0
            if last is not first:
                last.yield_t, last.yield_dv = .7, -7.0


def occupied_lanes(vehicles, obstacles, lo: float, hi: float, ignore=None) -> set[int]:
    out: set[int] = set()
    for b in vehicles:
        if b is not ignore and b.front > lo and b.rear < hi:
            out |= b.lanes()
    for o in obstacles:
        if o.solid and o.s + o.half_l > lo and o.s - o.half_l < hi:
            out |= o.lanes
    return out
