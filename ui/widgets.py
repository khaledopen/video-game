"""Composants d'interface animés : boutons, curseurs, sélecteurs, raccourcis clavier."""
from __future__ import annotations

import math

import pygame

from config.palette import CYAN, FAINT, MUTED, NIGHT, RED, VIOLET, WHITE, alpha, mix
from config.settings import key_label
from effects.animation import Spring, ease_out
from engine.mathx import clamp, damp
from ui import icons

PANEL = (.035, .058, .115, .70)


class Widget:
    focusable = True

    def __init__(self, x=0., y=0., w=100., h=50.):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.hover = Spring(0.0, 300, 24)
        self.press = 0.0
        self.focused = False
        self.selected = False      # onglet actif
        self.enabled = True
        self.visible = True
        self.appear = 1.0
        self.slide = (0.0, 0.0)

    def contains(self, mx, my) -> bool:
        return self.x <= mx <= self.x + self.w and self.y <= my <= self.y + self.h

    def update(self, dt):
        self.hover.t = 1.0 if self.focused and self.enabled else .75 if self.selected else 0.0
        self.hover.update(dt)
        self.press = max(0.0, self.press - dt * 3.2)

    # interactions : retourne True si l'événement est consommé
    def click(self, app, mx, my) -> bool:
        return False

    def drag(self, app, mx, my):
        pass

    def adjust(self, app, direction: int) -> bool:
        return False

    def draw(self, c, t):
        raise NotImplementedError


class Button(Widget):
    def __init__(self, label, callback, x=0., y=0., w=360., h=62., icon="", color=CYAN, sub="", size=26, sound="ui_click", primary=False, align="l"):
        super().__init__(x, y, w, h)
        self.label, self.callback, self.icon, self.color, self.sub = label, callback, icon, color, sub
        self.size, self.sound, self.primary, self.align = size, sound, primary, align
        self.phase = (x * 13 + y * 7) % 10
        self.note = ""
        self.sweep = 0.0

    def click(self, app, mx, my):
        self.press = 1.0
        if not self.enabled:
            app.audio.play("ui_denied", .7)
            return True
        app.audio.play(self.sound, .8)
        self.callback()
        return True

    def update(self, dt):
        was = self.hover.t
        super().update(dt)
        if self.hover.t > was:
            self.sweep = 0.0
        self.sweep += dt

    def draw(self, c, t):
        h = clamp(self.hover.v, 0, 1.15)
        a = self.appear
        if a <= .003:
            return
        c.alpha *= a
        x, y = self.x + self.slide[0] * (1 - a) + 12 * h, self.y + self.slide[1] * (1 - a)
        w, ht = self.w, self.h
        col = self.color if self.enabled else FAINT
        pr = self.press
        k = 1 - .03 * math.sin(pr * math.pi)
        x, y, w, ht = x + w * (1 - k) / 2, y + ht * (1 - k) / 2, w * k, ht * k
        sk = -.16
        base = mix(PANEL, (*col[:3], .34), .16 + .50 * h + (.35 if self.primary else 0))
        edge = alpha(col, .30 + .65 * clamp(h) + (.3 if self.primary else 0))
        c.panel(x, y, w, ht, (*base[:3], .80), (*[v * .55 for v in base[:3]], .72), 12, 1.4 + .8 * h, edge, 4 + 20 * h + (8 + 4 * math.sin(t * 3) if self.primary else 0), 1, sk)
        c.rect(x + 7, y + ht * .22, 4 + 2 * h, ht * .56, alpha(col, .55 + .45 * clamp(h)), skew=sk)
        # balayage lumineux
        s = self.sweep * 1.9
        if h > .05 and s < 1.25:
            sx = x + w * (s - .12)
            if x < sx < x + w - 46:
                c.panel(sx, y + 2, 46, ht - 4, (1, 1, 1, 0), (1, 1, 1, .16 * h), 0, 0, (0, 0, 0, 0), 0, 2, sk, True)
        if pr > 0:
            c.panel(x - 30 * (1 - pr), y - 12 * (1 - pr), w + 60 * (1 - pr), ht + 24 * (1 - pr), (0, 0, 0, 0), None, 14, 2, alpha(col, pr * .8), 0, 1, sk)
        tc = mix(MUTED if not self.enabled else (.86, .92, 1., 1.), WHITE, clamp(h))
        tx = x + 34
        if self.icon:
            icons.draw(c, self.icon, x + 48, y + ht / 2, 30 + 4 * h, alpha(mix(col, WHITE, .25 * clamp(h)), .95))
            tx = x + 84
        cy = y + ht / 2 - (9 if self.sub else 0)
        if self.align == "c":
            c.text(x + w / 2 + (18 if self.icon else 0), cy, self.label, self.size, tc, align="c", glow=.55 * h, glow_col=col, spacing=1.5 + h, max_w=w - 60)
        else:
            c.text(tx, cy, self.label, self.size, tc, glow=.55 * h, glow_col=col, spacing=1.5 + h, max_w=w - (tx - x) - 24)
        if self.sub:
            c.text(tx, y + ht / 2 + 18, self.sub, 17, alpha(MUTED, .9), "text", max_w=w - (tx - x) - 24)
        if self.note:
            c.text(x + w - 24, y + ht / 2, self.note, 18, alpha(col, .9), "text", "r")
        c.alpha /= a


class IconButton(Widget):
    def __init__(self, icon, callback, x=0., y=0., size=58., color=CYAN, sound="ui_click", rot=0.):
        super().__init__(x, y, size, size)
        self.icon, self.callback, self.color, self.sound, self.rot = icon, callback, color, sound, rot

    def click(self, app, mx, my):
        self.press = 1.0
        app.audio.play(self.sound, .8)
        self.callback()
        return True

    def draw(self, c, t):
        h, a = clamp(self.hover.v), self.appear
        c.alpha *= a
        c.panel(self.x, self.y, self.w, self.h, mix((.04, .07, .14, .72), (*self.color[:3], .55), h * .6), None, 12, 1.5, alpha(self.color, .35 + .6 * h), 14 * h, 0)
        icons.draw(c, self.icon, self.x + self.w / 2, self.y + self.h / 2, self.w * (.46 + .05 * h), mix((.8, .9, 1, 1), WHITE, h), self.rot)
        c.alpha /= max(a, 1e-3)


class Row(Widget):
    """Ligne de réglage : libellé à gauche, contrôle à droite."""

    def __init__(self, label, x, y, w, h=58., hint=""):
        super().__init__(x, y, w, h)
        self.label, self.hint = label, hint

    def back(self, c, color=CYAN):
        h = clamp(self.hover.v)
        c.panel(self.x, self.y, self.w, self.h, mix((.04, .065, .125, .52), (*color[:3], .20), h * .55), None, 10, 1.2, alpha(color, .12 + .6 * h), 10 * h)
        c.text(self.x + 24, self.y + self.h / 2, self.label, 23, mix((.78, .86, .97, 1), WHITE, h), "text")


class Slider(Row):
    def __init__(self, label, value, callback, x, y, w, lo=0., hi=1., step=.05, fmt=None, color=CYAN):
        super().__init__(label, x, y, w)
        self.value, self.callback, self.lo, self.hi, self.step, self.color = value, callback, lo, hi, step, color
        self.fmt = fmt or (lambda v: f"{round(v * 100)} %")
        self.vis = value

    def _bar(self):
        bw = self.w * .40
        return self.x + self.w - bw - 110, bw

    def _set(self, app, v, sound=True):
        v = round(clamp(v, self.lo, self.hi) / self.step) * self.step
        v = clamp(v, self.lo, self.hi)
        if abs(v - self.value) > 1e-6:
            self.value = v
            self.callback(v)
            if sound:
                app.audio.play("ui_hover", .6)

    def click(self, app, mx, my):
        self.drag(app, mx, my)
        return True

    def drag(self, app, mx, my):
        bx, bw = self._bar()
        self._set(app, self.lo + (mx - bx) / bw * (self.hi - self.lo))

    def adjust(self, app, direction):
        self._set(app, self.value + direction * self.step)
        return True

    def update(self, dt):
        super().update(dt)
        self.vis = damp(self.vis, self.value, 18, dt)

    def draw(self, c, t):
        self.back(c, self.color)
        bx, bw = self._bar()
        k = (self.vis - self.lo) / (self.hi - self.lo)
        cy = self.y + self.h / 2
        c.bar(bx, cy - 5, bw, 10, k, VIOLET, self.color, (.10, .14, .24, .9), 0, 5)
        h = clamp(self.hover.v)
        c.circle(bx + bw * k, cy, 10 + 2 * h, mix(self.color, WHITE, .55), 2, alpha(WHITE, .9), 12 + 8 * h)
        c.text(self.x + self.w - 24, cy, self.fmt(self.value), 21, WHITE, "text", "r")


class Selector(Row):
    def __init__(self, label, options, index, callback, x, y, w, color=CYAN):
        super().__init__(label, x, y, w)
        self.options, self.index, self.callback, self.color = options, index, callback, color
        self.shift = 0.0

    def _step(self, app, d):
        if not self.options:
            return
        self.index = (self.index + d) % len(self.options)
        self.shift = d
        app.audio.play("ui_hover", .8)
        self.callback(self.options[self.index], self.index)

    def click(self, app, mx, my):
        zone = self.x + self.w * .52
        self._step(app, -1 if zone < mx < zone + (self.x + self.w - zone) * .4 else 1)
        return True

    def adjust(self, app, direction):
        self._step(app, direction)
        return True

    def update(self, dt):
        super().update(dt)
        self.shift = damp(self.shift, 0, 14, dt)

    def draw(self, c, t):
        self.back(c, self.color)
        x0, x1 = self.x + self.w * .52, self.x + self.w - 26
        cy, h = self.y + self.h / 2, clamp(self.hover.v)
        c.triangle(x0, cy, 14, 18, alpha(self.color, .5 + .5 * h), math.pi)
        c.triangle(x1, cy, 14, 18, alpha(self.color, .5 + .5 * h))
        lab = str(self.options[self.index]) if self.options else "—"
        c.text((x0 + x1) / 2 + self.shift * 30, cy, lab, 22, alpha(WHITE, 1 - abs(self.shift) * .7), "text", "c", glow=.3 * h, glow_col=self.color, max_w=x1 - x0 - 50)


class Toggle(Row):
    def __init__(self, label, value, callback, x, y, w, color=CYAN):
        super().__init__(label, x, y, w)
        self.value, self.callback, self.color = value, callback, color
        self.vis = float(value)

    def click(self, app, mx, my):
        self.value = not self.value
        app.audio.play("ui_click", .6)
        self.callback(self.value)
        return True

    def adjust(self, app, direction):
        if (direction > 0) != self.value:
            self.click(app, 0, 0)
        return True

    def update(self, dt):
        super().update(dt)
        self.vis = damp(self.vis, float(self.value), 16, dt)

    def draw(self, c, t):
        self.back(c, self.color)
        x, cy, v = self.x + self.w - 104, self.y + self.h / 2, self.vis
        c.panel(x, cy - 15, 78, 30, mix((.10, .13, .22, .9), (*self.color[:3], .75), v), None, 15, 1.5, alpha(mix(MUTED, self.color, v), .7), 10 * v, 2)
        c.circle(x + 16 + 46 * v, cy, 11, mix(MUTED, WHITE, v), 0, alpha(self.color, .9), 8 * v)
        c.text(x - 16, cy, "ACTIVÉ" if self.value else "DÉSACTIVÉ", 17, mix(FAINT, WHITE, v), "text", "r")


class KeyBind(Row):
    def __init__(self, label, action, keys, callback, x, y, w):
        super().__init__(label, x, y, w)
        self.action, self.keys, self.callback = action, keys, callback
        self.waiting = -1

    def slot(self, mx):
        return 0 if mx < self.x + self.w - 170 else 1

    def click(self, app, mx, my):
        self.waiting = self.slot(mx) if mx else 0
        app.audio.play("ui_click", .7)
        return True

    def draw(self, c, t):
        self.back(c)
        for i in (0, 1):
            x = self.x + self.w - 320 + i * 156
            wait = self.waiting == i
            pulse = .5 + .5 * math.sin(t * 9)
            c.panel(x, self.y + 10, 144, self.h - 20, (.05, .09, .17, .9), None, 8, 1.5, alpha(RED if wait else CYAN, .4 + .5 * (pulse if wait else clamp(self.hover.v))), 12 if wait else 0)
            lab = "APPUYEZ…" if wait else key_label(self.keys[i] if i < len(self.keys) else "")
            c.text(x + 72, self.y + self.h / 2, lab, 18, WHITE if not wait else RED, "text", "c", max_w=130)


class Group:
    """Focus, souris et navigation clavier pour un ensemble de composants."""

    def __init__(self, app, widgets=()):
        self.app = app
        self.widgets: list[Widget] = list(widgets)
        self.focus: Widget | None = None
        self.dragging: Widget | None = None
        self.keyboard_mode = False
        self.travel = 0

    def active(self):
        return [w for w in self.widgets if w.visible and w.focusable]

    def set_focus(self, w, sound=True):
        if w is self.focus:
            return
        if self.focus:
            self.focus.focused = False
        self.focus = w
        if w:
            w.focused = True
            if sound:
                self.app.audio.play("ui_hover", .5)

    def event(self, e) -> bool:
        app = self.app
        if e.type == pygame.MOUSEMOTION:
            mx, my = app.canvas.to_virtual(e.pos)
            if self.dragging:
                self.dragging.drag(app, mx, my)
                return True
            # au clavier, un simple frémissement de la souris ne vole pas la sélection
            if self.keyboard_mode:
                self.travel += abs(e.rel[0]) + abs(e.rel[1])
                if self.travel < 24:
                    return False
            for w in reversed(self.active()):
                if w.contains(mx, my):
                    self.keyboard_mode = False
                    self.set_focus(w)
                    return True
            if not self.keyboard_mode:
                self.set_focus(None, False)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            mx, my = app.canvas.to_virtual(e.pos)
            for w in reversed(self.active()):
                if w.contains(mx, my):
                    self.set_focus(w, False)
                    if isinstance(w, Slider):
                        self.dragging = w
                    return w.click(app, mx, my)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.dragging = None
        elif e.type == pygame.KEYDOWN:
            d = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}.get(e.key)
            if d:
                self.keyboard_mode, self.travel = True, 0
                if d[0] and self.focus and self.focus.adjust(app, d[0]):
                    return True
                return self.move(*d)
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and self.focus and self.focus.visible:
                self.keyboard_mode = True
                return self.focus.click(app, 0, 0)
        return False

    def move(self, dx, dy) -> bool:
        ws = self.active()
        if not ws:
            return False
        if self.focus not in ws:
            self.set_focus(ws[0])
            return True
        f = self.focus
        fx, fy = f.x + f.w / 2, f.y + f.h / 2
        best, score = None, 1e9
        for w in ws:
            if w is f:
                continue
            ox, oy = w.x + w.w / 2 - fx, w.y + w.h / 2 - fy
            along = ox * dx + oy * dy
            if along <= 4:
                continue
            s = along + 2.4 * abs(ox * dy + oy * dx)
            if s < score:
                best, score = w, s
        if best:
            self.set_focus(best)
            return True
        return False

    def update(self, dt):
        for w in self.widgets:
            w.update(dt)

    def draw(self, c, t):
        for w in self.widgets:
            if w.visible:
                w.draw(c, t)

    def reveal(self, t, delay=.055, dur=.5, offset=(-90, 0), start=0.0):
        """Apparition décalée de tous les composants."""
        for i, w in enumerate(self.widgets):
            w.appear = ease_out((t - start - i * delay) / dur)
            w.slide = offset


def header(c, t, title, subtitle="", color=CYAN, a=1.0):
    """Titre d'écran avec liseré animé."""
    c.alpha *= a
    x = 90 - 40 * (1 - a)
    c.text(x, 92, title, 62, WHITE, color2=mix(WHITE, color, .55), glow=.5, glow_col=color, skew=.14, spacing=4)
    w = c.measure(title, 62, spacing=4)
    c.rect(x + 2, 140, w * a, 4, color, alpha(VIOLET, .1), True)
    c.rect(x + 2 + (w - 60) * ((t * .35) % 1.0), 138, 60, 8, alpha(WHITE, 0), alpha(WHITE, .7), True)
    if subtitle:
        c.text(x + 2, 170, subtitle, 22, MUTED, "text")
    c.alpha /= max(a, 1e-3)


def chip(c, x, y, icon, text, color, size=26, align="l"):
    """Étiquette icône + valeur ; retourne sa largeur."""
    w = c.measure(text, size) + 78
    if align == "r":
        x -= w
    c.glass(x, y - 26, w, 52, (.04, .07, .13, .66), 12, 1.4, alpha(color, .45))
    icons.draw(c, icon, x + 32, y, 28, color)
    c.text(x + 56, y, text, size, WHITE)
    return w
