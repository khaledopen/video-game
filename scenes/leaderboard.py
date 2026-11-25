"""Classement local des meilleures parties."""
from __future__ import annotations

import time

import pygame

from config.modes import BY_ID, MODES
from config.palette import CYAN, GOLD, MUTED, VIOLET, WHITE, alpha, hexc, mix
from config.vehicles import BY_ID as VEH
from core.scene_manager import Scene
from effects.animation import stagger
from engine.mathx import clamp
from effects.animation import ease_out
from scenes import backdrop
from ui import icons
from ui.hud import fmt
from ui.widgets import Button, Group, header

MEDALS = (GOLD, (.80, .86, .95, 1), (.90, .55, .30, 1))


class LeaderboardScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        self.filters = [(None, "TOUS", "trophy", "#00E5FF")] + [(m.id, m.name, m.icon, m.color) for m in MODES]
        self.sel = 0
        self.buttons = [Button(n, lambda i=i: self.choose(i), icon=ic, color=hexc(col), w=270, h=58, size=20) for i, (_, n, ic, col) in enumerate(self.filters)]
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=270, sound="ui_back")
        self.group = Group(app, [*self.buttons, self.back_btn])
        self.rt = 0.0
        self.choose(0)
        self.resized()

    def enter(self):
        super().enter()
        self.backdrop.set_shot("low")

    def resized(self):
        for i, b in enumerate(self.buttons):
            b.x, b.y = 90, 226 + i * 74
        self.back_btn.x, self.back_btn.y = 90, self.app.canvas.H - 108

    def choose(self, i):
        self.sel = i
        self.rows = self.app.store.top(self.filters[i][0], 10)
        self.rt = 0.0

    def back(self):
        self.app.scenes.go("menu")

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.audio.play("ui_back", .7)
            self.back()
        else:
            self.group.event(e)

    def update(self, dt):
        super().update(dt)
        self.rt += dt
        self.backdrop.update(dt)
        self.group.reveal(self.t, .05, .45, (-80, 0), .2)
        self.group.update(dt)
        for i, b in enumerate(self.buttons):
            b.selected = i == self.sel

    def draw(self, c):
        self.backdrop.draw(fade=.40)
        W, H, t = c.W, c.H, self.t
        c.rect(0, 0, W, H, (.01, .016, .04, .35), (.01, .016, .04, .65))
        header(c, t, "CLASSEMENT", "Vos dix meilleures parties, enregistrées sur cet ordinateur", GOLD, ease_out(t / .5))
        self.group.draw(c, t)
        x, y, w = 410, 226, W - 500
        c.glass(x, y, w, H - y - 70, (.03, .05, .105, .62), 30, 1.5, alpha(GOLD, .25))
        cols = (("RANG", .030, "l"), ("SCORE", .105, "l"), ("MODE", .30, "l"), ("VÉHICULE", .46, "l"), ("DISTANCE", .70, "r"), ("V. MAX", .815, "r"), ("DATE", .97, "r"))
        for lab, k, al in cols:
            c.text(x + w * k, y + 38, lab, 15, MUTED, "text", al, spacing=2)
        c.rect(x + 24, y + 60, w - 48, 2, alpha(GOLD, .6), alpha(GOLD, 0), True)
        if not self.rows:
            icons.draw(c, "trophy", x + w / 2, y + 260, 120, alpha(GOLD, .35))
            c.text(x + w / 2, y + 360, "AUCUNE PARTIE ENREGISTRÉE", 30, WHITE, align="c")
            c.text(x + w / 2, y + 400, "Prenez la route pour inscrire votre premier score", 20, MUTED, "text", "c")
        rh = min(66., (H - y - 160) / 10)
        for i, r in enumerate(self.rows):
            a = stagger(self.rt, i, .045, .4)
            if a <= 0:
                continue
            c.alpha = a
            ry = y + 78 + i * rh
            ox = 60 * (1 - a)
            col = MEDALS[i] if i < 3 else CYAN
            c.panel(x + 20 + ox, ry, w - 40, rh - 8, mix((.05, .08, .16, .55), (*col[:3], .55), .16 if i < 3 else .04), (.03, .05, .10, .25), 10, 1.2, alpha(col, .5 if i < 3 else .12), 0, 1, 0, True)
            cy = ry + (rh - 8) / 2
            mode = BY_ID.get(r.mode)
            mcol = hexc(mode.color) if mode else CYAN
            c.text(x + w * .045 + ox, cy, str(i + 1), 34 if i < 3 else 25, col, align="c", glow=.6 if i < 3 else 0, glow_col=col)
            c.text(x + w * .105 + ox, cy, fmt(r.score), 32, WHITE, mono=True, color2=mix(WHITE, col, .4))
            if mode:
                icons.draw(c, mode.icon, x + w * .31 + ox, cy, 24, mcol)
            c.text(x + w * .33 + ox, cy, mode.name if mode else r.mode, 19, mcol)
            c.text(x + w * .46 + ox, cy, VEH[r.vehicle].name if r.vehicle in VEH else r.vehicle, 20, (.82, .9, 1, 1))
            c.text(x + w * .70 + ox, cy, f"{r.distance / 1000:.2f} km", 20, WHITE, "text", "r")
            c.text(x + w * .815 + ox, cy, f"{r.top_speed:.0f} km/h", 20, WHITE, "text", "r")
            c.text(x + w * .97 + ox, cy, time.strftime("%d/%m/%Y  %H:%M", time.localtime(r.played_at)), 17, MUTED, "text", "r")
        c.alpha = clamp(1.0)
