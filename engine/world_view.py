"""Rendu d'une partie : caméra, effets, véhicules, objets. Lit le World sans le modifier."""
from __future__ import annotations

import math

import numpy as np

from config.environments import ENVIRONMENTS
from config.palette import linear, rgb
from config.vehicles import NITROS
from effects.animation import CameraShake, TimeWarp
from effects.particles import GLOW, RING, SMOKE, SPARK, STAR, Particles
from effects.trails import Trail
from engine.mathx import clamp, damp, lerp, look_angles, smooth
from engine.renderer import FrameView, Renderer, row
from engine.scenery import Scenery
from engine.vehicle_draw import Look, draw_player, draw_traffic
from entities.obstacles import PICKUP_COLORS
from entities.world import World

GOLD = (.62, .34, .04)
DAY = {1: .30, 3: .25}           # univers diurnes : néons de caisse atténués


class WorldView:
    def __init__(self, renderer: Renderer, world: World, look: Look, nitro: int = 0, trail: int = 0, fx: float = .85):
        self.r, self.world, self.look = renderer, world, look
        self.nitro_cols = [linear(rgb(c)) for c in NITROS[nitro % len(NITROS)][1:]]
        self.trail_style = trail
        self.scenery = Scenery(renderer)
        self.particles = Particles(renderer.quality.particles)
        self.model = renderer.car_model(look.vid)
        self.trails = [Trail(), Trail()]
        self.shake, self.warp = CameraShake(), TimeWarp()
        self.time = 0.0
        self.flash, self.flash_col = 0.0, (1., 1., 1.)
        self.aberr = 0.0
        self.glitch = 0.0
        self.desat = 0.0
        self.cam_x = world.player.x
        self.cam_roll = self.cam_yaw = 0.0
        self.fov = 64.0
        self.nitro_vis = 0.0
        self.death_t = 0.0
        self.intro = 0.0              # 1 → 0 : travelling de départ
        self.fx = fx
        self.env_blend = 0.0
        self.view: FrameView | None = None
        self._emit_acc = 0.0
        self.traffic_accents = {}

    # -- événements visuels -------------------------------------------------------------------
    def on_event(self, e):
        P, w = self.particles, self.world
        pl = w.player
        at = (e.x, e.y, e.s)
        if e.kind in ("crash", "bump", "destroyed"):
            k = .35 + .65 * e.power if e.kind != "destroyed" else 1.6
            self.shake.add(.25 + .55 * min(1, k))
            P.emit(34 * k, at, (0, 3, pl.v * .9), (5, 3.5, 7), color=(5, 2.2, .5), color2=(4, 3.4, 2.4), life=(.25, .8), size=(.045, .015), kind=SPARK, gravity=9, stretch=.035)
            P.emit(7 * k, at, (0, 1.2, pl.v * .86), (2, 1, 3), color=(.16, .17, .20), life=(.5, 1.2), size=(.35, 1.5), kind=SMOKE, drag=1.2, alpha=.42)
            P.emit(1, at, (0, 0, pl.v), color=(2.2, 1.0, .4), life=(.10, .16), size=(.7, 1.3), kind=GLOW)
            self.flash, self.flash_col = max(self.flash, .16 * k), (1., .45, .35)
            self.aberr = max(self.aberr, .09 * k)
            if e.kind == "crash" and e.power > .7:
                self.warp.trigger(.42, .22)
                self.glitch = .5
            if e.kind == "destroyed":
                self.warp.trigger(.16, 1.5)
                self.glitch, self.flash = 1.0, .45
                P.emit(90, at, (0, 4, pl.v * .6), (8, 5, 9), color=self.look.light, color2=(4, 2, .6), life=(.5, 1.6), size=(.07, .02), kind=SPARK, gravity=7, stretch=.04)
                P.emit(16, at, (0, 1.6, pl.v * .5), (3, 1.2, 3), color=(.13, .14, .17), life=(1, 2.4), size=(.6, 2.8), kind=SMOKE, drag=.9, alpha=.5)
                P.emit(1, at, (0, 0, pl.v * .6), color=tuple(v * .9 for v in self.look.light), life=(.5, .7), size=(.4, 4.5), kind=RING, alpha=.5)
        elif e.kind == "scrape":
            P.emit(9, (e.x, .55, e.s), (-math.copysign(2.5, e.x), 2, pl.v * .72), (1.4, 1.6, 4), jitter=(.05, .2, 1.2), color=(6, 3, .8), color2=(5, 4, 3), life=(.2, .5), size=(.035, .012), kind=SPARK, gravity=9, stretch=.035)
            self.shake.add(.06)
        elif e.kind == "coin":
            c = (3.2, 2.0, .35)
            P.emit(8, at, (0, 1.5, pl.v * .94), (1.8, 1.8, 1.8), color=c, life=(.25, .5), size=(.13, .02), kind=STAR, drag=1.5)
            P.emit(1, at, (0, .4, pl.v), color=tuple(v * .35 for v in c), life=(.28, .32), size=(.15, .80), kind=RING)
        elif e.kind == "pickup":
            c = tuple(v * 3.2 for v in linear(rgb(PICKUP_COLORS[e.data])))
            P.emit(26, at, (0, 2, pl.v * .95), (3.2, 2.6, 3.2), color=c, color2=(2, 2, 2), life=(.35, .9), size=(.15, .02), kind=STAR, drag=1.4)
            for k in range(3):
                P.emit(1, (pl.x, .4 + .3 * k, e.s), (0, 1.2 + k, pl.v), color=tuple(v * .4 for v in c), life=(.45, .55), size=(.6, 2.6 + k), kind=RING, alpha=.8)
            self.flash, self.flash_col = max(self.flash, .10), tuple(min(1, v / 3) for v in c)
        elif e.kind == "near_miss":
            side = math.copysign(1, e.x - pl.x)
            P.emit(10, (pl.x + side * 1.2, .7, e.s), (side * 2, .6, pl.v * .5), (1, 1, 6), color=(1.2, 2.2, 3), life=(.15, .35), size=(.03, .01), kind=SPARK, stretch=.05)
            self.shake.add(.08)
            if e.power > .72:
                self.warp.trigger(.72, .10)
        elif e.kind == "splash":
            P.emit(26, (e.x, .15, e.s), (0, 3.2, pl.v * .75), (3.2, 2, 4), jitter=(.9, .05, 1.4), color=(.55, .75, 1.0), life=(.35, .8), size=(.06, .03), kind=SPARK, gravity=9, stretch=.02, alpha=.6)
            P.emit(6, (e.x, .3, e.s), (0, 1, pl.v * .7), (2, .6, 3), color=(.30, .36, .46), life=(.4, .9), size=(.4, 1.5), kind=SMOKE, drag=1.2, alpha=.28)
            self.shake.add(.10)
        elif e.kind == "shield_hit":
            c = (.6, 1.6, 4)
            P.emit(30, (pl.x, .7, e.s), (0, 1, pl.v), (5, 3, 5), color=c, color2=(3, 3, 4), life=(.3, .7), size=(.10, .02), kind=STAR, drag=1.2)
            P.emit(2, (pl.x, .7, pl.s), (0, 0, pl.v), color=c, life=(.35, .45), size=(1.5, 4.5), kind=RING)
            self.shake.add(.35)
            self.flash, self.flash_col = .16, (.3, .65, 1.)
        elif e.kind == "nitro_start":
            self.shake.add(.28)
            self.aberr = max(self.aberr, .05)
            self.flash, self.flash_col = max(self.flash, .10), tuple(min(1., v) for v in self.nitro_cols[0])
            for ex in self.model.exhausts:
                P.emit(16, (pl.x + ex[0], ex[1], pl.s + ex[2]), (0, .4, pl.v * .5), (1.6, 1.2, 4), color=tuple(v * 4 for v in self.nitro_cols[0]), color2=tuple(v * 4 for v in self.nitro_cols[1]), life=(.2, .5), size=(.14, .03), kind=GLOW)
        elif e.kind == "environment":
            self.flash, self.flash_col = 1.0, (.75, .95, 1.)
            self.warp.trigger(.55, .35)
            self.glitch = .6
        elif e.kind == "level":
            P.emit(40, (pl.x, .3, pl.s + 1), (0, 3, pl.v), (3, 2.5, 3), color=tuple(v * 3 for v in self.look.light), color2=(3, 3, 3), life=(.5, 1.1), size=(.13, .02), kind=STAR, drag=1)

    # -- mise à jour -----------------------------------------------------------------------------
    def update(self, dt: float, real_dt: float):
        """`dt` est ralenti par les effets de temps ; `real_dt` est le temps réel."""
        w, p = self.world, self.world.player
        self.time += dt
        self.shake.update(real_dt)
        self.flash = max(0.0, self.flash - real_dt * (1.6 if self.flash > .4 else 2.4))
        self.aberr = damp(self.aberr, 0.0, 5, real_dt)
        self.glitch = max(0.0, self.glitch - real_dt * 1.6)
        self.desat = damp(self.desat, 0.0 if p.alive else .55, 1.6, real_dt)
        self.intro = max(0.0, self.intro - real_dt / 2.6)
        self.nitro_vis = damp(self.nitro_vis, 1.0 if p.nitro_on else 0.0, 7, dt)
        self._continuous(dt)
        self.particles.budget = (.35 + .65 * self.fx) * (self.r.quality.particles / 1000) ** .5
        self.particles.update(dt)
        c, s = math.cos(p.yaw), math.sin(p.yaw)
        for tr, tp in zip(self.trails, self.model.tail_points):
            tr.length = 9 + 9 * p.speed_ratio + 10 * self.nitro_vis
            if p.alive:
                tr.push(p.s + tp[2] * c - tp[0] * s, p.x + tp[0] * c + tp[2] * s, tp[1])
        # caméra
        self.cam_x = damp(self.cam_x, p.x * .84, 8.5, dt)
        self.cam_yaw = damp(self.cam_yaw, p.vx * .0052, 5, dt)
        self.cam_roll = damp(self.cam_roll, -p.vx * .0032 - float(w.track.curvature(p.s)) * p.v * p.v * .0028, 4, dt)
        self.fov = damp(self.fov, 62 + 11 * p.speed_ratio ** 1.6 + 8 * self.nitro_vis, 3.5, dt)
        if not p.alive:
            self.death_t += real_dt

    def _continuous(self, dt):
        """Émissions continues : échappement, nitro, fumée, gerbes, étincelles."""
        P, w, p = self.particles, self.world, self.world.player
        self._emit_acc += dt
        n = 0
        while self._emit_acc > 1 / 60:
            self._emit_acc -= 1 / 60
            n += 1
        if not n:
            return
        if p.nitro_on:
            c0, c1 = (tuple(v * 3.4 for v in c) for c in self.nitro_cols)
            for ex in self.model.exhausts:
                pos = (p.x + ex[0] + p.yaw * ex[2], ex[1], p.s + ex[2])
                P.emit(3 * n, pos, (0, .15, p.v - 13), (.35, .35, 3), jitter=(.03, .03, .2), color=c0, color2=c1, life=(.08, .22), size=(.13, .03), kind=GLOW, stretch=.022)
                P.emit(.5 * n, pos, (0, .6, p.v - 22), (1.3, 1.0, 5), color=c1, color2=c0, life=(.25, .5), size=(.05, .01), kind=SPARK, stretch=.03)
        wet = w.env.wet > .5
        if p.alive and p.v > 20:
            rear = [x for x in self.model.wheels if not x[3]]
            if wet:
                k = p.v / 60
                for x in rear:
                    P.emit(.55 * n * k, (p.x + x[0], .15, p.s + x[2] - .3), (0, 1.5, p.v * .70), (.7, .7, 3), color=(.30, .36, .48), life=(.25, .55), size=(.14, .85), kind=SMOKE, drag=1.1, alpha=.16)
            slide = clamp((abs(p.vx) - 8.5) / 5) + clamp(p.brake - .4) + (1 if p.slip > 0 else 0)
            if slide > .05 and not wet:
                for x in rear:
                    P.emit(.8 * n * slide, (p.x + x[0], .12, p.s + x[2]), (0, .7, p.v * .55), (.5, .4, 2), color=(.34, .35, .38), life=(.35, .8), size=(.18, .95), kind=SMOKE, drag=1.4, alpha=.24)
        if p.hp < 38 and p.alive:
            k = 1 - p.hp / 38
            P.emit((.3 + .6 * k) * n, (p.x, .95, p.s + 1.5), (0, 1.5, p.v * .75), (.5, .3, 1.5), color=(.07, .07, .09), life=(.5, 1.0), size=(.2, 1.1), kind=SMOKE, drag=.8, alpha=.30 + .25 * k)
            if k > .5:
                P.emit(.5 * n, (p.x, .8, p.s + 1.4), (0, 2, p.v * .9), (1.5, 1, 2), color=(5, 2.2, .5), life=(.2, .5), size=(.03, .01), kind=SPARK, gravity=7, stretch=.03)
        if not p.alive:
            P.emit(1.2 * n, (p.x, .9, p.s + 1), (0, 2.2, p.v * .5), (.8, .4, .8), color=(.06, .06, .08), life=(.8, 1.8), size=(.4, 2.2), kind=SMOKE, drag=.6, alpha=.5)
            P.emit(1.0 * n, (p.x, .8, p.s + 1), (0, 1.4, p.v * .7), (.7, .6, .7), color=(3.2, 1.2, .25), life=(.2, .5), size=(.35, .05), kind=GLOW)
        for v in w.vehicles:
            z = v.s - p.s
            if v.stalled and -10 < z < 110:
                P.emit(.35 * n, (v.x, 1.0, v.s + v.length * .3), (.3, 1.4, 0), (.3, .3, .3), color=(.20, .21, .24), life=(.9, 1.8), size=(.25, 1.6), kind=SMOKE, alpha=.30)
            elif v.hit > 0 and abs(z) < 60:
                P.emit(1.2 * n, (v.x, .2, v.s), (0, .8, v.v * .6), (1, .4, 2), color=(.30, .31, .34), life=(.35, .8), size=(.25, 1.2), kind=SMOKE, drag=1.2, alpha=.28)
            elif wet and v.v > 15 and -5 < z < 70:
                P.emit(.30 * n, (v.x, .25, v.rear), (0, 1.2, v.v * .6), (.8, .4, 2), color=(.28, .33, .44), life=(.3, .6), size=(.3, 1.2), kind=SMOKE, drag=1.1, alpha=.12)
        if p.active("shield") and p.alive:
            P.emit(.5 * n, (p.x, .7, p.s), (0, .8, p.v), (.6, .6, .6), jitter=(1.3, .7, 2.4), color=(.5, 1.4, 3.2), life=(.3, .6), size=(.07, .01), kind=STAR)
        if p.active("magnet") and p.alive:
            P.emit(.5 * n, (p.x, .6, p.s + 3), (0, .4, p.v - 5), (.4, .5, 1), jitter=(2.2, .7, 2.5), color=(3, .4, .9), life=(.25, .5), size=(.07, .01), kind=STAR)

    # -- rendu ---------------------------------------------------------------------------------------
    def build(self, cam_override=None) -> tuple:
        """Remplit la file du moteur et retourne tout ce qu'il faut pour `render`."""
        w, p, r = self.world, self.world.player, self.r
        env = w.env
        lag = w.acc if p.alive or p.v > .5 else 0.0
        s0 = p.s + p.v * lag                       # extrapolation : mouvement parfaitement fluide
        px = p.x + p.vx * lag * .8
        far = r.quality.far
        bend = w.track.bend_table(s0)
        t = self.time
        decals: list = []
        glows: list = []
        lights: list = []
        day = DAY.get(env.index, 1.0)
        night = w.mode.night
        glow_k = lerp(day, 1.0, night)
        yaw = p.yaw + p.spinout
        bob = math.sin(t * 31) * .004 * p.speed_ratio
        draw_player(r, self.look, (px, bob, 0.0), yaw, p.pitch, p.roll, p.spin, p.steer_vis, p.brake, p.flash * .7 * (math.sin(t * 60) * .5 + .5), 1.0, decals,
                    glow_k * (.85 + .5 * self.nitro_vis))
        c, sn = math.cos(yaw), math.sin(yaw)

        def local(q):
            return px + q[0] * c + q[2] * sn, q[1], -q[0] * sn + q[2] * c

        for tp in self.model.tail_points:
            x, y, z = local(tp)
            k = .20 + .5 * p.brake
            glows.append([x, y, z - .05, .30 + .22 * p.brake, 3 * k, .12 * k, .25 * k, .8, 0, 0, 0, GLOW])
        if self.nitro_vis > .02:
            for ex in self.model.exhausts:
                x, y, z = local(ex)
                fl = .75 + .25 * math.sin(t * 73 + ex[0] * 9)
                n = self.nitro_vis * fl
                a, b = self.nitro_cols
                glows.append([x, y, z - .75 * n, .13, *(v * 3.6 for v in b), n, 0, 0, 1.9 * n, SPARK])
                glows.append([x, y, z - .35 * n, .10, *(v * 4.0 + .6 for v in a), n, 0, 0, .9 * n, SPARK])
                glows.append([x, y, z - .1, .42 * n, *(v * 1.6 for v in a), .8, 0, 0, 0, GLOW])
                glows.append([x, y, z - .2, 1.0 * n, *(v * .5 for v in b), .7, 0, 0, 0, GLOW])
            decals.append([px, -3.6, 1.7, 2.6, *(v * 1.3 * self.nitro_vis for v in self.nitro_cols[1]), 0, 6, 0])
        if p.active("shield") and p.alive:
            tl = p.timers["shield"]
            k = (.22 + .07 * math.sin(t * 6)) * (1 if tl > 2 else .5 + .5 * math.sin(t * 18))
            glows.append([px, .68, 0, 1.95, .25 * k, .75 * k, 2.0 * k, .65, 0, 0, 0, RING])
            decals.append([px, 0, 2.2, 3.4, .12 * k, .45 * k, 1.1 * k, 0, 4, 0])
        # circulation
        for v in w.vehicles:
            z = v.s + v.v * lag - s0
            if z < -24 or z > far:
                continue
            x = v.x + v.vx * lag
            paint = linear(rgb(v.paint))
            hazard = v.blink == 2.0 and math.sin(t * 9 + v.seed * 6) > 0
            flash = .55 if v.cooldown > .7 else 0.0
            draw_traffic(r, v.kind, (x, 0, z), v.yaw, v.roll, v.spin, paint, v.accent, v.brake if not hazard else 1.0, v.seed, decals, z < 130, day == 1.0 or night > 0, flash)
            m = r.traffic_model(v.kind)
            cy, sy = math.cos(v.yaw), math.sin(v.yaw)
            if z < 240:
                for q in m.tails:
                    gx, gz = x + q[0] * cy + q[2] * sy, z - q[0] * sy + q[2] * cy
                    k = (.28 + .75 * v.brake) * glow_k
                    glows.append([gx, q[1], gz - .06, .34 + .25 * v.brake + z * .0022, 2.6 * k, .10 * k, .20 * k, .8, 0, 0, 0, GLOW])
                    if hazard or (abs(v.blink) == 1.0 and math.copysign(1, q[0]) == v.blink and math.sin(t * 11) > 0):
                        glows.append([gx, q[1] + .12, gz - .08, .42 + z * .003, 2.6, 1.15, .08, .9, 0, 0, 0, GLOW])
                if glow_k > .5:
                    decals.append([x, z - v.length / 2 - 2.6, v.width * .6, 3.2 + v.v * .05, .26 * glow_k, .012, .03, 0, 3, 0])
            if -5 < z < 90:
                lights.append((x, z - v.length / 2 - .6, (.8 + 1.2 * v.brake) * glow_k, 0.0))
        lights.sort(key=lambda l: l[1])
        # obstacles
        rows: dict[str, list] = {}
        for o in w.obstacles:
            z = o.s - s0
            if z < -14 or z > far:
                continue
            if o.kind == "puddle":
                decals.append([o.x, z, 1.5, 2.8, .10, .30, .50, .2 + o.seed * .7, 2, o.seed * .6])
                continue
            if o.fly:
                rows.setdefault(o.kind, []).append(row((o.x, o.y, z), o.rot * .5, o.rot, o.rot * .3, c1=(1.5, .55, .05), c2=(.9, .35, .02), seed=o.seed))
                continue
            rows.setdefault(o.kind, []).append(row((o.x, 0, z), (o.seed - .5) * .12 if o.kind != "debris" else o.seed * 6, c1=(1.5, .55, .05) if o.kind != "barrier" else (1.6, .5, .05), c2=(.85, .33, .02), seed=o.seed))
            if o.kind in ("barrier", "roadworks"):
                decals.append([o.x, z, 2.0, 1.1, 0, 0, 0, .6, 0, 0])
                if z > 0:
                    decals.append([o.x, z - 6.0, 1.55, 4.6, 0, 0, 0, 0, 5, 0])
                bl = .5 + .5 * math.sin(t * 7 + o.seed * 40)
                y = 1.05 if o.kind == "barrier" else 1.95
                glows.append([o.x, y, z - .3, 1.0 + .4 * bl, 1.5 * bl, .6 * bl, .05, .55, 0, 0, 0, GLOW])
            elif o.kind == "debris":
                decals.append([o.x, z, 1.1, .9, 0, 0, 0, .5, 0, 0])
                glows.append([o.x, .25, z, .55, .9, .35, .05, .5, 0, 0, 0, GLOW])
        for k, v in rows.items():
            r.queue(k, v)
        # pièces et bonus
        cr, cr5 = [], []
        for q in w.coins:
            z = q.s - s0
            if -8 < z < 230:
                y = q.y + .07 * math.sin(t * 3 + q.phase)
                (cr5 if q.value > 1 else cr).append(row((q.x, y, z), t * 2.6 + q.phase, 0, 0, (1.25,) * 3 if q.value > 1 else (1, 1, 1), c1=GOLD if q.value == 1 else (.42, .14, .95), c2=(1, .7, .1)))
                if z < 110:
                    g = (1.3, .72, .10) if q.value == 1 else (.8, .30, 1.8)
                    glows.append([q.x, y, z, .62, *(v * .42 for v in g), .7, 0, 0, 0, GLOW])
                    decals.append([q.x, z, .62, .62, *(v * .16 for v in g), 0, 6, 0])
        r.queue("coin", cr + cr5)
        pk: dict[str, list] = {}
        for k in w.pickups:
            z = k.s - s0
            if -8 < z < 300:
                col = linear(rgb(PICKUP_COLORS[k.kind]))
                pulse = 1 + .06 * math.sin(t * 5 + k.phase)
                pk.setdefault("pk_" + k.kind, []).append(row((k.x, .12 + .08 * math.sin(t * 2.4 + k.phase), z), t * 1.5 + k.phase, 0, 0, (1.25 * pulse,) * 3, c1=tuple(v * 1.1 + .05 for v in col), c2=col))
                glows.append([k.x, .9, z, 1.7, *(v * .6 for v in col), .7, 0, 0, 0, GLOW])
                glows.append([k.x, 5.0, z, .12, *(v * .8 for v in col), .55 * clamp((z - 6) / 14), 0, 9.0, 0, SPARK])
                decals.append([k.x, z, 1.5, 1.5, *(v * .55 for v in col), 0, 4, 0])
        for k, v in pk.items():
            r.queue(k, v)
        # portail d'univers
        if not w.fixed_env:
            z = w.portal_s - s0
            if z < far:
                nx = w.next_env
                r.queue("portal", [row((0, 0, z), 0, c1=tuple(v * 1.3 for v in nx.edge), c2=nx.edge2, seed=.5)])
                for k in range(10):
                    a = math.pi * (k + .5) / 10
                    glows.append([9.4 * math.cos(a), 8.7 * math.sin(a), z, 2.6, *(v * .5 for v in nx.edge), .6, 0, 0, 0, GLOW])
        self.scenery.queue(env, s0, t)

        # particules
        add, smoke = self.particles.instances(s0, p.v)
        g = np.array(glows, "f4") if glows else np.zeros((0, 12), "f4")
        if add is not None and len(add):
            g = np.concatenate([g, add])
        ribbons = []
        if p.alive and p.speed_ratio > .12:
            width = .07 if self.trail_style != 1 else .045
            for i, (tr, tp) in enumerate(zip(self.trails, self.model.tail_points)):
                x, y, z = local(tp)
                power = (.30 + .55 * p.speed_ratio + .6 * self.nitro_vis) * (.55 + .45 * glow_k)
                col = np.array((1.6, .06, .16)) * (1 - self.nitro_vis) + np.array(self.look.light) * 2.2 * self.nitro_vis if self.trail_style == 0 else np.array(self.look.light) * 1.8
                rb = tr.ribbon((s0 + z, x, y), s0, col, width, self.trail_style, t, power)
                if rb is not None:
                    ribbons.append(rb)
                if self.trail_style == 1:
                    rb2 = tr.ribbon((s0 + z, x, y), s0, np.array(self.look.light) * 1.1, width * .8, 0, t, power * .7)
                    if rb2 is not None:
                        rb2[:, 1] -= .22
                        ribbons.append(rb2)

        # caméra
        ratio = p.speed_ratio
        dx, dy, rl = self.shake.sample(ratio * self.fx)
        dist = 6.1 + .55 * ratio - .5 * self.nitro_vis
        cam = [self.cam_x + dx, 2.55 + .12 * ratio + dy, -dist]
        cyaw, cpitch, croll = self.cam_yaw, -.128, self.cam_roll + rl
        fov = self.fov
        if cam_override is not None:
            cam, (cyaw, cpitch), croll, fov = cam_override(px, t)
        elif not p.alive:
            k = smooth(self.death_t / 3.2)
            a = k * 2.2
            rad = dist + .6 * k
            tgt = (px, .6, 0)
            orbit = [px + math.sin(a) * rad, lerp(cam[1], 1.5, k), -math.cos(a) * rad]
            cam = [lerp(cam[i], orbit[i], min(1, k * 2)) + (dx, dy, 0)[i] for i in range(3)]
            yw, pt = look_angles(cam, tgt)
            cyaw, cpitch = lerp(cyaw, yw, min(1, k * 2)), lerp(cpitch, pt, min(1, k * 2))
            fov = lerp(fov, 48, k)
        elif self.intro > 0:
            k = smooth(1 - self.intro)
            a = lerp(2.5, 0.0, k)
            rad = lerp(5.6, dist, k)
            o = [px + math.sin(a) * rad, lerp(.95, cam[1], k), -math.cos(a) * rad]
            yw, pt = look_angles(o, (px, .7, 0))
            m = smooth(clamp(k * 1.6 - .6))
            cam = [lerp(o[i], cam[i], m) for i in range(3)]
            cyaw, cpitch = lerp(yw, cyaw, m), lerp(pt, cpitch, m)
            fov = lerp(48, fov, k)
        ox, oy = w.track.offset(cam[2])
        cam = (cam[0] + ox, max(.35, cam[1]) + oy, cam[2])
        hour = (.5 + .5 * math.sin(s0 / 2600.)) if env.index == 3 else .3
        sun = None
        if env.index == 3:
            warm = abs(hour - .5) * 2
            sun = (1.45 + .25 * warm, 1.12 - .30 * warm, .85 - .40 * warm)
        self.view = FrameView(
            env=env, time=t, s=s0, speed=p.v, cam=cam, yaw=cyaw, pitch=cpitch, roll=croll, fov=fov, slope=w.track.slope(s0),
            curvature=float(w.track.curvature(s0)), sky_yaw=w.sky_yaw, hour=hour, sun_col=sun, night=night, player_x=px, head_z=self.model.hl - .1,
            headlights=1.0 if p.alive else .25, accent=self.look.light, nitro=self.nitro_vis,
            speed_lines=clamp((ratio - .48) * 1.5) * self.fx + .5 * self.nitro_vis * self.fx, rain=env.rain, dust=env.dust * (.4 + .6 * self.fx), lights=lights[:8],
            blur=clamp((ratio - .55) * .9) * .55 + .42 * self.nitro_vis, aberration=self.aberr + .004 * self.nitro_vis, vignette=.55 + .25 * night,
            flash=self.flash, flash_col=self.flash_col, desat=self.desat + (.10 if p.active("slow") else 0), glitch=self.glitch, drops=.9 if env.rain else 0.0,
            tint=(.90, .93, 1.12) if p.active("slow") else (1.0, 1.0, 1.0), center=(.5, .56))
        return self.view, bend, decals, g, smoke, ribbons

    def render(self, cam_override=None, **post):
        v, bend, decals, add, smoke, ribbons = self.build(cam_override)
        for k, val in post.items():
            setattr(v, k, val)
        self.r.render(v, bend, decals=decals, particles=add, smoke=smoke, ribbons=ribbons)


STUDIO = ENVIRONMENTS[5]
