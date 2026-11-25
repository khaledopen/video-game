"""Tableau de bord en jeu : compteur, nitro, vie, score, bonus, alertes."""
from __future__ import annotations

import math

from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, hexc, mix
from effects.animation import Counter, Spring, ease_back, ease_out
from engine.mathx import clamp, damp
from entities.obstacles import PICKUP_COLORS, PICKUP_NAMES
from entities.player import BONUS_TIME
from entities.world import LEVEL_LENGTH
from ui import icons

BONUS_ICON = {"shield": "shield", "magnet": "magnet", "multi": "multi", "slow": "slow"}
A0, A1 = math.radians(-128), math.radians(128)


def fmt(n) -> str:
    return f"{int(n):,}".replace(",", " ")


class Popup:
    def __init__(self, text, color, size=34, sub=""):
        self.text, self.color, self.size, self.sub, self.t = text, color, size, sub, 0.0


class HUD:
    def __init__(self, accent=CYAN):
        self.accent = accent
        self.speed = Counter(0, 12)
        self.score = Counter(0, 10)
        self.coins = 0
        self.coin_pop = Spring(0, 340, 18)
        self.hp = 1.0
        self.hp_lag = 1.0
        self.nitro = .5
        self.popups: list[Popup] = []
        self.banner: Popup | None = None
        self.hurt = 0.0
        self.vis = 0.0
        self.combo_pop = Spring(0, 340, 16)
        self.warn = 0.0
        self.gear = 1

    def popup(self, text, color, size=34, sub=""):
        self.popups.append(Popup(text, color, size, sub))
        del self.popups[:-4]

    def show_banner(self, text, sub, color):
        self.banner = Popup(text, color, 64, sub)

    def on_event(self, e, world):
        if e.kind == "near_miss":
            self.combo_pop.d = 14
            self.popup(f"FRÔLEMENT  +{e.data}", CYAN, 30, f"COMBO ×{world.combo}" if world.combo > 1 else "")
        elif e.kind == "coin":
            self.coin_pop.d = 10
        elif e.kind == "pickup":
            self.popup(PICKUP_NAMES[e.data], hexc(PICKUP_COLORS[e.data]), 36)
        elif e.kind in ("crash", "bump"):
            self.hurt = max(self.hurt, .5 + .5 * e.power)
        elif e.kind == "time_penalty":
            self.popup("−2 SECONDES", RED, 34)
        elif e.kind == "level":
            self.show_banner(f"NIVEAU {e.data}", "La circulation s'intensifie", CYAN)
        elif e.kind == "environment":
            self.show_banner(e.data.name, e.data.subtitle, hexc(e.data.accent))

    def update(self, dt, world):
        p = world.player
        self.vis = damp(self.vis, 1.0, 4, dt)
        self.speed.update(p.v * 3.6, dt)
        self.score.update(world.stats.score, dt)
        self.hp = damp(self.hp, p.hp / 100, 12, dt)
        self.hp_lag = damp(self.hp_lag, p.hp / 100, 2.2, dt) if self.hp_lag > p.hp / 100 else p.hp / 100
        self.nitro = damp(self.nitro, p.nitro, 14, dt)
        self.hurt = max(0.0, self.hurt - dt * 1.5)
        self.coin_pop.update(dt)
        self.combo_pop.update(dt)
        self.warn = damp(self.warn, 1.0 if p.hp < 28 and p.alive else 0.0, 5, dt)
        for q in self.popups:
            q.t += dt
        self.popups = [q for q in self.popups if q.t < 1.5]
        if self.banner:
            self.banner.t += dt
            if self.banner.t > 3.0:
                self.banner = None

    # -- dessin ------------------------------------------------------------------------------
    def draw(self, c, world, t, pause_button=None):
        W, H = c.W, c.H
        p, st = world.player, world.stats
        off = (1 - ease_out(self.vis)) * 160
        self._edges(c, W, H, t)
        # -- score (haut gauche) --
        c.oy = -off
        c.glass(46, 34, 372, 112, (.025, .045, .095, .50), 20, 1.4, alpha(CYAN, .30))
        c.text(72, 60, "SCORE", 15, MUTED, "text", spacing=3)
        c.text(72, 103, fmt(self.score.v), 50, WHITE, color2=(.68, .90, 1, 1), glow=.35, glow_col=CYAN, mono=True, max_w=230)
        mult = world.multiplier
        if mult > 1.01:
            k = 1 + .14 * clamp(self.combo_pop.v, -.5, 1)
            col = GOLD if p.active("multi") else CYAN
            c.text(392, 100, f"×{mult:.1f}", 34 * k, col, align="r", glow=.7, glow_col=col)
            if world.combo:
                c.bar(300, 124, 92, 5, world.combo_t / 5.0, col, WHITE, (.1, .14, .22, .6), 0, 2)
        # -- distance et niveau (haut centre) --
        bw = 420
        bx = W / 2 - bw / 2
        c.panel(bx, 30, bw, 62, (.025, .045, .095, .58), None, 18, 1.3, alpha(WHITE, .14), 0, 0)
        lv = (p.s % LEVEL_LENGTH) / LEVEL_LENGTH
        dist = f"{p.s / 1000:.2f} KM"
        c.text(W / 2, 54, dist, 28, WHITE, align="c", mono=True)
        c.text(bx + 24, 54, f"NIV {st.level}", 20, CYAN)
        c.text(bx + bw - 24, 54, world.env.name, 15, hexc(world.env.accent), "text", "r", max_w=112)
        c.bar(bx + 22, 76, bw - 44, 5, lv, CYAN, VIOLET, (.10, .14, .22, .7), 0, 2)
        if world.mode.time_limit:
            tl = world.time_left
            low = tl < 10
            col = mix(GOLD, RED, 1 if low else 0)
            k = 1 + (.10 * max(0, math.sin(t * 12)) if low else 0)
            c.text(W / 2, 134, f"{int(tl // 60)}:{tl % 60:04.1f}", 52 * k, WHITE, color2=col, align="c", glow=.8, glow_col=col, mono=True)
        # -- pièces (haut droite) --
        s = fmt(st.coins)
        w = c.measure(s, 32, mono=True) + 86
        rx = W - 46 - (78 if pause_button else 0)
        c.glass(rx - w, 34, w, 58, (.025, .045, .095, .50), 14, 1.4, alpha(GOLD, .35))
        icons.draw(c, "coin", rx - w + 34, 63, 32 * (1 + .35 * clamp(self.coin_pop.v, -.4, 1)), GOLD)
        c.text(rx - 22, 63, s, 32, WHITE, align="r", mono=True)
        c.oy = 0
        if pause_button:
            pause_button.draw(c, t)
        c.oy = off
        self._cluster(c, W, H, p, t)
        self._health(c, W, H, world, t)
        c.oy = 0
        self._messages(c, W, H, t)

    def _edges(self, c, W, H, t):
        """Voiles rouges : choc récent ou vie critique."""
        k = max(self.hurt * .75, self.warn * (.28 + .16 * math.sin(t * 6)))
        if k > .01:
            col = alpha(RED, k * .55)
            off = alpha(RED, 0)
            c.rect(0, 0, 190, H, col, off, True)
            c.rect(W - 190, 0, 190, H, off, col, True)
            c.rect(0, H - 110, W, 110, off, alpha(RED, k * .4))

    def _cluster(self, c, W, H, p, t):
        """Combiné numérique en bas à droite."""
        cx, cy, r = W - 214, H - 196, 142
        ratio = clamp(self.speed.v / (p.top * 3.6 * 1.28))
        hot = clamp((ratio - .74) / .26)
        col = mix(CYAN, RED, hot) if not p.nitro_on else mix(CYAN, WHITE, .3 + .3 * math.sin(t * 22))
        c.circle(cx, cy, r + 34, (.018, .032, .075, .58), 1.4, alpha(CYAN, .22), 18)
        c.arc(cx, cy, r, 18, A0, A1, (.09, .13, .23, .80), (.16, .07, .14, .80), 40)
        c.arc(cx, cy, r, 18, A0, A0 + (A1 - A0) * ratio, mix(VIOLET, CYAN, clamp(ratio * 1.6)), col, 0, 1)
        a = A0 + (A1 - A0) * ratio
        tip = (cx + math.sin(a) * (r + 13), cy - math.cos(a) * (r + 13))
        c.line(cx + math.sin(a) * (r - 34), cy - math.cos(a) * (r - 34), *tip, alpha(col, .15), 4, WHITE)
        c.halo(*tip, 34, alpha(col, .8))
        top = int(p.top * 3.6 * 1.28 / 50) * 50
        for i in range(0, top + 1, 50):
            q = A0 + (A1 - A0) * clamp(i / (p.top * 3.6 * 1.28))
            c.text(cx + math.sin(q) * (r - 31), cy - math.cos(q) * (r - 31), str(i), 13, alpha(MUTED, .9 if i % 100 == 0 else .45), "text", "c")
        # nitro : arc intérieur
        c.arc(cx, cy, r - 54, 8, A0, A1, (.08, .11, .20, .85), None, 12)
        ncol = VIOLET if not p.nitro_on else WHITE
        c.arc(cx, cy, r - 54, 8, A0, A0 + (A1 - A0) * self.nitro, ncol, CYAN, 12, 1 if self.nitro > .95 or p.nitro_on else .4)
        c.text(cx, cy - 10, str(int(self.speed.v)), 56, WHITE, color2=mix(WHITE, col, .55), align="c", glow=.45 + .4 * hot, glow_col=col, mono=True)
        c.text(cx, cy + 38, "KM/H", 18, MUTED, "text", "c", spacing=3)
        gear = min(6, 1 + int(ratio * 6.2)) if p.spec.engine != "electric" else "E"
        c.text(cx, cy + 84, str(gear), 38, col, align="c")
        ready = self.nitro > .06
        icons.draw(c, "nitro", cx - 58, cy + 88, 26, alpha(CYAN if ready else MUTED, .55 + .45 * (math.sin(t * 5) if self.nitro > .95 else 0)))
        c.text(cx + 40, cy + 90, f"{round(self.nitro * 100)}", 20, WHITE if ready else MUTED, mono=True)

    def _health(self, c, W, H, world, t):
        """Vie et bonus actifs en bas à gauche."""
        p = world.player
        x, y = 46, H - 118
        c.glass(x, y, 430, 78, (.025, .045, .095, .52), 18, 1.4, alpha(RED if self.warn > .5 else CYAN, .30 + .4 * self.warn))
        beat = 1 + (.16 * max(0, math.sin(t * 9)) if self.warn > .5 else 0)
        col = mix(RED, GREEN, clamp((self.hp - .2) / .5))
        if self.hp > .55:
            col = mix(GREEN, CYAN, clamp((self.hp - .55) / .45))
        icons.draw(c, "heart", x + 40, y + 39, 38 * beat, col)
        bx, bw = x + 76, 240
        c.bar(bx, y + 28, bw, 22, self.hp_lag, alpha(RED, .75), alpha(RED, .75), (.09, .12, .20, .85), 20, 6, -.3)
        c.bar(bx, y + 28, bw, 22, self.hp, col, mix(col, WHITE, .25), (0, 0, 0, 0), 20, 6, -.3)
        c.text(x + 408, y + 39, f"{math.ceil(max(0, p.hp)):d}", 30, WHITE, align="r", mono=True)
        # bonus actifs
        i = 0
        for k, total in BONUS_TIME.items():
            left = p.timers[k]
            if left <= 0:
                continue
            cx, cy = x + 42 + i * 92, y - 56
            bc = hexc(PICKUP_COLORS[k])
            blink = 1.0 if left > 2 else .45 + .55 * (math.sin(t * 14) > 0)
            c.circle(cx, cy, 36, (.03, .05, .11, .75), 0, alpha(bc, .9), 8)
            c.arc(cx, cy, 34, 6, 0, math.tau * .999, (.1, .14, .22, .8))
            c.arc(cx, cy, 34, 6, 0, math.tau * clamp(left / total) * .999, bc, WHITE, 0, 1)
            icons.draw(c, BONUS_ICON[k], cx, cy, 34, alpha(WHITE, blink))
            i += 1

    def _messages(self, c, W, H, t):
        y = H * .34
        for q in reversed(self.popups):
            k = ease_back(q.t / .22)
            a = clamp((1.5 - q.t) / .4)
            c.text(W / 2, y - q.t * 34, q.text, max(8, q.size * k), alpha(WHITE, a), color2=alpha(q.color, a), align="c", glow=.8 * a, glow_col=q.color, skew=.14, spacing=2)
            if q.sub:
                c.text(W / 2, y + 34 - q.t * 34, q.sub, 22, alpha(q.color, a), align="c", spacing=2)
            y -= 62
        b = self.banner
        if b:
            a = ease_out(b.t / .4) * clamp((3.0 - b.t) / .5)
            yy = H * .20
            w = 520 * ease_out(b.t / .6)
            c.alpha = a
            c.panel(W / 2 - w, yy - 58, 2 * w, 132, (.01, .02, .05, 0), (.01, .02, .05, .0), 0, 0)
            c.rect(W / 2 - w, yy - 56, w, 126, (.01, .02, .05, 0), (.01, .02, .05, .62), True)
            c.rect(W / 2, yy - 56, w, 126, (.01, .02, .05, .62), (.01, .02, .05, 0), True)
            c.rect(W / 2 - w, yy - 57, 2 * w, 2, alpha(b.color, .8))
            c.rect(W / 2 - w, yy + 70, 2 * w, 2, alpha(b.color, .8))
            c.text(W / 2, yy - 6, b.text, b.size, WHITE, color2=b.color, align="c", glow=.9, glow_col=b.color, skew=.16, spacing=8 * ease_out(b.t / .8))
            c.text(W / 2, yy + 46, b.sub, 22, (.82, .9, 1, 1), "text", "c")
            c.alpha = 1
