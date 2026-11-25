"""Génération procédurale du trafic, des obstacles, des pièces et des bonus.

Règle d'équité : chaque rangée d'obstacles laisse au moins une voie libre (deux au
début), deux rangées sont toujours assez espacées pour traverser la route, et aucun
véhicule n'apparaît là où il fermerait le dernier passage.
"""
from __future__ import annotations

import math
import random

from config.modes import Mode
from engine.track import LANES, LANE_W, lane_x
from entities.obstacles import Coin, Pickup, PICKUP_KINDS, make_obstacle
from entities.traffic import WEIGHTS, make_vehicle, occupied_lanes

SPAWN_AHEAD = 430.0


class Spawner:
    def __init__(self, rng: random.Random, mode: Mode):
        self.rng, self.mode = rng, mode
        self.next_obstacle = 260.0
        self.next_coins = 120.0
        self.next_pickup = 320.0
        self.next_traffic = 0.0
        self.warm = False
        self.last_kind = ""

    def difficulty(self, distance: float) -> float:
        return 1.0 - math.exp(-distance * self.mode.obstacle_growth / 8500.0)

    def update(self, world) -> None:
        p = world.player
        d = self.difficulty(p.s)
        horizon = p.s + SPAWN_AHEAD
        if not self.warm:                       # peuplement initial
            self.warm = True
            s = p.s + 110
            while s < horizon:
                self._vehicle(world, s, d)
                s += self.rng.uniform(30, 58)
            self.next_traffic = horizon
        while self.next_obstacle < horizon:
            self._obstacle_row(world, self.next_obstacle, d)
            base = 210.0 - 95.0 * d
            gap = base / self.mode.obstacle_rate * self.rng.uniform(.8, 1.35)
            self.next_obstacle += max(82.0, gap)
        while self.next_coins < horizon:
            self.next_coins += self._coins(world, self.next_coins) + self.rng.uniform(55, 130)
        while self.next_pickup < horizon:
            self._pickup(world, self.next_pickup, d)
            self.next_pickup += self.rng.uniform(300, 520) - 70 * d
        # trafic : densité visée par tranche de route devant le joueur
        ahead = [v for v in world.vehicles if v.s > p.s]
        want = (8.5 + 9.0 * d) * self.mode.traffic_rate
        world.spawn_cd -= world.dt
        if len(ahead) < want and world.spawn_cd <= 0:
            far = max((v.s for v in ahead), default=p.s + 150)
            s = max(p.s + 330 + self.rng.random() * 60, min(far + self.rng.uniform(26, 60) - 18 * d, horizon + 30))
            if self._vehicle(world, s, d):
                world.spawn_cd = .22 + .35 * self.rng.random()

    def _vehicle(self, world, s, d) -> bool:
        kinds = list(WEIGHTS)
        kind = self.rng.choices(kinds, [WEIGHTS[k] for k in kinds])[0]
        lanes = list(range(LANES))
        self.rng.shuffle(lanes)
        for lane in lanes:
            v = make_vehicle(self.rng, kind, s, lane, d)
            if any(abs(b.s - s) < (b.length + v.length) / 2 + 14 and lane in b.lanes() for b in world.vehicles):
                continue
            if any(o.solid and lane in o.lanes and -14 < o.s - s < 60 for o in world.obstacles):
                continue
            if len(occupied_lanes(world.vehicles, world.obstacles, s - 26, s + 26) | {lane}) >= LANES:
                continue
            world.vehicles.append(v)
            return True
        return False

    # -- obstacles --------------------------------------------------------------------
    def _obstacle_row(self, world, s, d):
        r = self.rng
        kinds = ["cones", "puddle", "debris", "barrier", "works", "stalled", "double", "slalom"]
        w = [16, 14, 13, 15 + 8 * d, 9 + 6 * d, 9 + 5 * d, 3 + 15 * d, 4 + 8 * d]
        if self.last_kind in kinds:
            w[kinds.index(self.last_kind)] *= .35
        kind = r.choices(kinds, w)[0]
        self.last_kind = kind
        taken = occupied_lanes([], world.obstacles, s - 40, s + 40)
        lanes = [l for l in range(LANES) if l not in taken]
        if len(lanes) < 2:
            return
        r.shuffle(lanes)
        ob = world.obstacles
        lane = lanes[0]
        if kind == "cones":
            side = r.choice((-1, 1))
            for i in range(6):
                ob.append(make_obstacle("cone", s + i * 3.4, lane_x(lane) + side * (-1.3 + i * .5), r.random()))
        elif kind == "puddle":
            for l in lanes[:r.choice((1, 1, 2))]:
                ob.append(make_obstacle("puddle", s + r.uniform(-8, 8), lane_x(l) + r.uniform(-.3, .3), r.random()))
        elif kind == "debris":
            for l in lanes[:r.choice((1, 2))]:
                ob.append(make_obstacle("debris", s + r.uniform(-10, 10), lane_x(l) + r.uniform(-.7, .7), r.random()))
        elif kind == "barrier":
            ob.append(make_obstacle("barrier", s, lane_x(lane), r.random()))
        elif kind == "double":
            a = r.randrange(LANES - 1)
            pair = [a, a + 1]
            if d > .45 and r.random() < .35 * d:
                pair.append((a + 2) if a + 2 < LANES else a - 1)
            for l in pair:
                if l not in taken:
                    ob.append(make_obstacle("barrier", s + r.uniform(-.2, .2), lane_x(l), r.random()))
        elif kind == "works":
            ob.append(make_obstacle("roadworks", s, lane_x(lane), r.random()))
            for i in range(5):
                ob.append(make_obstacle("cone", s - 22 + i * 4.4, lane_x(lane) + (-1.4 if lane < 2 else 1.4) * (1 - i / 4) + (1.4 if lane < 2 else -1.4) * (i / 4), r.random()))
        elif kind == "stalled":
            k = r.choice(("sedan", "van", "compact", "truck" if d > .4 else "sedan"))
            if not any(abs(v.s - s) < 30 and lane in v.lanes() for v in world.vehicles):
                v = make_vehicle(r, k, s, lane, d, stalled=True)
                world.vehicles.append(v)
                ob.append(make_obstacle("cone", s - v.length / 2 - 4.5, lane_x(lane) - .7, r.random()))
                ob.append(make_obstacle("cone", s - v.length / 2 - 4.5, lane_x(lane) + .7, r.random()))
        else:                                           # slalom : barrières alternées bien espacées
            first = r.randrange(LANES)
            step = max(52.0, 78.0 - 22 * d)
            for i in range(3):
                l = (first + i * 2) % LANES
                ob.append(make_obstacle("barrier", s + i * step, lane_x(l), r.random()))
            self.next_obstacle += 2 * step

    # -- pièces et bonus ----------------------------------------------------------------
    def _free_lane(self, world, s, length) -> int:
        blocked = set()
        for o in world.obstacles:
            if o.kind != "puddle" and s - 14 < o.s < s + length + 14:
                blocked |= {l for l in range(LANES) if abs(lane_x(l) - o.x) < o.half_w + 1.1}
        for v in world.vehicles:
            if v.stalled and s - 14 < v.s < s + length + 14:
                blocked |= v.lanes()
        free = [l for l in range(LANES) if l not in blocked]
        return self.rng.choice(free or list(range(LANES)))

    def _coins(self, world, s) -> float:
        r = self.rng
        n = r.choice((6, 8, 10))
        shape = r.choice(("line", "line", "wave", "shift", "arc"))
        step = 5.2
        length = n * step
        lane = self._free_lane(world, s, length)
        x0 = lane_x(lane)
        other = lane + (1 if lane == 0 or (lane < LANES - 1 and r.random() < .5) else -1)
        for i in range(n):
            t = i / (n - 1)
            x, y = x0, .78
            if shape == "wave":
                x += math.sin(t * math.tau) * .9
            elif shape == "shift":
                k = t * t * (3 - 2 * t)
                x = x0 + (lane_x(other) - x0) * k
            elif shape == "arc":
                y += math.sin(t * math.pi) * .35
            world.coins.append(Coin(s + i * step, x, y, 5 if (i == n - 1 and r.random() < .25) else 1, i * .35))
        return length

    def _pickup(self, world, s, d):
        r = self.rng
        p = world.player
        w = {"nitro": 26, "shield": 15, "magnet": 14, "repair": 10 + (22 if p.hp < 55 else 0), "multi": 14, "slow": 11 + 6 * d}
        if not self.mode.repairs:
            w["repair"] = 0
        kind = r.choices(PICKUP_KINDS, [w[k] for k in PICKUP_KINDS])[0]
        lane = self._free_lane(world, s, 6)
        world.pickups.append(Pickup(kind, s, lane_x(lane) + r.uniform(-.2, .2) * LANE_W * .3, r.random() * 6))
