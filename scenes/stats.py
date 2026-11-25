"""Statistiques, courbe des scores et succès."""
from __future__ import annotations

import math

import pygame

from config.modes import MODES
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, hexc, mix
from core.progression import ACHIEVEMENTS, level_from_xp, rank
from core.scene_manager import Scene
from effects.animation import ease_out, stagger
from engine.mathx import clamp
from scenes import backdrop
from ui import icons
from ui.hud import fmt
from ui.widgets import Button, Group, header


def duration(s: float) -> str:
    s = int(s)
    return f"{s // 3600} h {s % 3600 // 60:02d}" if s >= 3600 else f"{s // 60} min {s % 60:02d}"


class StatsScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        st = app.store
        self.tot = st.totals()
        self.recent = list(reversed(st.recent(24)))
        self.done = st.achievements()
        self.level, self.xp, self.need = level_from_xp(st.get("xp"))
        self.modes = st.per_mode()
        self.owned = len(st.unlocked())
        self.page = 0
        self.tabs = [Button("VUE D'ENSEMBLE", lambda: self.set_page(0), icon="chart", color=CYAN, w=330, h=58, size=20),
                     Button(f"SUCCÈS  {len(self.done)} / {len(ACHIEVEMENTS)}", lambda: self.set_page(1), icon="star", color=GOLD, w=330, h=58, size=20)]
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=230, sound="ui_back")
        self.group = Group(app, [*self.tabs, self.back_btn])
        self.pt = 0.0
        self.resized()

    def enter(self):
        super().enter()
        self.backdrop.set_shot("side")

    def resized(self):
        W = self.app.canvas.W
        for i, b in enumerate(self.tabs):
            b.x, b.y = W - 90 - 2 * 350 - 260 + i * 350, 62
        self.back_btn.x, self.back_btn.y = W - 90 - 230, 60

    def set_page(self, i):
        self.page, self.pt = i, 0.0

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
        self.pt += dt
        self.backdrop.update(dt)
        self.group.update(dt)
        for i, b in enumerate(self.tabs):
            b.selected = i == self.page

    def draw(self, c):
        self.backdrop.draw(fade=.36)
        c.rect(0, 0, c.W, c.H, (.01, .016, .04, .35), (.01, .016, .04, .65))
        header(c, self.t, "STATISTIQUES", "Votre carrière en chiffres", GREEN, ease_out(self.t / .5))
        self.group.draw(c, self.t)
        (self._overview if self.page == 0 else self._achievements)(c)
        c.alpha = 1

    def _overview(self, c):
        T, t, W, H = self.tot, self.pt, c.W, c.H
        m, gap = 90, 22
        tiles = (("MEILLEUR SCORE", fmt(T["best"]), "trophy", GOLD), ("DISTANCE TOTALE", f"{T['distance'] / 1000:.1f} km", "road", CYAN), ("PARTIES", fmt(T["games"]), "flag", VIOLET),
                 ("TEMPS DE JEU", duration(T["time"]), "clock", GREEN), ("VITESSE RECORD", f"{T['top_speed']:.0f} km/h", "speed", RED), ("PIÈCES RAMASSÉES", fmt(T["coins"]), "coin", GOLD),
                 ("OBSTACLES ÉVITÉS", fmt(T["dodged"]), "shield", CYAN), ("FRÔLEMENTS", fmt(T["near_misses"]), "bolt", VIOLET))
        w = (W - 2 * m - 3 * gap) / 4
        for i, (lab, val, ic, col) in enumerate(tiles):
            a = stagger(t, i, .05, .45)
            c.alpha = a
            x, y = m + (i % 4) * (w + gap), 220 + (i // 4) * 144 + 30 * (1 - a)
            c.glass(x, y, w, 122, (.03, .05, .105, .62), 20, 1.4, alpha(col, .35))
            c.halo(x + 62, y + 61, 70, alpha(col, .20))
            icons.draw(c, ic, x + 62, y + 61, 52, col)
            c.text(x + 118, y + 40, lab, 15, MUTED, "text", spacing=1)
            c.text(x + 118, y + 80, val, 36, WHITE, max_w=w - 140)
        # courbe
        c.alpha = stagger(t, 8, .05, .5)
        x, y, gw, gh = m, 530, (W - 2 * m) * .60, H - 530 - 60
        c.glass(x, y, gw, gh, (.03, .05, .105, .62), 24, 1.4, alpha(CYAN, .30))
        c.text(x + 34, y + 40, "SCORES DES DERNIÈRES PARTIES", 19, WHITE, spacing=1)
        pts = [r.score for r in self.recent]
        if len(pts) >= 2:
            top = max(max(pts), 1)
            px0, py0, pw, ph = x + 92, y + 78, gw - 130, gh - 124
            for i in range(5):
                yy = py0 + ph * i / 4
                c.rect(px0, yy, pw, 1, alpha(WHITE, .09))
                c.text(px0 - 14, yy, fmt(top * (1 - i / 4)), 14, MUTED, "text", "r")
            prog = ease_out(t / 1.2)
            P = [(px0 + pw * i / (len(pts) - 1), py0 + ph * (1 - v / top * prog)) for i, v in enumerate(pts)]
            for i in range(len(P) - 1):
                (x0, y0), (x1, y1) = P[i], P[i + 1]
                n = 8
                for k in range(n):
                    xa, xb = x0 + (x1 - x0) * k / n, x0 + (x1 - x0) * (k + 1) / n
                    ya = y0 + (y1 - y0) * (k + .5) / n
                    c.rect(xa, ya, xb - xa + .6, py0 + ph - ya, alpha(CYAN, .26), alpha(VIOLET, .02))
            for i in range(len(P) - 1):
                c.line(*P[i], *P[i + 1], CYAN, 3, CYAN)
            for p, v in zip(P, pts):
                best = v == top
                c.circle(*p, 7 if best else 5, GOLD if best else WHITE, 2, alpha(GOLD if best else CYAN, 1), 12)
        else:
            c.text(x + gw / 2, y + gh / 2, "Jouez au moins deux parties pour tracer la courbe", 20, MUTED, "text", "c")
        # modes et niveau
        x2, w2 = x + gw + gap, (W - 2 * m) * .40 - gap
        c.glass(x2, y, w2, gh, (.03, .05, .105, .62), 24, 1.4, alpha(VIOLET, .30))
        cx, cy = x2 + 110, y + 112
        c.arc(cx, cy, 66, 10, 0, math.tau * .999, (.10, .14, .24, .9))
        c.arc(cx, cy, 66, 10, 0, math.tau * max(.01, self.xp / self.need * ease_out(t / 1.0)) * .999, CYAN, VIOLET, glow=1)
        c.text(cx, cy - 4, str(self.level), 48, WHITE, align="c")
        c.text(cx, cy + 32, "NIVEAU", 13, MUTED, "text", "c")
        c.text(x2 + 204, y + 82, rank(self.level), 30, WHITE, color2=VIOLET, glow=.5, glow_col=VIOLET, max_w=w2 - 230)
        c.text(x2 + 204, y + 120, f"{fmt(self.xp)} / {fmt(self.need)} XP", 19, MUTED, "text")
        c.text(x2 + 204, y + 148, f"{self.owned} véhicules possédés", 17, MUTED, "text")
        yy = y + 216
        row = min(54., (gh - 236) / 5)
        mx = max([self.modes[m_.id][2] for m_ in MODES if m_.id in self.modes] + [1])
        for md in MODES:
            n, bs, ds = self.modes.get(md.id, (0, 0, 0))
            col = hexc(md.color)
            icons.draw(c, md.icon, x2 + 46, yy, 26, col)
            c.text(x2 + 74, yy - 7, md.name, 16, WHITE)
            c.text(x2 + w2 - 30, yy - 7, f"{n} parties · {fmt(bs or 0)}", 15, MUTED, "text", "r")
            c.bar(x2 + 74, yy + 8, w2 - 104, 6, ds / mx * ease_out(t / 1.2), col, WHITE, (.1, .14, .22, .7), 0, 2)
            yy += row

    def _achievements(self, c):
        W, H, m, gap = c.W, c.H, 90, 16
        cols = 4
        w = (W - 2 * m - (cols - 1) * gap) / cols
        rows = math.ceil(len(ACHIEVEMENTS) / cols)
        h = min(124., (H - 220 - 60) / rows - gap)
        for i, a in enumerate(ACHIEVEMENTS):
            k = stagger(self.pt, i, .022, .4)
            if k <= 0:
                continue
            c.alpha = k
            ok = a.id in self.done
            col = GOLD if ok else (.36, .43, .56, 1)
            x, y = m + (i % cols) * (w + gap), 220 + (i // cols) * (h + gap) + 24 * (1 - k)
            c.panel(x, y, w, h, mix((.035, .055, .11, .78), (*col[:3], .6), .14 if ok else .02), (.02, .03, .07, .78), 18, 1.4, alpha(col, .7 if ok else .22), 10 if ok else 0)
            if ok:
                c.halo(x + 54, y + h / 2, 62, alpha(GOLD, .28))
            icons.draw(c, a.icon if ok else "lock", x + 54, y + h / 2, 44, col)
            c.text(x + 100, y + h * .28, a.name, 20, WHITE if ok else (.62, .70, .82, 1), max_w=w - 116)
            c.text(x + 100, y + h * .54, a.description, 15.5, MUTED, "text", max_w=w - 116)
            icons.draw(c, "coin", x + 109, y + h * .79, 18, alpha(GOLD, 1 if ok else .5))
            c.text(x + 124, y + h * .79, f"{a.reward}", 15, alpha(GOLD, 1 if ok else .6))
            if ok:
                c.text(x + w - 18, y + h * .79, "OBTENU", 13, GREEN, "text", "r")


__all__ = ["StatsScene", "clamp"]
