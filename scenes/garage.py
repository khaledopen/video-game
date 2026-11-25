"""Garage : plateau tournant 3D, achat et personnalisation des véhicules."""
from __future__ import annotations

import math

import numpy as np
import pygame

from config.environments import ENVIRONMENTS
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, hexc, linear, mix, rgb
from config.vehicles import BY_ID, LIGHTS, NITROS, PAINTS, RIMS, TRAILS, VEHICLES
from core.progression import check_achievements
from core.scene_manager import Scene
from effects.animation import ease_back, ease_out
from effects.particles import GLOW, SPARK, STAR, Particles
from engine.mathx import clamp, damp, look_angles
from engine.renderer import FrameView
from engine.vehicle_draw import Look, draw_player
from scenes.menu import start_game
from ui import icons
from ui.hud import fmt
from ui.widgets import Button, Group, IconButton, Widget, chip, header

FLAT = np.zeros((320, 2), "f4")
TABS = (("paint", "COULEUR", "paint"), ("rim", "JANTES", "rim"), ("light", "ÉCLAIRAGE", "light"), ("nitro", "NITRO", "flame"), ("trail", "TRAÎNÉE", "trail"))
STATS = (("VITESSE MAX", lambda s: s.top_speed / 360, lambda s: f"{s.top_speed:.0f} km/h", CYAN), ("ACCÉLÉRATION", lambda s: s.accel / 10, lambda s: f"{s.accel:.1f}", VIOLET),
         ("MANIABILITÉ", lambda s: s.handling / 10, lambda s: f"{s.handling:.1f}", GREEN), ("RÉSISTANCE", lambda s: s.armor / 10, lambda s: f"{s.armor:.1f}", GOLD),
         ("NITRO", lambda s: s.nitro / 10, lambda s: f"{s.nitro:.1f}", RED))


class Swatch(Widget):
    """Pastille de personnalisation."""

    def __init__(self, scene, kind, value, label, colors, icon=""):
        super().__init__(w=64, h=64)
        self.scene, self.kind, self.value, self.label, self.colors, self.icon = scene, kind, value, label, colors, icon

    def click(self, app, mx, my):
        app.audio.play("ui_click", .7)
        self.scene.set_custom(self.kind, self.value)
        return True

    def draw(self, c, t):
        sel = self.scene.custom[self.kind] == self.value
        h = clamp(self.hover.v)
        x, y, r = self.x + 32, self.y + 32, 25 + 3 * h
        c.alpha *= self.appear
        if sel or h > .05:
            c.circle(x, y, r + 7, (0, 0, 0, 0), 2.2, alpha(WHITE if sel else CYAN, .95 if sel else h), 10)
        if self.icon:
            c.circle(x, y, r, (.05, .08, .16, .95), 1.4, alpha(CYAN, .5))
            icons.draw(c, self.icon, x, y, 32, WHITE)
        else:
            a, b = self.colors
            c._add(x - r, y - r, 2 * r, 2 * r, 0, mix(a, WHITE, .18), b, alpha(WHITE, .35), (r * c.k, 1.5 * c.k, 0, 2.0))
        c.alpha /= max(self.appear, 1e-3)


class Thumb(Widget):
    """Vignette d'un véhicule dans le bandeau inférieur."""

    def __init__(self, scene, index, spec):
        super().__init__(w=176, h=84)
        self.scene, self.index, self.spec = scene, index, spec

    def click(self, app, mx, my):
        self.scene.show(self.index)
        return True

    def draw(self, c, t):
        s = self.scene
        sel = s.index == self.index
        owned = self.spec.id in s.owned
        h = clamp(self.hover.v)
        col = hexc(self.spec.accent)
        c.alpha *= self.appear
        c.panel(self.x, self.y - 6 * h, self.w, self.h, mix((.03, .05, .105, .82), (*col[:3], .7), .06 + .12 * h + (.22 if sel else 0)), None, 14, 1.4 + sel, alpha(col if owned else MUTED, .22 + .4 * h + (.6 if sel else 0)), 16 * max(h, float(sel)), 1, -.12)
        cx, cy = self.x + self.w / 2, self.y - 6 * h
        c.text(cx, cy + 30, self.spec.name, 20, WHITE if owned else (.62, .70, .82, 1), align="c", max_w=self.w - 30)
        if not owned:
            w = c.measure(fmt(self.spec.price), 18)
            icons.draw(c, "lock", cx - w / 2 - 14, cy + 59, 20, GOLD)
            c.text(cx + 4, cy + 59, fmt(self.spec.price), 18, GOLD, align="c")
        else:
            sel_v = s.app.settings["vehicle"] == self.spec.id
            c.text(cx, cy + 59, "SÉLECTIONNÉ" if sel_v else "POSSÉDÉ", 14, GREEN if sel_v else MUTED, "text", "c", spacing=1)
        c.alpha /= max(self.appear, 1e-3)


class GarageScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.owned = app.store.unlocked()
        self.coins = app.store.coins
        self.index = next(i for i, v in enumerate(VEHICLES) if v.id == app.vehicle.id)
        self.yaw = 2.5
        self.yaw_v = .28
        self.pitch = 0.0
        self.zoom = 0.0
        self.grab = None
        self.swap = 1.0
        self.prev_index = self.index
        self.bars = [0.0] * 5
        self.msg, self.msg_t, self.msg_col = "", 9.0, WHITE
        self.tab = 0
        self.particles = Particles(400, 5)
        self.custom = app.custom(self.spec.id)
        self.paint_vis = list(linear(rgb(self.custom["paint"])))
        self.light_vis = list(linear(rgb(self.custom["light"])))
        self.demo = 0.0
        self.unlock_fx = 0.0
        self.thumbs = [Thumb(self, i, v) for i, v in enumerate(VEHICLES)]
        self.prev_btn = IconButton("arrow", lambda: self.show(self.index - 1), size=66, rot=math.pi)
        self.next_btn = IconButton("arrow", lambda: self.show(self.index + 1), size=66)
        self.action = Button("", self.act, w=400, h=74, size=26, primary=True)
        self.drive = Button("CONDUIRE", lambda: start_game(app), icon="play", color=GREEN, w=300, h=62)
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=230, sound="ui_back")
        self.tabs = [IconButton(ic, lambda i=i: self.set_tab(i), size=62, color=VIOLET) for i, (_, _, ic) in enumerate(TABS)]
        self.group = Group(app)
        self._rebuild()

    @property
    def spec(self):
        return VEHICLES[self.index]

    def enter(self):
        super().enter()
        self.app.audio.ambience("")

    def resized(self):
        self._rebuild()

    def _rebuild(self):
        c = self.app.canvas
        n = len(self.thumbs)
        tw = min(190., (c.W - 2 * 330 - 12 * (n - 1)) / n) if c.W < 2100 else 190.
        tw = max(tw, 146.)
        x0 = c.W / 2 - (n * tw + (n - 1) * 12) / 2
        for i, w in enumerate(self.thumbs):
            w.w, w.x, w.y = tw, x0 + i * (tw + 12), c.H - 116
        self.prev_btn.x, self.prev_btn.y = c.W / 2 - 440, c.H * .42
        self.next_btn.x, self.next_btn.y = c.W / 2 + 374, c.H * .42
        self.action.x, self.action.y = 90, c.H - 238
        self.drive.x, self.drive.y = c.W - 90 - 300, c.H - 226
        self.back_btn.x, self.back_btn.y = c.W - 90 - 230, 60
        px = c.W - 90 - 380
        for i, b in enumerate(self.tabs):
            b.x, b.y = px + i * 79, 206
        kind = TABS[self.tab][0]
        if kind == "paint":
            items = [(code, name, (hexc(code), mix(hexc(code), (0, 0, 0, 1), .55)), "") for name, code in PAINTS]
        elif kind == "light":
            items = [(code, name, (hexc(code), mix(hexc(code), (0, 0, 0, 1), .35)), "") for name, code in LIGHTS]
        elif kind == "rim":
            items = [(i, n, None, "rim") for i, n in enumerate(RIMS)]
        elif kind == "nitro":
            items = [(i, n, (hexc(a), hexc(b)), "") for i, (n, a, b) in enumerate(NITROS)]
        else:
            items = [(i, n, None, "trail") for i, n in enumerate(TRAILS)]
        owned = self.spec.id in self.owned
        self.swatches = [Swatch(self, kind, v, lab, col, ic) for v, lab, col, ic in items] if owned else []
        for i, s in enumerate(self.swatches):
            s.x, s.y = px + (i % 5) * 79, 330 + (i // 5) * 76
        for b in self.tabs:
            b.visible = owned
        self._action_label()
        self.group.widgets = [self.prev_btn, self.next_btn, self.action, self.drive, self.back_btn, *(self.tabs if owned else []), *self.swatches, *self.thumbs]
        if self.group.focus not in self.group.widgets:
            self.group.set_focus(None, False)

    def _action_label(self):
        s, a = self.spec, self.action
        if s.id not in self.owned:
            a.label, a.icon, a.color, a.enabled = f"DÉBLOQUER  {fmt(s.price)}", "lock", GOLD, self.coins >= s.price
            a.sub = "" if a.enabled else f"Il manque {fmt(s.price - self.coins)} pièces"
        elif self.app.settings["vehicle"] == s.id:
            a.label, a.icon, a.color, a.enabled, a.sub = "SÉLECTIONNÉ", "check", GREEN, True, ""
        else:
            a.label, a.icon, a.color, a.enabled, a.sub = "SÉLECTIONNER", "car", CYAN, True, ""

    # -- actions -----------------------------------------------------------------------
    def show(self, i):
        i %= len(VEHICLES)
        if i == self.index:
            return
        self.app.audio.play("ui_click", .7)
        self.prev_index, self.index, self.swap = self.index, i, 0.0
        self.custom = self.app.custom(self.spec.id)
        self._rebuild()

    def set_tab(self, i):
        self.tab = i
        self._rebuild()

    def set_custom(self, kind, value):
        self.custom[kind] = value
        self.app.store.set_custom(self.spec.id, self.custom)
        if kind in ("nitro", "trail"):
            self.demo = 1.6
            self.app.audio.play("nitro_start", .4)

    def act(self):
        app, s = self.app, self.spec
        if s.id not in self.owned:
            if app.store.buy(s.id, s.price):
                self.owned, self.coins = app.store.unlocked(), app.store.coins
                app.settings["vehicle"] = s.id
                app.settings.save()
                app.audio.play("ui_unlock", .9)
                self.unlock_fx = 1.0
                for k in range(3):
                    self.particles.emit(60, (0, .6, 0), (0, 2.5, 0), (4, 2.5, 4), jitter=(1, .3, 2), color=tuple(v * 3 for v in self.light_vis), color2=(3, 2.4, 1), life=(.6, 1.6), size=(.10, .02), kind=STAR, gravity=1.5, drag=.8)
                self.say("VÉHICULE DÉBLOQUÉ !", GREEN)
                ach = check_achievements(app.store)
                if ach:
                    self.coins = app.store.coins
                    self.say(f"SUCCÈS : {ach[0].name}  +{ach[0].reward}", GOLD)
                self.custom = app.custom(s.id)
                self._rebuild()
        elif app.settings["vehicle"] != s.id:
            app.settings["vehicle"] = s.id
            app.settings.save()
            self.say(f"{s.name} SÉLECTIONNÉE", CYAN)
            self._action_label()

    def say(self, text, color):
        self.msg, self.msg_t, self.msg_col = text, 0.0, color

    def back(self):
        self.app.scenes.go("menu")

    def event(self, e):
        c = self.app.canvas
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.app.audio.play("ui_back", .7)
                return self.back()
            if e.key in (pygame.K_LEFT, pygame.K_RIGHT) and not (self.group.focus and self.group.focus in self.swatches + self.tabs):
                return self.show(self.index + (1 if e.key == pygame.K_RIGHT else -1))
            if e.key == pygame.K_RETURN and self.group.focus is None:
                return self.action.click(self.app, 0, 0)
        if self.group.event(e):
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.grab = c.to_virtual(e.pos)
        elif e.type == pygame.MOUSEMOTION and self.grab:
            m = c.to_virtual(e.pos)
            self.yaw_v = -(m[0] - self.grab[0]) * .22
            self.yaw -= (m[0] - self.grab[0]) * .006
            self.pitch = clamp(self.pitch + (m[1] - self.grab[1]) * .002, -.25, .9)
            self.grab = m
        elif e.type == pygame.MOUSEBUTTONUP:
            self.grab = None
        elif e.type == pygame.MOUSEWHEEL:
            self.zoom = clamp(self.zoom + e.y * .12, -.5, 1.0)

    def update(self, dt):
        super().update(dt)
        if not self.grab:
            self.yaw_v = damp(self.yaw_v, .28, 1.6, dt)
            self.yaw += self.yaw_v * dt
        self.swap = min(1.0, self.swap + dt / .55)
        self.unlock_fx = max(0.0, self.unlock_fx - dt * .7)
        self.demo = max(0.0, self.demo - dt)
        self.msg_t += dt
        for i, (_, f, _, _) in enumerate(STATS):
            self.bars[i] = damp(self.bars[i], f(self.spec), 7, dt)
        p, li = linear(rgb(self.custom["paint"])), linear(rgb(self.custom["light"]))
        for i in range(3):
            self.paint_vis[i] = damp(self.paint_vis[i], p[i], 9, dt)
            self.light_vis[i] = damp(self.light_vis[i], li[i], 9, dt)
        if self.demo > 0:
            m = self.app.renderer.car_model(self.spec.id)
            n0, n1 = (tuple(v * 3 for v in linear(rgb(x))) for x in NITROS[self.custom["nitro"] % len(NITROS)][1:])
            cs, sn = math.cos(self.yaw), math.sin(self.yaw)
            for ex in m.exhausts:
                pos = (ex[0] * cs + ex[2] * sn, ex[1], -ex[0] * sn + ex[2] * cs)
                d = (-sn * 7, .1, -cs * 7)
                self.particles.emit(5, pos, d, (.3, .3, .3), color=n0, color2=n1, life=(.10, .28), size=(.13, .02), kind=GLOW, stretch=.03)
                self.particles.emit(.6, pos, d, (1, 1, 1), color=n1, life=(.2, .5), size=(.04, .01), kind=SPARK, stretch=.03)
        if np.random.random() < dt * 14:
            a = np.random.random() * 6.28
            self.particles.emit(1, (math.cos(a) * 3.4, .05, math.sin(a) * 3.4), (0, .5, 0), (.1, .2, .1), color=tuple(v * 1.4 for v in self.light_vis), life=(1.2, 2.4), size=(.05, .01), kind=GLOW)
        self.particles.update(dt)
        self.group.reveal(self.t, .025, .45, (0, 30), .2)
        self.group.update(dt)
        for i, b in enumerate(self.tabs):
            b.selected = i == self.tab

    def draw(self, c):
        r, t = self.app.renderer, self.t
        decals: list = []
        k = ease_out(self.swap)
        owned = self.spec.id in self.owned
        look = Look(self.spec.id, self.custom["paint"], self.custom["light"], self.custom["rim"] % 4)
        look.paint, look.light = tuple(self.paint_vis), tuple(self.light_vis)
        if not owned:
            look.paint = tuple(v * .75 for v in look.paint)
        rise = (1 - ease_back(self.swap)) * .5
        draw_player(r, look, (0, rise, 0), self.yaw + (1 - k) * 2.4, steer=.38 * math.sin(t * .7), spin=t * (8 if self.demo else .0), decals=decals,
                    brake=.5 + .5 * math.sin(t * 1.3) if t % 6 < 3 else 0, flash=0.0, lights=1.0, glow=.9 + .4 * self.unlock_fx)
        ang = math.sin(t * .13) * .10
        dist = 6.9 - 1.6 * self.zoom
        h = 1.30 + 2.6 * max(0, self.pitch) - .5 * min(0, self.pitch)
        cam = (math.sin(ang) * dist + .0, h, -math.cos(ang) * dist)
        yaw, pitch = look_angles(cam, (0.0, .34, 0))
        v = FrameView(env=ENVIRONMENTS[5], time=t, cam=cam, yaw=yaw, pitch=pitch, fov=40, studio=True, accent=tuple(self.light_vis), headlights=0., vignette=.8,
                      flash=.5 * max(0, self.unlock_fx - .75) * 4, flash_col=(1, .95, .8), bloom=.85, aberration=.006)
        add, smoke = self.particles.instances(0.0)
        r.render(v, FLAT, decals=decals, particles=add, smoke=smoke)
        W, H = c.W, c.H
        c.rect(0, 0, 620, H, (.008, .014, .034, .78), (.008, .014, .034, 0), True)
        c.rect(W - 620, 0, 620, H, (.008, .014, .034, 0), (.008, .014, .034, .78), True)
        c.rect(0, H - 220, W, 220, (.008, .012, .03, 0), (.008, .012, .03, .85))
        header(c, t, "GARAGE", f"{len(self.owned)} / {len(VEHICLES)} véhicules", VIOLET, ease_out(t / .5))
        chip(c, W - 90 - 250, 91, "coin", fmt(self.coins), GOLD, align="r")
        # fiche
        s, a = self.spec, ease_out(self.swap * 1.2)
        col = hexc(s.accent)
        c.alpha = a
        x = 90 - 40 * (1 - a)
        c.text(x, 268, s.name, 74, WHITE, color2=mix(WHITE, col, .75), glow=.6, glow_col=col, skew=.14, spacing=2, max_w=520)
        c.text(x + 2, 326, s.tagline, 23, MUTED, "text")
        kind = {"v8": "MOTEUR V8 ATMOSPHÉRIQUE", "turbo": "MOTEUR TURBO", "electric": "MOTEUR ÉLECTRIQUE"}[s.engine]
        c.text(x + 2, 362, kind, 15, alpha(col, 1), "text", spacing=2)
        for i, (lab, _, val, bc) in enumerate(STATS):
            y = 424 + i * 72
            c.text(x, y, lab, 17, (.72, .80, .92, 1), "text", spacing=1)
            c.text(x + 400, y, val(s), 22, WHITE, align="r")
            c.bar(x, y + 18, 400, 12, self.bars[i], mix(bc, VIOLET, .4), bc, (.08, .11, .20, .85), 26, 4, -.25)
        c.alpha = 1
        # personnalisation
        px = W - 90 - 380
        if owned:
            c.text(px, 178, "PERSONNALISATION", 18, MUTED, spacing=3)
            c.text(px, 300, TABS[self.tab][1], 24, WHITE, glow=.4, glow_col=VIOLET)
            cur = next((q.label for q in self.swatches if q.value == self.custom[q.kind]), "")
            foc = self.group.focus.label if isinstance(self.group.focus, Swatch) else cur
            c.text(px + 380, 300, foc, 20, CYAN, "text", "r")
        else:
            c.glass(px, 190, 380, 190, (.04, .06, .12, .60), 22, 1.5, alpha(GOLD, .5))
            icons.draw(c, "lock", px + 190, 246, 54, GOLD)
            c.text(px + 190, 304, "VÉHICULE VERROUILLÉ", 24, WHITE, align="c")
            c.text(px + 190, 338, "Débloquez-le avec les pièces gagnées en course", 16, MUTED, "text", "c")
        self.prev_btn.visible = self.next_btn.visible = True
        self.group.draw(c, t)
        # flèche gauche : icône retournée
        if self.msg_t < 2.6:
            m = ease_out(self.msg_t / .3) * clamp((2.6 - self.msg_t) / .5)
            c.alpha = m
            w = c.measure(self.msg, 40) + 120
            c.panel(W / 2 - w / 2, 180, w, 84, (.02, .035, .08, .9), None, 22, 2, alpha(self.msg_col, .9), 26)
            c.text(W / 2, 222, self.msg, 40, WHITE, color2=self.msg_col, align="c", glow=.7, glow_col=self.msg_col)
            c.alpha = 1
        c.text(W / 2, H - 152, "← → CHANGER DE VÉHICULE      GLISSER POUR TOURNER      MOLETTE POUR ZOOMER", 14, alpha(MUTED, .7), "text", "c")


assert all(v.id in BY_ID for v in VEHICLES)
