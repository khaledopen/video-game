"""Voiture du joueur : conduite arcade, inertie, nitro, vie et bonus actifs."""
from __future__ import annotations

import math
from dataclasses import dataclass

from config.vehicles import VehicleSpec
from engine.mathx import approach, clamp, damp
from engine.track import ROAD_HALF

MIN_SPEED = 13.0
BONUS_TIME = {"shield": 8.0, "magnet": 12.0, "multi": 12.0, "slow": 7.0}


@dataclass
class Controls:
    """Entrées normalisées, quelle que soit leur source (clavier, gestes, pilote auto)."""
    steer: float = 0.0        # -1 gauche .. 1 droite
    throttle: float = 0.0     # 0..1
    brake: float = 0.0        # 0..1
    nitro: bool = False


class Player:
    def __init__(self, spec: VehicleSpec, width: float = 1.95, length: float = 4.6):
        self.spec = spec
        self.width, self.length = width, length
        self.s = 0.0
        self.x = -1.8
        self.v = 24.0
        self.vx = 0.0
        self.hp = 100.0
        self.nitro = .5
        self.nitro_on = False
        self.nitro_lock = 0.0
        self.invuln = 0.0
        self.slip = 0.0               # aquaplanage restant (s)
        self.timers = {k: 0.0 for k in BONUS_TIME}
        self.scraping = 0.0
        self.alive = True
        # visuel
        self.roll = self.yaw = self.pitch = self.spin = self.steer_vis = 0.0
        self.brake = self.flash = 0.0
        self.spinout = 0.0            # tête-à-queue résiduel (rad)
        self.accel_vis = 0.0

    # caractéristiques dérivées
    @property
    def top(self) -> float:
        return self.spec.top_ms

    @property
    def cruise(self) -> float:
        return self.top * .58

    @property
    def speed_ratio(self) -> float:
        return clamp(self.v / (self.top * 1.28))

    @property
    def lateral_max(self) -> float:
        return (8.6 + .62 * self.spec.handling) * (.55 + .45 * min(1.0, self.v / 30.0))

    @property
    def edge(self) -> float:
        return ROAD_HALF - self.width / 2 - .22

    def active(self, bonus: str) -> bool:
        return self.timers[bonus] > 0

    def update(self, dt: float, c: Controls, curvature: float, grip: float = 1.0, boost_top: float = 1.0) -> None:
        sp = self.spec
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt * 2.6)
        self.slip = max(0.0, self.slip - dt)
        self.nitro_lock = max(0.0, self.nitro_lock - dt)
        for k in self.timers:
            self.timers[k] = max(0.0, self.timers[k] - dt)

        # nitro : hystérésis pour ne pas crachoter à vide
        want = c.nitro and self.alive and self.nitro_lock <= 0
        if self.nitro_on:
            self.nitro_on = want and self.nitro > 0
            if self.nitro <= 0:
                self.nitro_lock = .6
        else:
            self.nitro_on = want and self.nitro > .06
        if self.nitro_on:
            self.nitro = max(0.0, self.nitro - dt / (2.0 + .28 * sp.nitro))
        else:
            self.nitro = min(1.0, self.nitro + dt * (.012 + .0016 * sp.nitro) * (.4 + self.speed_ratio))

        # vitesse
        top = self.top * boost_top
        acc = 6.2 + 1.15 * sp.accel
        v0 = self.v
        if not self.alive:
            self.v = approach(self.v, 0.0, 15.0 * dt)
        elif self.nitro_on:
            lim = top * 1.28
            self.v = approach(self.v, lim, (acc * 1.9) * dt * (1.15 - .6 * clamp(self.v / lim)))
        elif c.brake > .05:
            self.v = approach(self.v, MIN_SPEED, (20.0 + sp.handling) * c.brake * dt * grip)
        elif c.throttle > .05:
            lim = self.cruise + (top - self.cruise) * c.throttle
            if self.v > lim:
                self.v = approach(self.v, lim, 5.0 * dt)
            else:
                self.v = approach(self.v, lim, acc * dt * (1.18 - .95 * clamp(self.v / top) ** 1.5))
        else:
            self.v = approach(self.v, self.cruise, (5.5 if self.v > self.cruise else 4.0) * dt)
        if self.slip > 0:
            self.v -= self.v * .10 * dt
        self.brake = damp(self.brake, c.brake if self.alive else 1.0, 14, dt)

        # latéral avec inertie
        g = grip * (.16 if self.slip > 0 else 1.0)
        target = c.steer * self.lateral_max if self.alive else 0.0
        resp = (5.2 + .42 * sp.handling) * g
        if abs(target) < abs(self.vx) or target * self.vx < 0:
            resp *= 1.25
        self.vx += (target - self.vx) * (1 - math.exp(-resp * dt))
        drift = -curvature * self.v * self.v * .20 * (1.15 - .045 * sp.handling)
        self.x += (self.vx + drift) * dt
        self.s += self.v * dt

        # glissière
        self.scraping = max(0.0, self.scraping - dt)

        # visuel : lacet, roulis, tangage, roues
        self.accel_vis = damp(self.accel_vis, (self.v - v0) / max(dt, 1e-4), 7, dt)
        self.yaw = damp(self.yaw, math.atan2(self.vx * .62, max(self.v, 16.0)) * 1.25, 10, dt)
        self.roll = damp(self.roll, clamp(-self.vx * .0075 - curvature * self.v * self.v * .004, -.12, .12), 8, dt)
        self.pitch = damp(self.pitch, clamp(-self.accel_vis * .0024, -.035, .045), 6, dt)
        self.spinout = damp(self.spinout, 0.0, 2.6 if self.alive else .35, dt)
        self.steer_vis = damp(self.steer_vis, c.steer * .42, 12, dt)
        self.spin = (self.spin + self.v / .345 * dt) % (2 * math.pi)

    def damage(self, amount: float, scale: float = 1.0) -> float:
        """Applique des dégâts ; retourne les dégâts réellement subis."""
        if not self.alive or self.invuln > 0:
            return 0.0
        amount *= (1.38 - .075 * self.spec.armor) * scale
        self.hp = max(0.0, self.hp - amount)
        self.flash = 1.0
        return amount

    def give(self, bonus: str) -> None:
        if bonus == "nitro":
            self.nitro = min(1.0, self.nitro + .55)
        elif bonus == "repair":
            self.hp = min(100.0, self.hp + 35)
        else:
            self.timers[bonus] = BONUS_TIME[bonus]
