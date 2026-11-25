"""Contrôleur clavier (et manette si une est branchée), configurable."""
from __future__ import annotations

import pygame

from config.settings import ACTIONS, Settings, key_codes
from engine.mathx import clamp, damp
from entities.player import Controls


class KeyboardController:
    name = "Clavier"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.steer = 0.0
        self.reload()
        self.pads = []
        try:
            pygame.joystick.init()
            self.pads = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        except pygame.error:
            self.pads = []

    def reload(self):
        self.codes = {a: key_codes(self.settings["keys"][a]) for a in ACTIONS}

    def is_action(self, event, action: str) -> bool:
        return event.type == pygame.KEYDOWN and event.key in self.codes[action]

    def update(self, dt: float) -> Controls:
        pressed = pygame.key.get_pressed()

        def down(a):
            return any(pressed[c] for c in self.codes[a])
        target = float(down("right")) - float(down("left"))
        c = Controls(throttle=float(down("up")), brake=float(down("down")), nitro=down("nitro"))
        for p in self.pads:
            try:
                ax = p.get_axis(0)
                if abs(ax) > .14:
                    target = clamp(ax * 1.15, -1, 1)
                if p.get_numaxes() >= 6:
                    c.throttle = max(c.throttle, (p.get_axis(5) + 1) / 2)
                    c.brake = max(c.brake, (p.get_axis(4) + 1) / 2)
                c.nitro = c.nitro or p.get_button(0)
            except pygame.error:
                continue
        # montée progressive réglée par la sensibilité, retour au centre plus vif
        sens = self.settings["sensitivity"]
        rate = 6.5 + 13.0 * sens
        if target == 0 or target * self.steer < 0:
            rate *= 1.5
        self.steer = damp(self.steer, target, rate, dt)
        c.steer = self.steer * (.78 + .44 * sens)
        c.steer = clamp(c.steer, -1.15, 1.15)
        return c
