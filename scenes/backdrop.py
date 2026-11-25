"""Fond 3D vivant des menus : la voiture du joueur roule seule dans Neon City."""
from __future__ import annotations

import dataclasses
import math

from config.environments import PLAYABLE
from config.modes import MODES
from engine.mathx import damp, look_angles
from engine.world_view import WorldView
from entities.autopilot import Autopilot
from entities.world import World

ATTRACT = dataclasses.replace(MODES[0], id="attract", traffic_rate=.45, obstacle_rate=.22, damage=0.0, lethal=False)

# cadrages : (position relative, cible, champ)
SHOTS = {
    "menu": ((-3.6, 1.10, -5.4), (-1.15, 1.0, 1.6), 52.0),
    "wide": ((-1.4, 4.2, -10.5), (0.0, 1.6, 18.0), 56.0),
    "low": ((2.6, .75, -4.2), (.3, .9, 6.0), 54.0),
    "side": ((-4.6, 1.5, -2.6), (.8, .8, 5.0), 52.0),
}


class Backdrop:
    def __init__(self, app):
        self.app = app
        self.shot = "menu"
        self.cam = [list(SHOTS["menu"][0]), list(SHOTS["menu"][1]), SHOTS["menu"][2]]
        self.reload()

    def reload(self):
        app = self.app
        spec = app.vehicle
        m = app.renderer.car_model(spec.id)
        cust = app.custom(spec.id)
        self.key = (spec.id, tuple(sorted(cust.items())), app.renderer.quality.name)
        self.world = World(spec, ATTRACT, PLAYABLE[0], 11, (m.W, m.L))
        self.world.player.s = 900.0
        self.world.player.v = 40.0
        self.world.spawner.next_obstacle = 1300.0
        self.world.spawner.next_coins = self.world.spawner.next_pickup = 1e9
        self.view = WorldView(app.renderer, self.world, app.look(spec.id), cust["nitro"], cust["trail"], app.settings["effects"])
        self.pilot = Autopilot(.35)

    def set_shot(self, name):
        self.shot = name

    def update(self, dt):
        app = self.app
        cust = app.custom(app.vehicle.id)
        if self.key != (app.vehicle.id, tuple(sorted(cust.items())), app.renderer.quality.name):
            self.reload()
        w = self.world
        c = self.pilot.control(w, dt)
        w.update(dt, c)
        for e in w.drain_events():
            if e.kind not in ("environment",):
                self.view.on_event(e)
        self.view.shake.trauma *= .5
        self.view.fx = app.settings["effects"]
        self.view.update(dt, dt)
        tgt = SHOTS[self.shot]
        for k in (0, 1):
            for i in range(3):
                self.cam[k][i] = damp(self.cam[k][i], tgt[k][i], 2.2, dt)
        self.cam[2] = damp(self.cam[2], tgt[2], 2.2, dt)

    def draw(self, fade=1.0, flash=0.0, vignette=.95):
        def cam(px, t):
            p, q, fov = self.cam
            pos = (px + p[0] + .35 * math.sin(t * .23), p[1] + .12 * math.sin(t * .31 + 1), p[2] + .4 * math.sin(t * .17))
            yaw, pitch = look_angles(pos, (px + q[0] + .2 * math.sin(t * .19), q[1], q[2]))
            return list(pos), (yaw, pitch), -.02 + .012 * math.sin(t * .27), fov
        self.view.render(cam, fade=fade, flash=flash, vignette=vignette, speed_lines=.15, blur=.0, desat=0.0, tint=(.96, .98, 1.06))


def get(app) -> Backdrop:
    if not hasattr(app, "backdrop"):
        app.backdrop = Backdrop(app)
    return app.backdrop
