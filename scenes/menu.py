"""Menu principal."""
from __future__ import annotations

import math

import pygame

from config.modes import BY_ID as MODES
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha
from core.progression import level_from_xp, rank
from core.scene_manager import Scene
from effects.animation import ease_out
from engine.mathx import clamp
from scenes import backdrop
from ui import icons
from ui.logo import draw_logo
from ui.widgets import Button, Group, chip


def start_game(app, mode_id: str | None = None, replay: bool = False):
    """Lance une partie ; le mode gestuel passe par la calibration."""
    mode = MODES[mode_id or app.settings["mode"]]
    if mode.gesture and not (replay and app.gesture.calibrated):
        app.scenes.go("calibration", then="game")
    else:
        app.scenes.go("game", mode_id=mode.id)


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        go = app.scenes.go
        items = (("JOUER", "play", lambda: start_game(app), CYAN), ("GARAGE", "garage", lambda: go("garage"), VIOLET),
                 ("MODES DE JEU", "grid", lambda: go("modes"), CYAN), ("CLASSEMENT", "trophy", lambda: go("leaderboard"), GOLD),
                 ("STATISTIQUES", "chart", lambda: go("stats"), GREEN), ("PARAMÈTRES", "gear", lambda: go("settings"), VIOLET),
                 ("QUITTER", "exit", self.ask_quit, RED))
        self.group = Group(app, [Button(n, cb, icon=ic, color=col, primary=i == 0, w=430 if i == 0 else 400, h=78 if i == 0 else 62, size=32 if i == 0 else 25)
                                 for i, (n, ic, cb, col) in enumerate(items)])
        self.group.widgets[0].sub = f"Mode {MODES[app.settings['mode']].name.title()}"
        self.confirm = 0.0
        self.quit_group = Group(app, [Button("RESTER", self.cancel_quit, icon="check", color=CYAN, w=260, align="c"),
                                      Button("QUITTER", app.quit, icon="exit", color=RED, w=260, align="c")])
        self.asking = False
        self.resized()
        st = app.store
        self.best, self.coins = st.best(), st.coins
        self.level, self.xp, self.need = level_from_xp(st.get("xp"))

    def resized(self):
        c = self.app.canvas
        y = 372 + (c.H - 1080) / 2
        for i, b in enumerate(self.group.widgets):
            b.x, b.y = 104 - i * 5, y
            y += b.h + 16
        for i, b in enumerate(self.quit_group.widgets):
            b.x, b.y = c.W / 2 - 280 + i * 300, c.H / 2 + 50

    def enter(self):
        super().enter()
        self.backdrop.set_shot("menu")
        self.app.audio.ambience("neon_city")

    def ask_quit(self):
        self.asking = True
        self.quit_group.set_focus(self.quit_group.widgets[0], False)

    def cancel_quit(self):
        self.asking = False

    def event(self, e):
        if self.asking:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.cancel_quit()
            else:
                self.quit_group.event(e)
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.audio.play("ui_back", .7)
            self.ask_quit()
        else:
            self.group.event(e)

    def update(self, dt):
        super().update(dt)
        self.backdrop.update(dt)
        self.group.reveal(self.t, start=.35)
        self.group.update(dt)
        self.quit_group.update(dt)
        self.confirm += ((1.0 if self.asking else 0.0) - self.confirm) * min(1, dt * 12)

    def draw(self, c):
        self.backdrop.draw(flash=max(0, .5 - self.t) * .6)
        t, W, H, app = self.t, c.W, c.H, self.app
        c.rect(0, 0, 820, H, (.012, .02, .045, .86), (.012, .02, .045, 0), True)
        c.rect(0, H - 260, W, 260, (.01, .016, .035, 0), (.01, .016, .035, .80))
        draw_logo(c, 100, 178 + (H - 1080) / 3, 112, t, clamp(t / 1.2))
        self.group.draw(c, t)
        # bandeau joueur
        a = ease_out((t - .6) / .6)
        c.alpha = a
        x = W - 70
        x -= chip(c, x, 74, "coin", f"{self.coins:,}".replace(",", " "), GOLD, align="r") + 18
        chip(c, x, 74, "trophy", f"{self.best:,}".replace(",", " "), CYAN, align="r")
        # carte véhicule
        spec = app.vehicle
        bx, by, bw = W - 560, H - 206, 490
        c.glass(bx, by, bw, 136, (.035, .06, .12, .62), 22, 1.5, alpha(CYAN, .40))
        c.text(bx + 30, by + 38, "VÉHICULE ACTIF", 16, MUTED, "text", spacing=2)
        c.text(bx + 30, by + 78, spec.name, 40, WHITE, color2=(.6, .85, 1, 1), glow=.4, glow_col=CYAN, skew=.12, max_w=280)
        c.text(bx + 30, by + 112, spec.tagline, 17, MUTED, "text", max_w=290)
        c.arc(bx + bw - 82, by + 68, 44, 7, 0, math.tau * .999, (.10, .14, .24, .9))
        c.arc(bx + bw - 82, by + 68, 44, 7, 0, math.tau * max(.02, self.xp / self.need) * .999, CYAN, VIOLET, glow=1)
        c.text(bx + bw - 82, by + 64, str(self.level), 34, WHITE, align="c")
        c.text(bx + bw - 82, by + 92, "NIVEAU", 11, MUTED, "text", "c")
        c.text(bx + bw - 146, by + 112, rank(self.level), 14, alpha(CYAN, .9), "text", "r")
        c.text(104, H - 38, "↑ ↓  NAVIGUER     ENTRÉE  VALIDER     F11  PLEIN ÉCRAN", 16, alpha(MUTED, .8), "text")
        c.alpha = 1
        if self.confirm > .01:
            k = self.confirm
            c.rect(0, 0, W, H, (.01, .015, .03, .72 * k))
            c.alpha = k
            c.panel(W / 2 - 360, H / 2 - 130, 720, 280, (.04, .065, .13, .96), (.02, .035, .08, .96), 28, 2, alpha(RED, .7), 24)
            icons.draw(c, "exit", W / 2, H / 2 - 82, 44, RED)
            c.text(W / 2, H / 2 - 18, "QUITTER NEON DRIVE ?", 36, WHITE, align="c")
            self.quit_group.draw(c, t)
            c.alpha = 1
