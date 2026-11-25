"""Fin de partie : bilan, récompenses et animation NEW RECORD."""
from __future__ import annotations

import math

import numpy as np
import pygame

from config.modes import BY_ID as MODES
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, hexc, mix
from core.progression import rank
from core.scene_manager import Scene
from effects.animation import ease_back, ease_out, stagger
from engine.mathx import clamp, look_angles
from scenes.menu import start_game
from ui import icons
from ui.hud import fmt
from ui.widgets import Button, Group

RECORD_AT = 1.9


class GameOverScene(Scene):
    def __init__(self, app, world, view, result):
        super().__init__(app)
        self.world, self.view, self.res = world, view, result
        self.view.desat = .25
        self.view.particles.clear()
        self.group = Group(app, [Button("REJOUER", lambda: start_game(app, world.mode.id, replay=True), icon="retry", color=CYAN, w=400, h=76, size=28, primary=True),
                                 Button("GARAGE", lambda: app.scenes.go("garage"), icon="garage", color=VIOLET, w=330, h=76, size=25),
                                 Button("MENU PRINCIPAL", lambda: app.scenes.go("menu"), icon="home", color=GOLD, w=400, h=76, size=25)])
        self.played = set()
        self.mode = MODES[world.mode.id]
        rng = np.random.default_rng(3)
        self.conf = rng.random((90, 5))
        self.resized()

    def enter(self):
        super().enter()
        self.app.audio.play("game_over" if not self.res.record else "level_up", .8)

    def resized(self):
        c = self.app.canvas
        tot = sum(b.w for b in self.group.widgets) + 2 * 26
        x = c.W / 2 - tot / 2
        for b in self.group.widgets:
            b.x, b.y = x, c.H - 136
            x += b.w + 26

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.scenes.go("menu")
        elif self.t > .6:
            self.group.event(e)

    def _once(self, name, when, sound, vol=.8):
        if self.t > when and name not in self.played:
            self.played.add(name)
            self.app.audio.play(sound, vol)

    def update(self, dt):
        super().update(dt)
        self.group.reveal(self.t, .10, .5, (0, 50), 1.2)
        self.group.update(dt)
        self.view.update(dt, dt)
        if self.res.record:
            self._once("record", RECORD_AT, "new_record", 1.0)
        if self.res.level_after > self.res.level_before:
            self._once("level", 2.6, "level_up")
        for i, _ in enumerate(self.res.achievements):
            self._once(f"a{i}", 2.2 + i * .35, "achievement", .7)
        if 1 < self.t < 2.1 and int(self.t * 18) != int((self.t - dt) * 18):
            self.app.audio.play("ui_tick", .12)

    def draw(self, c):
        w = self.world

        def cam(px, t):
            a = .9 + self.t * .10
            pos = [px + math.sin(a) * 7.6, 1.5 + .3 * math.sin(self.t * .2), -math.cos(a) * 7.6]
            yaw, pitch = look_angles(pos, (px, .9, 0))
            return pos, (yaw, pitch), 0.0, 50.0
        self.view.render(cam, fade=.36, vignette=1.1, speed_lines=0.0, blur=0.0, flash=max(0, .4 - self.t), desat=.35)
        t, W, H, r, st = self.t, c.W, c.H, self.res, w.stats
        col = hexc(self.mode.color)
        c.rect(0, 0, W, H, (.01, .015, .04, .30), (.01, .015, .04, .72))
        # titre
        k = ease_out(t / .7)
        title = "GAME OVER" if w.over_reason == "destroyed" else "TEMPS ÉCOULÉ"
        c.text(W / 2, 108, title, 96, alpha(WHITE, k), color2=alpha(RED if w.over_reason == "destroyed" else GOLD, k), align="c", glow=.9 * k, glow_col=RED if w.over_reason == "destroyed" else GOLD, skew=.16, spacing=6 + 40 * (1 - k))
        c.rect(W / 2 - 420 * k, 172, 840 * k, 3, alpha(CYAN, .8), alpha(VIOLET, .8), True)
        c.text(W / 2, 200, f"MODE {self.mode.name}   ·   {w.player.spec.name}   ·   {w.env.name}", 20, alpha(MUTED, k), align="c", spacing=2)
        # score
        sx, sy, sw, sh = W / 2 - 800, 244, 760, 270
        a = ease_out((t - .25) / .5)
        c.alpha = a
        c.glass(sx, sy, sw, sh, (.03, .05, .11, .66), 34, 1.8, alpha(col, .5), 20)
        c.text(sx + 46, sy + 50, "SCORE FINAL", 22, MUTED, spacing=4)
        val = r.score * ease_out((t - .8) / 1.3)
        c.text(sx + 44, sy + 134, fmt(val), 112, WHITE, color2=mix(WHITE, col, .7), glow=.6, glow_col=col, mono=True, max_w=sw - 90)
        c.rect(sx + 46, sy + 198, sw - 92, 2, alpha(WHITE, .15))
        icons.draw(c, "trophy", sx + 62, sy + 232, 32, GOLD)
        c.text(sx + 92, sy + 232, "MEILLEUR SCORE", 18, MUTED, "text")
        c.text(sx + sw - 46, sy + 232, fmt(max(r.best, r.score)), 32, GOLD, align="r", mono=True)
        # bilan
        items = (("DISTANCE", f"{st.distance / 1000:.2f} km", "road", CYAN), ("TEMPS DE JEU", f"{int(st.time // 60)}:{int(st.time % 60):02d}", "clock", GREEN),
                 ("VITESSE MAX", f"{st.top_speed:.0f} km/h", "speed", RED), ("PIÈCES", f"{st.coins}", "coin", GOLD),
                 ("OBSTACLES ÉVITÉS", f"{st.dodged}", "shield", CYAN), ("FRÔLEMENTS", f"{st.near_misses}", "bolt", VIOLET))
        gx, gw = W / 2 - 16, 400
        for i, (lab, v, ic, ccol) in enumerate(items):
            q = stagger(t, i, .09, .4) if t > .5 else 0
            q = stagger(t - .5, i, .09, .4)
            c.alpha = q
            x, y = gx + (i % 2) * (gw + 16) + 40 * (1 - q), sy + (i // 2) * 93
            c.glass(x, y, gw, 84, (.03, .05, .11, .62), 16, 1.3, alpha(ccol, .32))
            icons.draw(c, ic, x + 46, y + 42, 38, ccol)
            c.text(x + 86, y + 27, lab, 15, MUTED, "text", spacing=1)
            c.text(x + 86, y + 57, v, 31, WHITE)
        # récompenses
        c.alpha = ease_out((t - 1.1) / .5)
        ry, rh = 540, H - 540 - 168
        c.glass(sx, ry, 1600, rh, (.03, .05, .11, .62), 30, 1.5, alpha(GOLD, .35))
        c.text(sx + 46, ry + 44, "RÉCOMPENSES", 24, WHITE, color2=GOLD, spacing=3)
        chips = [("coin", f"+{fmt(r.coins)}", "pièces ramassées", GOLD), ("star", f"+{fmt(r.xp)} XP", "expérience", VIOLET)]
        if r.level_bonus:
            chips.append(("trophy", f"+{fmt(r.level_bonus)}", "bonus de niveau", CYAN))
        if r.bonus_coins:
            chips.append(("flag", f"+{fmt(r.bonus_coins)}", "pièces des succès", GREEN))
        x = sx + 46
        for i, (ic, v, sub, ccol) in enumerate(chips):
            q = ease_back((t - 1.3 - i * .18) / .35)
            if q <= 0:
                continue
            icons.draw(c, ic, x + 26, ry + 108, 46 * q, ccol)
            c.text(x + 62, ry + 98, v, 32, WHITE, glow=.4, glow_col=ccol)
            c.text(x + 62, ry + 128, sub, 16, MUTED, "text")
            x += 260
        # barre d'expérience
        bx, bw = sx + 1600 - 46 - 420, 420
        up = r.level_after > r.level_before
        c.text(bx, ry + 84, f"NIVEAU {r.level_after}", 26, WHITE, color2=CYAN, glow=.6 if up else .2, glow_col=CYAN)
        c.text(bx + bw, ry + 84, rank(r.level_after), 16, MUTED, "text", "r")
        c.bar(bx, ry + 108, bw, 16, r.xp_into / r.xp_need * ease_out((t - 1.5) / 1.0), CYAN, VIOLET, (.09, .13, .22, .9), 30, 5, -.2)
        c.text(bx + bw, ry + 146, f"{fmt(r.xp_into)} / {fmt(r.xp_need)} XP", 15, MUTED, "text", "r")
        if up and t > 2.6:
            c.text(bx, ry + 146, "NIVEAU SUPÉRIEUR !", 17, alpha(GREEN, .6 + .4 * math.sin(t * 6)))
        ax = sx + 46
        for i, ach in enumerate(r.achievements[:4]):
            q = ease_out((t - 2.2 - i * .35) / .4)
            if q <= 0:
                continue
            c.alpha = q
            wd = 366
            c.panel(ax, ry + rh - 92 + 20 * (1 - q), wd, 70, (.20, .14, .02, .72), (.08, .06, .02, .7), 14, 1.5, alpha(GOLD, .8), 14)
            icons.draw(c, ach.icon, ax + 42, ry + rh - 57, 38, GOLD)
            c.text(ax + 76, ry + rh - 71, ach.name, 19, WHITE, max_w=wd - 96)
            c.text(ax + 76, ry + rh - 43, f"Succès · +{ach.reward} pièces", 15, GOLD, "text")
            ax += wd + 16
        if len(r.achievements) > 4:
            c.text(sx + 1600 - 46, ry + 40, f"+{len(r.achievements) - 4} autres succès", 16, GOLD, "text", "r")
        c.alpha = 1
        self.group.draw(c, t)
        if r.record:
            self._record(c, t - RECORD_AT, W, H)

    def _record(self, c, t, W, H):
        """Bannière NEW RECORD : éclair, anneaux, confettis lumineux."""
        if t < 0:
            return
        fl = clamp(1 - t / .35)
        if fl > 0:
            c.rect(0, 0, W, H, alpha(WHITE, fl * .55))
        cx, cy = W / 2, 240
        for i in range(3):
            q = (t - i * .16) / 1.1
            if 0 < q < 1:
                c.arc(cx, cy + 120, 80 + 900 * ease_out(q), 10 * (1 - q) + 1, 0, math.tau * .999, alpha(GOLD, 1 - q), alpha(RED, 1 - q), 0, 1)
        for i, (a, b, d, e, f) in enumerate(self.conf):
            life = t - d * .5
            if life < 0 or life > 4.5:
                continue
            ang, sp = a * math.tau, 300 + 900 * b
            x = cx + math.cos(ang) * sp * (1 - math.exp(-1.6 * life)) * .9
            y = cy + 120 + math.sin(ang) * sp * .5 * (1 - math.exp(-1.6 * life)) + 120 * life * life * (.3 + e)
            col = (GOLD, CYAN, RED, VIOLET, WHITE)[i % 5]
            s = 7 + 12 * f
            c.panel(x, y, s, s * (.35 + .65 * abs(math.sin(life * 7 + i))), alpha(col, clamp(4.5 - life)), None, 2, 0, alpha(col, .8), 8, 1, 0, False, life * 4 + i)
        k = ease_back(t / .45)
        out = clamp((4.4 - t) / .5)
        if out > 0:
            c.alpha = out
            pulse = 1 + .03 * math.sin(t * 9)
            bw = 980 * k
            c.panel(cx - bw / 2, cy + 60, bw, 150, (.16, .10, .01, .92), (.22, .03, .06, .92), 34, 3, GOLD, 60, 1, -.16)
            sw = ((t * .8) % 1.6) / 1.2
            if sw < 1:
                c.rect(cx - bw / 2 + bw * sw, cy + 62, 80, 146, alpha(WHITE, 0), alpha(WHITE, .35), True, skew=-.16)
            c.text(cx, cy + 136, "NEW RECORD", 104 * k * pulse, WHITE, color2=GOLD, align="c", glow=1.0, glow_col=GOLD, skew=.16, spacing=6)
            c.alpha = 1
