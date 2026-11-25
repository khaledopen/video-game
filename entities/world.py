"""Simulation complète d'une partie, indépendante du rendu et de l'audio.

La scène de jeu lit `events` après chaque mise à jour pour déclencher effets et sons.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from config.environments import PLAYABLE, Environment
from config.modes import Mode
from config.vehicles import VehicleSpec
from engine.mathx import clamp
from engine.track import Track
from entities.collision import circle_hit, obb_overlap
from entities.player import Controls, Player
from entities.spawner import Spawner
from entities.traffic import TrafficAI, Vehicle

LEVEL_LENGTH = 1500.0
STEP = 1 / 120


@dataclass
class Event:
    kind: str
    x: float = 0.0
    y: float = .6
    s: float = 0.0
    power: float = 0.0
    data: object = None


@dataclass
class RunStats:
    score: float = 0.0
    distance: float = 0.0
    time: float = 0.0
    top_speed: float = 0.0
    coins: int = 0
    dodged: int = 0
    near_misses: int = 0
    crashes: int = 0
    pickups: int = 0
    nitro_time: float = 0.0
    best_combo: int = 0
    perfect: float = 0.0        # plus longue distance sans choc
    level: int = 1
    environments: set = field(default_factory=set)


class World:
    def __init__(self, spec: VehicleSpec, mode: Mode, env: Environment | None = None, seed: int | None = None,
                 size: tuple[float, float] = (1.95, 4.6)):
        self.mode = mode
        self.rng = random.Random(seed)
        self.track = Track(self.rng.randrange(1 << 30))
        self.player = Player(spec, *size)
        self.fixed_env = env is not None
        self.env_order = list(PLAYABLE)
        if env is None:
            rest = self.env_order[1:]
            self.rng.shuffle(rest)
            self.env_order = [PLAYABLE[0]] + rest
        self.env = env or self.env_order[0]
        self.track.set_environment(self.env.index, True)
        self.vehicles: list[Vehicle] = []
        self.obstacles: list = []
        self.coins: list = []
        self.pickups: list = []
        self.events: list[Event] = []
        self.spawner = Spawner(self.rng, mode)
        self.ai = TrafficAI(self.rng)
        self.stats = RunStats()
        self.stats.environments.add(self.env.id)
        self.combo, self.combo_t = 0, 0.0
        self.since_crash = 0.0
        self.time_left = mode.time_limit
        self.over = False
        self.over_reason = ""
        self.dt = 0.0
        self.spawn_cd = 0.0
        self.acc = 0.0
        self.coin_streak, self.coin_t = 0, 0.0
        self.scrape_cd = 0.0
        self.sky_yaw = 0.0

    # -- propriétés ---------------------------------------------------------------------
    @property
    def multiplier(self) -> float:
        m = 1.0 + min(self.combo, 20) * .1
        if self.player.active("multi"):
            m *= 2
        if self.mode.id == "night":
            m *= 1.5
        return m

    @property
    def difficulty(self) -> float:
        return self.spawner.difficulty(self.player.s)

    @property
    def next_env(self) -> Environment:
        i = self.env_order.index(self.env)
        return self.env_order[(i + 1) % len(self.env_order)]

    @property
    def portal_s(self) -> float:
        """Distance du prochain portail (2 niveaux par univers)."""
        seg = LEVEL_LENGTH * 2
        return (math.floor(self.player.s / seg) + 1) * seg

    def emit(self, kind, x=0., s=0., y=.6, power=0., data=None):
        self.events.append(Event(kind, x, y, s, power, data))

    # -- boucle ------------------------------------------------------------------------------
    def update(self, dt: float, c: Controls) -> None:
        """Pas fixe de 1/120 s : même physique quel que soit le nombre d'images par seconde."""
        self.acc = min(self.acc + dt, .12)
        while self.acc >= STEP:
            self.acc -= STEP
            self._step(STEP, c)

    def _step(self, dt: float, c: Controls) -> None:
        p, st = self.player, self.stats
        self.dt = dt
        prev_s = p.s
        k = float(self.track.curvature(p.s))
        was_nitro = p.nitro_on
        p.update(dt, c, k, self.env.grip, 1.0 + .10 * self.difficulty)
        if p.nitro_on and not was_nitro:
            self.emit("nitro_start", p.x, p.s)
        elif was_nitro and not p.nitro_on:
            self.emit("nitro_end", p.x, p.s)
        self.sky_yaw += k * p.v * dt * .9
        self.track.update(dt)
        self._edges(dt)
        if not self.over:
            self.spawner.update(self)
        slow = .55 if p.active("slow") else 1.0
        self.ai.update(dt, self.vehicles, self.obstacles, p, slow)
        self._vehicles(dt, prev_s)
        self._obstacles(dt)
        self._items(dt)
        self._progress(dt, prev_s)
        self._cleanup()

    def _edges(self, dt):
        p = self.player
        self.scrape_cd = max(0.0, self.scrape_cd - dt)
        if abs(p.x) <= p.edge:
            return
        side = math.copysign(1.0, p.x)
        p.x = side * p.edge
        impact = abs(p.vx) if p.vx * side > 0 else 0.0
        if impact > 5.0 and self.scrape_cd <= 0:
            self._hurt(2.0 + impact * .55, side * (p.edge + .9), p.s, "wall", .25 + impact * .03)
            p.vx = -side * impact * .42
            p.v *= .95
            self.scrape_cd = .45
        else:
            p.vx = min(p.vx * side, 0.0) * side
            if self.scrape_cd <= 0:
                self.scrape_cd = .12
                if not p.active("shield"):
                    p.hp = max(0.0, p.hp - .45 * self.mode.damage) if self.mode.lethal else p.hp
                self.emit("scrape", side * (p.edge + .9), p.s)
        p.scraping = .18
        p.v -= p.v * .16 * dt

    def _hurt(self, amount, x, s, source, power):
        """Choc : bouclier, dégâts, ralentissement, événements."""
        p, st = self.player, self.stats
        if p.invuln > 0 or not p.alive:
            return False
        if p.active("shield"):
            p.timers["shield"] = max(0.0, p.timers["shield"] - 4.0)
            p.invuln = .8
            self.emit("shield_hit", x, s, power=power)
            return True
        p.damage(amount, self.mode.damage if self.mode.lethal else 0.0)
        heavy = power > .55
        if source not in ("cone", "wall"):
            st.crashes += 1
        self.combo = 0
        st.perfect = max(st.perfect, self.since_crash)
        self.since_crash = 0.0
        p.invuln = max(p.invuln, 1.1 if heavy else .35)
        if not self.mode.lethal and amount > 8:
            self.time_left = max(.1, self.time_left - 2.0)
            self.emit("time_penalty", x, s, power=2.0)
        self.emit("crash" if heavy else "bump", x, s, power=power, data=source)
        if p.hp <= 0 and self.mode.lethal:
            self._die(x, s)
        return True

    def _die(self, x, s):
        p = self.player
        p.alive = False
        p.nitro_on = False
        p.spinout = 5.2 * (1 if self.rng.random() < .5 else -1)
        self.over, self.over_reason = True, "destroyed"
        self.emit("destroyed", p.x, p.s, power=1.0)

    def _vehicles(self, dt, prev_s):
        p, st = self.player, self.stats
        ph, pl = p.width / 2 * .93, p.length / 2 * .97
        for a in self.vehicles:
            ds = a.s - p.s
            if abs(ds) < 22 and a.cooldown <= 0 and p.alive:
                hit = obb_overlap(p.x, p.s, ph, pl, p.yaw, a.x, a.s, a.width / 2 * .95, a.length / 2 * .98, a.yaw)
                if hit:
                    self._hit_vehicle(a, hit)
                else:
                    lat = abs(a.x - p.x) - (a.width + p.width) / 2
                    lon = abs(ds) - (a.length + p.length) / 2
                    if lon < .6:
                        a.near_gap = min(a.near_gap, lat)
            if not a.passed and a.front < p.s - p.length / 2:
                a.passed = True
                st.dodged += 1
                if p.alive and a.cooldown <= 0 and a.near_gap < 1.15 and p.v - a.v > 7:
                    st.near_misses += 1
                    self.combo += 1
                    self.combo_t = 5.0
                    st.best_combo = max(st.best_combo, self.combo)
                    p.nitro = min(1.0, p.nitro + .07)
                    pts = 120 * self.multiplier
                    st.score += pts
                    self.emit("near_miss", (a.x + p.x) / 2, p.s, power=clamp(1 - a.near_gap / 1.15), data=int(pts))

    def _hit_vehicle(self, a: Vehicle, hit):
        p = self.player
        pen, nx, ns = hit
        rel = p.v - a.v
        cx, cs = (p.x * .55 + a.x * .45), (p.s + (p.length * .4 if a.s > p.s else -p.length * .4))
        a.cooldown = 1.0
        if p.active("shield"):
            self._hurt(0, cx, cs, "vehicle", .5)
            a.push, a.hit = (7.0 if a.x >= p.x else -7.0) / max(1.0, a.mass * .5), 1.1
            a.v = max(a.v, p.v * .8)
            return
        if abs(ns) > abs(nx):                           # choc avant / arrière
            power = clamp(abs(rel) / 38, .12, 1.0)
            done = self._hurt(a.hit_damage * (.35 + 1.05 * power), cx, cs, "vehicle", power)
            if ns < 0:                                  # le joueur tape l'arrière
                p.s = min(p.s, a.s - (a.length + p.length) / 2 - .05)
                share = a.mass / (1.3 + a.mass)
                p.v = max(9.0, a.v + rel * (.40 - .55 * share))
                a.v += max(0.0, rel) * .75 / (.6 + a.mass)
            elif done:
                a.v = min(a.v, p.v * .9)
            side = 1.0 if a.x >= p.x else -1.0
            a.push = side * (2.0 + 5.0 * power) / a.mass
            a.hit = .5 + .9 * power / a.mass
            p.vx -= side * 2.5 * power
            p.spinout = -side * .28 * power
        else:                                           # touchette latérale
            side = 1.0 if nx > 0 else -1.0
            power = clamp(.18 + abs(p.vx - a.vx) * .035 + abs(rel) * .004, .15, .6)
            self._hurt(5.0 + 12.0 * power, cx, cs, "side", power * .85)
            p.x += side * (pen + .04)
            p.vx = side * max(2.4, abs(p.vx) * .55)
            p.v *= .975
            a.push = -side * 4.0 / a.mass
            a.hit = .45
            a.cooldown = .45

    def _obstacles(self, dt):
        p, st = self.player, self.stats
        ph, pl = p.width / 2 * .92, p.length / 2 * .96
        for o in self.obstacles:
            if o.fly:
                vx, vy, vs, vr = o.fly
                vy -= 12.0 * dt
                o.x += vx * dt
                o.y = max(0.0, o.y + vy * dt)
                o.s += vs * dt
                o.rot += vr * dt
                o.fly = (vx, -vy * .4 if o.y <= 0 and vy < 0 else vy, vs * (1 - .3 * dt), vr * (1 - .5 * dt))
                continue
            if not o.passed and o.s + o.half_l < p.s - pl:
                o.passed = True
                if not o.touched and o.kind != "puddle":
                    st.dodged += 1
            if o.dead or abs(o.s - p.s) > 8 or not p.alive:
                continue
            if not obb_overlap(p.x, p.s, ph, pl, p.yaw, o.x, o.s, o.half_w, o.half_l, 0.0):
                continue
            o.touched = True
            if o.kind == "puddle":
                o.dead = True
                p.slip = max(p.slip, .85)
                p.vx += self.rng.uniform(-2.2, 2.2) * (1.3 - .08 * p.spec.handling)
                self.emit("splash", o.x, o.s, .1)
            elif o.kind in ("cone", "debris"):
                o.dead = True
                out = math.copysign(1, o.x - p.x or 1)
                o.fly = (out * self.rng.uniform(2, 7), self.rng.uniform(4, 8), p.v * self.rng.uniform(.75, 1.15), self.rng.uniform(-14, 14))
                self._hurt(o.damage, o.x, o.s, o.kind, .2 if o.kind == "cone" else .42)
                p.v *= .985 if o.kind == "cone" else .93
            else:
                power = clamp(p.v / 52, .5, 1.0)
                o.dead = True
                if self._hurt(o.damage * (.45 + .75 * power), o.x, o.s - o.half_l, o.kind, power):
                    if not p.active("shield"):
                        p.v *= .42
                        side = 1.0 if p.x >= o.x else -1.0
                        p.vx = side * 5.0
                        p.spinout = side * .35
                    o.fly = ((-1.0 if p.x >= o.x else 1.0) * 5.0, 5.5, p.v * .9 + 14, self.rng.uniform(-4, 4))

    def _items(self, dt):
        p, st = self.player, self.stats
        ph, pl = p.width / 2, p.length / 2
        self.coin_t = max(0.0, self.coin_t - dt)
        if self.coin_t <= 0:
            self.coin_streak = 0
        magnet = p.active("magnet")
        for c in self.coins:
            ds = c.s - p.s
            if ds > 34 or ds < -6:
                continue
            if magnet and p.alive and -3 < ds < 30:
                pull = clamp(1 - abs(ds) / 30) * 16 * dt
                c.x += clamp(p.x - c.x, -pull, pull)
                c.s -= max(0.0, ds) * 1.2 * dt
            if p.alive and circle_hit(p.x, p.s, ph, pl, c.x, c.s, .62):
                c.taken = True
                gain = int(c.value * self.mode.coin_bonus + .001)
                st.coins += gain
                st.score += 25 * c.value * self.multiplier
                self.coin_streak += 1
                self.coin_t = 1.2
                self.emit("coin", c.x, c.s, c.y, power=min(self.coin_streak, 12), data=gain)
        for k in self.pickups:
            if p.alive and abs(k.s - p.s) < 8 and circle_hit(p.x, p.s, ph, pl, k.x, k.s, .95):
                k.taken = True
                st.pickups += 1
                p.give(k.kind)
                st.score += 150 * self.multiplier
                self.emit("pickup", k.x, k.s, .8, data=k.kind)

    def _progress(self, dt, prev_s):
        p, st = self.player, self.stats
        if self.over:
            return
        st.time += dt
        ds = p.s - prev_s
        st.distance = p.s
        self.since_crash += max(0.0, ds)
        st.perfect = max(st.perfect, self.since_crash)
        st.top_speed = max(st.top_speed, p.v * 3.6)
        if p.nitro_on:
            st.nitro_time += dt
        st.score += max(0.0, ds) * (1.0 + 1.6 * p.speed_ratio ** 2) * self.multiplier
        if self.combo:
            self.combo_t -= dt
            if self.combo_t <= 0:
                self.combo = 0
                self.emit("combo_end")
        lvl = 1 + int(p.s // LEVEL_LENGTH)
        if lvl != st.level:
            st.level = lvl
            self.emit("level", data=lvl)
            seg = LEVEL_LENGTH * 2
            if not self.fixed_env and int(prev_s // seg) != int(p.s // seg):
                self.env = self.next_env
                self.track.set_environment(self.env.index)
                st.environments.add(self.env.id)
                self.emit("environment", data=self.env)
        if self.mode.time_limit:
            before = self.time_left
            self.time_left -= dt
            if self.time_left <= 10 and math.ceil(before) != math.ceil(self.time_left):
                self.emit("tick")
            if self.time_left <= 0:
                self.time_left = 0.0
                self.over, self.over_reason = True, "time"
                self.emit("time_up")
        if p.alive and p.hp <= 0 and self.mode.lethal:
            self._die(p.x, p.s)

    def _cleanup(self):
        back = self.player.s - 70
        if any(v.s < back for v in self.vehicles) or len(self.vehicles) > 40:
            self.vehicles = [v for v in self.vehicles if v.s > back]
        self.vehicles = [v for v in self.vehicles if v.s < self.player.s + 620]
        if self.obstacles and self.obstacles[0].s < back or any(o.fly and o.s < back for o in self.obstacles):
            self.obstacles = [o for o in self.obstacles if o.s > back]
        if self.coins and (self.coins[0].s < back or any(c.taken for c in self.coins)):
            self.coins = [c for c in self.coins if c.s > back and not c.taken]
        if self.pickups and (self.pickups[0].s < back or any(k.taken for k in self.pickups)):
            self.pickups = [k for k in self.pickups if k.s > back and not k.taken]

    def drain_events(self) -> list[Event]:
        out, self.events = self.events, []
        return out
