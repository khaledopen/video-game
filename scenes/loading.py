"""Introduction animée : chargement réel des ressources pendant que le logo s'allume."""
from __future__ import annotations

import math
import time

import pygame

from config.palette import BLACK, CYAN, RED, VIOLET, WHITE, alpha, mix
from core.scene_manager import Scene
from effects.animation import ease_in_out, ease_out
from engine.mathx import clamp, damp, hash01
from ui.logo import draw_logo

SOUNDS = ("boot ui_hover ui_click ui_back ui_denied ui_transition ui_count ui_go coin coin_big crash bump scrape cone splash near_miss "
          "nitro_start nitro_end shield_hit level_up portal destroyed warning pk_nitro pk_shield pk_magnet pk_repair pk_multi pk_slow").split()
TIPS = ("Frôler un véhicule recharge la nitro et fait monter le combo.", "Dans les virages, la force centrifuge pousse la voiture vers l'extérieur.",
        "Les flaques font perdre l'adhérence : redressez doucement.", "Le bouclier absorbe les chocs et repousse la circulation.",
        "Chaque univers a son adhérence : méfiance sous la pluie de Tokyo.")


class LoadingScene(Scene):
    music = None
    MIN_TIME = 4.2

    def __init__(self, app):
        super().__init__(app)
        r = app.renderer
        self.tasks = [(f"MODÈLES 3D  {n.split(':')[-1].upper()}", lambda n=n: r.load_mesh(n)) for n in r.preload_names()]
        self.tasks += [(f"SONS  {n.upper()}", lambda n=n: app.audio.sound(n)) for n in SOUNDS]
        self.tasks.append(("MONDE", lambda: __import__("scenes.backdrop", fromlist=["get"]).get(app)))
        self.total = len(self.tasks)
        self.done = 0
        self.bar = 0.0
        self.label = "INITIALISATION"
        self.leaving = False
        self.tip = int(time.time()) % len(TIPS)

    def enter(self):
        self.app.audio.play("boot", .9)

    def event(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.done >= self.total:
            self._leave()

    def _leave(self):
        if not self.leaving:
            self.leaving = True
            self.app.scenes.go("menu")

    def update(self, dt):
        super().update(dt)
        t0 = time.perf_counter()
        while self.done < self.total and time.perf_counter() - t0 < .010:
            self.label, job = self.tasks[self.done]
            job()
            self.done += 1
        target = min(self.done / self.total, self.t / (self.MIN_TIME - .5))
        self.bar = damp(self.bar, target, 7, dt)
        if self.done >= self.total and self.t > self.MIN_TIME:
            self._leave()

    def draw(self, c):
        self.app.ctx.screen.use() if not self.app.headless else self.app.target.use()
        t, W, H = self.t, c.W, c.H
        c.rect(0, 0, W, H, mix(BLACK, (.02, .03, .07, 1), .5), BLACK)
        hz = H * .60
        pulse = clamp(1 - abs(t - 2.15) * 1.6)
        k = ease_out(t / 2.2)
        # horizon, grille en perspective et pluie de lumière
        c.halo(W / 2, hz, 900 * k, alpha(VIOLET, .30 * k))
        c.halo(W / 2, hz, 520 * k, alpha(CYAN, .26 * k + .4 * pulse))
        for i in range(-14, 15):
            a = (1 - abs(i) / 15) * .55 * k
            c.line(W / 2 + i * 26, hz, W / 2 + i * 260, H + 40, alpha(CYAN, a * .35), 2, alpha(VIOLET, a))
        for i in range(12):
            z = ((i + t * 1.6) % 12) / 12
            y = hz + (H - hz) * z**2.6
            c.rect(0, y, W, 1 + 2 * z, alpha(CYAN, .05 + .40 * z * k))
        c.rect(0, hz - 1, W * k, 2, alpha(CYAN, .9), alpha(VIOLET, .9), True)
        for i in range(46):
            h1, h2 = float(hash01(i, 1)), float(hash01(i, 2))
            z = (h2 + t * (.16 + .22 * h1)) % 1
            ang = h1 * math.tau
            r0 = 40 + z**2 * W * .62
            ln = 12 + 150 * z**2
            x0, y0 = W / 2 + math.cos(ang) * r0, hz - 40 + math.sin(ang) * r0 * .5
            if y0 < hz:
                c.line(x0, y0, x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln * .5, alpha((.6, .85, 1), 0), 1 + 2 * z, alpha(CYAN if i % 3 else VIOLET, .55 * z * k))
        # logo
        draw_logo(c, W / 2, H * .40 + 12 * math.sin(t * .8), 132 + 10 * pulse, t, clamp((t - .5) / 1.9), "c")
        if pulse > 0:
            c.rect(0, H * .40 - 3 * pulse, W, 6 * pulse, alpha(WHITE, 0), alpha(WHITE, pulse), True)
            c.halo(W / 2, H * .40, 1100, alpha(CYAN, .25 * pulse))
        # barre de chargement segmentée
        a = ease_out((t - .4) / .8)
        bw, bx, by = 760, W / 2 - 380, H * .80
        c.alpha = a
        c.panel(bx - 14, by - 14, bw + 28, 42, (.03, .05, .10, .75), None, 10, 1.4, alpha(CYAN, .45), 14, 1, -.2)
        c.bar(bx, by, bw, 14, self.bar, CYAN, VIOLET, (.08, .11, .19, .9), 46, 4, -.2)
        hx = bx + bw * self.bar
        c.halo(hx, by + 7, 70, alpha(WHITE, .55))
        c.text(bx - 8, by + 52, self.label if self.done < self.total else "PRÊT", 18, alpha((.7, .82, 1), .8), "text")
        c.text(bx + bw + 8, by + 52, f"{round(self.bar * 100):d}", 30, WHITE, align="r", glow=.5, glow_col=CYAN, mono=True)
        c.text(W / 2, H * .93, TIPS[self.tip], 20, alpha((.6, .7, .88), .9), "text", "c")
        c.alpha = 1
        f = ease_in_out(clamp(t / .7))
        if f < 1:
            c.rect(0, 0, W, H, alpha(BLACK, 1 - f))
        c.rect(0, H - 4, W * self.bar, 4, RED, VIOLET, True)
