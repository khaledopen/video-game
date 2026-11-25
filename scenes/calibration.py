"""Calibration du contrôle gestuel, avec essai en direct des commandes."""
from __future__ import annotations

import math

import pygame

from computer_vision.gestures import FIST, LABELS, OPEN, TWO, Calibrator
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, mix
from core.scene_manager import Scene
from effects.animation import ease_out
from engine.mathx import clamp, damp
from scenes import backdrop
from scenes.game import draw_camera
from ui import icons
from ui.widgets import Button, Group, header

STEP_TEXT = {"center": ("POSITION CENTRALE", "Placez votre main ouverte (ou vos deux mains comme sur un volant) au centre, puis restez immobile."),
             "left": ("À GAUCHE", "Déplacez la main vers la gauche, jusqu'à votre limite confortable, et restez immobile."),
             "right": ("À DROITE", "Même chose vers la droite.")}
GESTURES = ((OPEN, "MAIN OUVERTE", "Accélérer", GREEN), (FIST, "POING FERMÉ", "Ralentir", RED), (TWO, "DEUX DOIGTS", "Nitro", CYAN))


class CalibrationScene(Scene):
    def __init__(self, app, then: str = "game"):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        self.then = then
        self.ok, self.why = app.gesture.available()
        self.cal = Calibrator()
        self.done = False
        self.seq = -1
        self.steer_vis = 0.0
        self.tested = {OPEN: 0.0, FIST: 0.0, TWO: 0.0}
        self.start_btn = Button("COMMENCER" if then == "game" else "TERMINER", self.finish, icon="play", color=GREEN, w=400, h=72, primary=True, size=26)
        self.redo_btn = Button("RECALIBRER", self.redo, icon="retry", color=VIOLET, w=300)
        self.keep_btn = Button("GARDER LA CALIBRATION", self.keep, icon="check", color=CYAN, w=400)
        self.kbd_btn = Button("JOUER AU CLAVIER", self.keyboard, icon="keyboard", color=GOLD, w=340)
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=240, sound="ui_back")
        self.group = Group(app, [self.start_btn, self.redo_btn, self.keep_btn, self.kbd_btn, self.back_btn])
        self.resized()

    def enter(self):
        super().enter()
        self.backdrop.set_shot("wide")
        if self.ok:
            self.app.gesture.start()

    def leave(self):
        nxt = self.app.scenes.next
        if not (nxt and nxt[0] == "game" and nxt[1].get("mode_id") == "gesture"):
            self.app.gesture.stop()          # sinon la webcam reste ouverte pour la partie

    def resized(self):
        c = self.app.canvas
        y = c.H - 112
        self.back_btn.x, self.back_btn.y = 90, y
        self.kbd_btn.x, self.kbd_btn.y = 350, y
        self.start_btn.x, self.start_btn.y = c.W - 90 - 400, y - 5
        self.redo_btn.x, self.redo_btn.y = c.W - 90 - 400 - 320, y
        self.keep_btn.x, self.keep_btn.y = c.W - 90 - 400, y

    def finish(self):
        self.app.settings.save()
        if self.then == "game":
            self.app.scenes.go("game", mode_id="gesture")
        else:
            self.app.scenes.go("settings", tab=3)

    def keyboard(self):
        self.app.scenes.go("game", mode_id="endless")

    def back(self):
        self.app.scenes.go("modes" if self.then == "game" else "settings", **({} if self.then == "game" else {"tab": 3}))

    def redo(self):
        self.cal, self.done = Calibrator(), False

    def keep(self):
        self.done = True

    def event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.audio.play("ui_back", .7)
            self.back()
        else:
            self.group.event(e)

    def update(self, dt):
        super().update(dt)
        app, g = self.app, self.app.gesture
        self.backdrop.update(dt)
        c = g.update(dt)
        st = g.state
        self.steer_vis = damp(self.steer_vis, c.steer, 12, dt)
        running = g.status == "running"
        if running and not self.done:
            before = self.cal.step
            self.cal.update(dt, st)
            if self.cal.step != before:
                app.audio.play("pk_magnet" if not self.cal.done else "level_up", .7)
            if self.cal.done:
                self.done = True
                cal = self.cal.result()
                app.settings["gesture_calibration"] = cal.to_dict()
                app.settings.save()
                g.tracker.configure(calibration=cal)
        if self.done and st.present and st.label in self.tested:
            self.tested[st.label] = min(1.0, self.tested[st.label] + dt * 2)
        self.start_btn.visible = self.redo_btn.visible = self.done and running
        self.keep_btn.visible = not self.done and running and g.calibrated
        self.kbd_btn.visible = self.then == "game"
        self.group.reveal(self.t, .05, .45, (0, 30), .2)
        self.group.update(dt)

    def draw(self, c):
        self.backdrop.draw(fade=.36)
        W, H, t, g = c.W, c.H, self.t, self.app.gesture
        c.rect(0, 0, W, H, (.01, .016, .04, .4), (.01, .016, .04, .68))
        header(c, t, "CONTRÔLE GESTUEL", "Traitement 100 % local : aucune image n'est enregistrée ni envoyée", GOLD, ease_out(t / .5))
        if not self.ok:
            c.glass(W / 2 - 460, H / 2 - 130, 920, 240, (.04, .06, .12, .7), 30, 1.8, alpha(RED, .6))
            icons.draw(c, "camera", W / 2, H / 2 - 70, 60, RED)
            c.text(W / 2, H / 2, "CONTRÔLE GESTUEL INDISPONIBLE", 32, WHITE, align="c")
            c.text(W / 2, H / 2 + 44, self.why, 20, MUTED, "text", "c")
            self.group.draw(c, t)
            return
        self.seq = draw_camera(c, self.app, 98, 226, 760, t, self.seq)
        x, w = 930, W - 930 - 90
        if not self.done:
            name, text = STEP_TEXT[self.cal.current]
            c.glass(x, 218, w, 300, (.03, .05, .11, .66), 30, 1.8, alpha(GOLD, .45), 16)
            c.text(x + 44, 262, f"ÉTAPE {self.cal.step + 1} / 3", 20, MUTED, spacing=3)
            c.text(x + 44, 322, name, 52, WHITE, color2=GOLD, glow=.6, glow_col=GOLD, skew=.12, max_w=w - 250)
            c.paragraph(x + 44, 384, text, 22, (.80, .88, 1, 1), w - 270)
            cx, cy = x + w - 120, 360
            c.arc(cx, cy, 70, 12, 0, math.tau * .999, (.10, .14, .24, .9))
            c.arc(cx, cy, 70, 12, 0, math.tau * clamp(self.cal.progress) * .999, GOLD, WHITE, 0, 1)
            d = {"center": 0, "left": -1, "right": 1}[self.cal.current]
            icons.draw(c, "hand", cx + d * 20 * (.5 + .5 * math.sin(t * 3)), cy, 60, WHITE)
            if g.status == "error":
                c.text(x + 44, 484, g.error, 18, RED, "text", max_w=w - 88)
            elif not g.state.present:
                c.text(x + 44, 484, "Montrez votre main à la webcam…" if g.status == "running" else "Ouverture de la webcam…", 20, alpha(GOLD, .6 + .4 * math.sin(t * 4)), "text")
        else:
            c.glass(x, 218, w, 300, (.03, .05, .11, .66), 30, 1.8, alpha(GREEN, .5), 16)
            c.text(x + 44, 262, "CALIBRATION TERMINÉE", 34, WHITE, color2=GREEN, glow=.6, glow_col=GREEN)
            c.text(x + 44, 306, "Essayez la direction et les gestes ci-dessous", 20, MUTED, "text")
            # volant virtuel
            cx, cy, r = x + w - 150, 366, 92
            a = self.steer_vis * 1.5
            c.arc(cx, cy, r, 14, -math.pi * .999, math.pi * .999, (.12, .17, .28, 1), (.12, .17, .28, 1))
            c.arc(cx, cy, r, 14, a - .5, a + .5, CYAN, WHITE, 0, 1)
            for q in (0, 2.1, -2.1):
                c.line(cx, cy, cx + math.sin(a + q) * r, cy - math.cos(a + q) * r, (.3, .4, .55, 1), 8)
            c.circle(cx, cy, 18, (.1, .15, .25, 1), 2, CYAN, 8)
            c.bar(x + 44, 384, w - 360, 18, .5 + .5 * self.steer_vis, VIOLET, CYAN, (.09, .13, .22, .9), 0, 6)
            c.rect(x + 44 + (w - 360) / 2 - 2, 376, 4, 34, WHITE)
            c.text(x + 44, 440, f"DIRECTION {self.steer_vis * 100:+.0f} %", 22, WHITE, mono=True)
            c.text(x + 44, 478, "Deux mains visibles : mode volant" if not g.state.wheel else "MODE VOLANT ACTIF", 18, GREEN if g.state.wheel else MUTED, "text")
        # rappel des gestes
        gw = (w - 2 * 18) / 3
        for i, (key, name, act, col) in enumerate(GESTURES):
            on = g.state.present and g.state.label == key
            ok = self.tested[key] >= 1
            gx, gy = x + i * (gw + 18), 546
            c.panel(gx, gy, gw, 236, mix((.03, .05, .11, .80), (*col[:3], .75), .30 if on else .05), (.02, .03, .07, .80), 24, 1.6 + on, alpha(col, 1 if on else .35), 26 if on else 0)
            ic = {OPEN: "hand", FIST: "shield", TWO: "nitro"}[key]
            self._hand(c, gx + gw / 2, gy + 84, key, mix(col, WHITE, .5 if on else .1))
            c.text(gx + gw / 2, gy + 166, name, 22, WHITE, align="c", max_w=gw - 20)
            c.text(gx + gw / 2, gy + 200, act, 20, col, "text", "c")
            if ok:
                icons.draw(c, "check", gx + gw - 32, gy + 32, 26, GREEN)
            del ic
        c.text(x, 820, f"Geste détecté : {LABELS[g.state.label] if g.state.present else 'aucune main'}", 20, MUTED, "text")
        self.group.draw(c, t)

    @staticmethod
    def _hand(c, x, y, key, col):
        """Pictogramme de main : paume et doigts levés ou repliés."""
        up = {OPEN: (1, 1, 1, 1), FIST: (0, 0, 0, 0), TWO: (1, 1, 0, 0)}[key]
        c.panel(x - 34, y - 8, 68, 58, alpha(col, .9), None, 16, 0, alpha(col, .6), 8, 2)
        for i, u in enumerate(up):
            h = 56 if u else 18
            c.panel(x - 33 + i * 17, y - 4 - h + (6 if i in (0, 3) else 0), 14, h + 8, col, None, 7, 0, alpha(col, .5), 4, 2)
        if key == OPEN:
            c.panel(x - 56, y + 2, 30, 14, col, None, 7, 0, alpha(col, .5), 0, 2, 0, False, .6)
