"""Gestion des scènes et des transitions cinématographiques."""
from __future__ import annotations

import importlib
import logging

import pygame

from config.palette import CYAN, VIOLET, alpha
from effects.animation import ease_in_out

log = logging.getLogger(__name__)
SCENES = {
    "loading": "scenes.loading:LoadingScene", "menu": "scenes.menu:MenuScene", "modes": "scenes.modes:ModesScene",
    "garage": "scenes.garage:GarageScene", "leaderboard": "scenes.leaderboard:LeaderboardScene", "stats": "scenes.stats:StatsScene",
    "settings": "scenes.settings:SettingsScene", "game": "scenes.game:GameScene", "gameover": "scenes.gameover:GameOverScene",
    "calibration": "scenes.calibration:CalibrationScene",
}


class Scene:
    """Base : chaque écran gère ses événements, sa mise à jour et son dessin."""
    music = "menu"

    def __init__(self, app, **kw):
        self.app = app
        self.t = 0.0

    def enter(self):
        if self.music:
            self.app.audio.music(self.music)

    def leave(self):
        pass

    def event(self, e):
        pass

    def update(self, dt):
        self.t += dt

    def draw(self, c):
        pass

    def resized(self):
        pass

    def intensity(self) -> float:
        return 0.0


class SceneManager:
    DURATION = .85

    def __init__(self, app):
        self.app = app
        self.scene: Scene | None = None
        self.name = ""
        self.next = None
        self.k = 1.0           # progression de la transition (0..1), 1 = terminée
        self.swapped = True
        self.style = "blades"

    def _build(self, name, kw):
        mod, cls = SCENES[name].split(":")
        return getattr(importlib.import_module(mod), cls)(self.app, **kw)

    def set(self, name: str, **kw):
        """Changement immédiat."""
        if self.scene:
            self.scene.leave()
        self.name = name
        self.scene = self._build(name, kw)
        self.scene.enter()

    def go(self, name: str, style: str = "blades", **kw):
        """Changement avec transition ; ignoré si une transition est en cours."""
        if self.busy:
            return
        self.next, self.k, self.swapped, self.style = (name, kw), 0.0, False, style
        self.app.audio.play("ui_transition", .7)

    @property
    def busy(self) -> bool:
        return self.k < 1.0 and not self.swapped

    def event(self, e):
        if self.scene and not (self.busy and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN)):
            self.scene.event(e)

    def update(self, dt):
        if self.k < 1.0:
            self.k = min(1.0, self.k + min(dt, .05) / self.DURATION)
            if self.k >= .5 and not self.swapped:
                self.swapped = True
                name, kw = self.next
                self.set(name, **kw)
        if self.scene:
            self.scene.update(dt)

    def draw(self):
        c = self.app.canvas
        if self.scene:
            self.scene.draw(c)
        if self.k < 1.0:
            c.alpha, c.ox, c.oy = 1.0, 0.0, 0.0
            self._transition(c)

    def _transition(self, c):
        """Lames inclinées qui se referment puis s'ouvrent, bordées de lumière."""
        n, W, H = 7, c.W, c.H
        k = self.k * 2
        closing = k < 1
        for i in range(n):
            d = i / (n - 1) * .45
            p = ease_in_out(((k if closing else k - 1) - d) / .55)
            w = W / n * 1.34
            x = -W * .12 + i * W / n * 1.12
            h = H + 8
            if closing:
                y = -h + h * p if i % 2 == 0 else H - h * p
            else:
                y = h * p if i % 2 == 0 else -h * p
            if -h < y < H:
                col = (.016, .024, .050, 1)
                c.rect(x, y - 4, w, h, col, (.028, .040, .085, 1), skew=.18)
                edge = CYAN if i % 2 else VIOLET
                ey = y + h - 6 if (i % 2 == 0) == closing else y
                c.rect(x, ey - 4, w, 4, edge, skew=.18)
                c.rect(x, ey - 24, w, 44, alpha(edge, .10), skew=.18)
        f = 1 - abs(self.k - .5) * 7
        if f > 0:
            c.text(W / 2, H / 2, "NEON DRIVE", 46, alpha((1, 1, 1, 1), f), align="c", glow=.8 * f, glow_col=CYAN, skew=.16, spacing=10)
            c.rect(W / 2 - 260 * f, H / 2 + 44, 520 * f, 3, alpha(CYAN, f), alpha(VIOLET, f), True)

    def resized(self):
        if self.scene:
            self.scene.resized()

    def music_intensity(self) -> float:
        return self.scene.intensity() if self.scene else 0.0
