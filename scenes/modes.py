"""Choix du mode de jeu et de l'univers."""
from __future__ import annotations

import math

import pygame

from config.environments import PLAYABLE
from config.modes import MODES
from config.palette import CYAN, GOLD, MUTED, RED, VIOLET, WHITE, alpha, hexc, mix
from controllers.gesture import GestureController
from core.scene_manager import Scene
from effects.animation import ease_out
from engine.mathx import clamp
from scenes import backdrop
from scenes.menu import start_game
from ui import icons
from ui.hud import fmt
from ui.widgets import Button, Group, Widget, header


class ModeCard(Widget):
    def __init__(self, scene, mode, best, available=True, reason=""):
        super().__init__()
        self.scene, self.mode, self.best, self.available, self.reason = scene, mode, best, available, reason
        self.color = hexc(mode.color)

    def click(self, app, mx, my):
        if not self.available:
            app.audio.play("ui_denied", .7)
            return True
        if self.scene.selected == self.mode.id:
            self.scene.play()
        else:
            app.audio.play("ui_click", .8)
            self.scene.select(self.mode.id)
        self.press = 1.0
        return True

    def draw(self, c, t):
        a = self.appear
        if a < .01:
            return
        sel = self.scene.selected == self.mode.id
        h = clamp(self.hover.v)
        col = self.color if self.available else (.35, .40, .50, 1)
        x, y, w, ht = self.x, self.y + 60 * (1 - a) - 14 * h - (10 if sel else 0), self.w, self.h
        c.alpha *= a
        c.panel(x, y, w, ht, mix((.030, .050, .105, .84), (*col[:3], .80), .10 + .10 * h + (.10 if sel else 0)), (.018, .028, .065, .88), 30, 1.6 + (1.4 if sel else 0),
                alpha(col, .28 + .4 * h + (.5 if sel else 0)), 10 + 24 * max(h, float(sel)))
        cx, cy = x + w / 2, y + 112
        c.halo(cx, cy, 120, alpha(col, .20 + .25 * max(h, float(sel))))
        rot = t * .35 * (1 if sel else .4)
        for i in range(3):
            s0 = rot + i * math.tau / 3
            c.arc(cx, cy, 72, 3, s0 - math.tau * round(s0 / math.tau), s0 - math.tau * round(s0 / math.tau) + 1.3, alpha(col, .8), alpha(WHITE, .2))
        icons.draw(c, self.mode.icon, cx, cy, 72 + 8 * h, mix(col, WHITE, .35))
        c.text(cx, y + 226, self.mode.name, 33, WHITE, color2=mix(WHITE, col, .7), align="c", glow=.5 * max(h, float(sel)), glow_col=col, max_w=w - 36, spacing=2)
        c.text(cx, y + 262, self.mode.subtitle, 16, alpha(mix(MUTED, col, .4), 1), "text", "c", max_w=w - 36)
        c.rect(x + 34, y + 288, w - 68, 2, alpha(col, .5), alpha(col, 0), True)
        c.paragraph(cx, y + 320, self.mode.description if self.available else self.reason, 16.5, (.74, .82, .94, 1), w - 48, align="c")
        c.text(cx, y + ht - 62, "RECORD", 13, MUTED, "text", "c", spacing=3)
        c.text(cx, y + ht - 34, fmt(self.best) if self.best else "—", 25, WHITE, align="c")
        c.alpha /= a


class EnvTile(Widget):
    def __init__(self, scene, env_id, name, color, sub):
        super().__init__(h=70)
        self.scene, self.env_id, self.name, self.color, self.sub = scene, env_id, name, color, sub

    def click(self, app, mx, my):
        app.audio.play("ui_click", .7)
        app.settings["environment"] = self.env_id
        app.settings.save()
        return True

    def draw(self, c, t):
        sel = self.scene.app.settings["environment"] == self.env_id
        h = clamp(self.hover.v)
        c.alpha *= self.appear
        c.panel(self.x, self.y, self.w, self.h, mix((.03, .05, .10, .80), (*self.color[:3], .7), .08 + .2 * h + (.25 if sel else 0)), None, 12, 1.4 + sel,
                alpha(self.color, .25 + .4 * h + (.5 if sel else 0)), 16 * max(h, float(sel)), 1, -.14)
        c.text(self.x + self.w / 2, self.y + 27, self.name, 19, WHITE, align="c", max_w=self.w - 34)
        c.text(self.x + self.w / 2, self.y + 51, self.sub, 13, MUTED, "text", "c", max_w=self.w - 40)
        c.alpha /= max(self.appear, 1e-3)


class ModesScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        self.selected = app.settings["mode"]
        ok, why = GestureController.available()
        self.cards = []
        for m in MODES:
            av, reason = (True, "") if not m.gesture else (ok and app.settings["gesture_enabled"], why or "Activez le contrôle gestuel dans les paramètres.")
            self.cards.append(ModeCard(self, m, app.store.best(m.id), av, reason))
        self.tiles = [EnvTile(self, "auto", "TOUR DU MONDE", CYAN, "Les 5 univers s'enchaînent")]
        self.tiles += [EnvTile(self, e.id, e.name, hexc(e.accent), e.subtitle) for e in PLAYABLE]
        self.go_btn = Button("LANCER LA PARTIE", self.play, icon="play", w=430, h=72, size=27, primary=True)
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=240, sound="ui_back")
        self.group = Group(app, [*self.cards, *self.tiles, self.back_btn, self.go_btn])
        self.resized()

    def enter(self):
        super().enter()
        self.backdrop.set_shot("wide")

    def resized(self):
        c = self.app.canvas
        n, gap, m = len(self.cards), 22, 90
        w = (c.W - 2 * m - gap * (n - 1)) / n
        y = 218 + (c.H - 1080) * .3
        for i, k in enumerate(self.cards):
            k.x, k.y, k.w, k.h = m + i * (w + gap), y, w, 510
        n2 = len(self.tiles)
        w2 = (c.W - 2 * m - 16 * (n2 - 1)) / n2
        for i, k in enumerate(self.tiles):
            k.x, k.y, k.w = m + i * (w2 + 16), y + 586, w2
        self.back_btn.x, self.back_btn.y = m, c.H - 108
        self.go_btn.x, self.go_btn.y = c.W - m - self.go_btn.w, c.H - 112

    def select(self, mid):
        self.selected = mid
        self.app.settings["mode"] = mid
        self.app.settings.save()

    def play(self):
        start_game(self.app, self.selected)

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
        self.backdrop.update(dt)
        self.group.reveal(self.t, .05, .5, (0, 40), .2)
        self.group.update(dt)

    def draw(self, c):
        self.backdrop.draw(fade=.42)
        c.rect(0, 0, c.W, c.H, (.01, .016, .04, .30), (.01, .016, .04, .62))
        header(c, self.t, "MODES DE JEU", "Choisissez votre défi, puis l'univers de départ", CYAN, ease_out(self.t / .5))
        c.text(90, self.tiles[0].y - 26, "UNIVERS", 20, MUTED, spacing=4)
        self.group.draw(c, self.t)


__all__ = ["ModesScene", "GOLD", "RED"]
