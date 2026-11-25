"""Partie en cours : compte à rebours, conduite, pause, fin."""
from __future__ import annotations

import math

import pygame

from config.environments import BY_ID as ENVS
from config.modes import BY_ID as MODES
from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha, hexc
from config.settings import key_label
from core.progression import finish_run
from core.scene_manager import Scene
from effects.animation import ease_back, ease_out
from engine.mathx import clamp, damp
from engine.world_view import WorldView
from entities.player import Controls
from entities.world import World
from ui import icons
from ui.hud import HUD
from ui.widgets import Button, Group, IconButton, header

COUNTDOWN = 3.0


class GameScene(Scene):
    music = None

    def __init__(self, app, mode_id: str | None = None, seed: int | None = None):
        super().__init__(app)
        self.mode = MODES[mode_id or app.settings["mode"]]
        env_id = app.settings["environment"]
        env = ENVS.get(env_id) if env_id != "auto" else None
        spec = app.vehicle
        m = app.renderer.car_model(spec.id)
        cust = app.custom(spec.id)
        self.world = World(spec, self.mode, env, seed, (m.W, m.L))
        self.view = WorldView(app.renderer, self.world, app.look(spec.id), cust["nitro"], cust["trail"], app.settings["effects"])
        self.view.intro = 1.0
        self.hud = HUD()
        self.hud.vis = -.6
        self.countdown = COUNTDOWN + .6
        self.last_count = 99
        self.paused = False
        self.pause_k = 0.0
        self.pause_reason = ""
        self.use_gesture = self.mode.gesture
        self.over_t = 0.0
        self.result = None
        self.resume_grace = 0.0
        self.controls = Controls()
        self.warn_t = 0.0
        self.cam_seq = -1
        self.cam_ratio = 0.0
        self.pause_btn = IconButton("pause", self.pause, size=58)
        self.hud_group = Group(app, [self.pause_btn])
        self.resized()
        self._build_pause()

    # -- cycle de vie -----------------------------------------------------------------------
    def enter(self):
        app = self.app
        app.keyboard.reload()
        app.audio.music(self.world.env.id)
        app.audio.ambience(self.world.env.id)
        app.audio.engine_start(self.world.player.spec.engine)
        app.audio.duck_target = 1.0
        if self.use_gesture:
            app.gesture.start()
        pygame.mouse.set_visible(True)

    def leave(self):
        self.app.audio.engine_stop()
        self.app.audio.engine_update(.5, 0, 0, 0, False)
        self.app.audio.duck_target = 1.0
        self.app.audio.ambience("")
        if self.use_gesture:
            self.app.gesture.stop()

    def resized(self):
        self.pause_btn.x, self.pause_btn.y = self.app.canvas.W - 46 - 58, 34
        if hasattr(self, "pause_group"):
            self._layout_pause()

    def intensity(self):
        p = self.world.player
        return 0.0 if self.paused or not p.alive else clamp(.25 + .75 * p.speed_ratio + .25 * self.view.nitro_vis + .2 * self.world.difficulty)

    # -- pause --------------------------------------------------------------------------------
    def _build_pause(self):
        app = self.app
        self.pause_group = Group(app, [
            Button("REPRENDRE", self.resume, icon="play", color=CYAN, w=460, h=70, primary=True, size=28),
            Button("RECOMMENCER", lambda: app.scenes.go("game", mode_id=self.mode.id), icon="retry", color=VIOLET, w=460),
            Button("REVENIR AU CLAVIER", self.to_keyboard, icon="keyboard", color=GREEN, w=460),
            Button("GARAGE", lambda: app.scenes.go("garage"), icon="garage", color=GOLD, w=460),
            Button("MENU PRINCIPAL", lambda: app.scenes.go("menu"), icon="home", color=RED, w=460)])
        self._layout_pause()

    def _layout_pause(self):
        c = self.app.canvas
        self.pause_group.widgets[2].visible = self.use_gesture
        y = c.H / 2 - 150
        for b in self.pause_group.widgets:
            if b.visible:
                b.x, b.y = c.W / 2 - 230, y
                y += b.h + 16

    def pause(self, reason=""):
        if self.paused or self.world.over or self.t < .3:
            return
        self.paused, self.pause_reason = True, reason
        self.app.audio.duck_target = .12
        self.app.audio.play("ui_back", .7)
        self.pause_group.set_focus(self.pause_group.widgets[0], False)

    def resume(self):
        if self.use_gesture and self.pause_reason and self.app.gesture.lost:
            self.app.audio.play("ui_denied", .6)
            return
        self.paused, self.pause_reason = False, ""
        self.app.audio.duck_target = 1.0
        self.resume_grace = 1.2
        if self.countdown <= 0:
            self.countdown = 1.6            # court décompte à la reprise
            self.last_count = 99

    def to_keyboard(self):
        self.use_gesture = False
        self.app.gesture.stop()
        self._layout_pause()
        self.resume()

    def event(self, e):
        app = self.app
        if e.type == pygame.WINDOWFOCUSLOST and not self.paused and self.countdown <= 0:
            self.pause("FENÊTRE INACTIVE")
            return
        if self.paused:
            if app.keyboard.is_action(e, "pause") or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                self.resume()
            else:
                self.pause_group.event(e)
            return
        if app.keyboard.is_action(e, "pause"):
            self.pause()
        elif e.type == pygame.JOYBUTTONDOWN and e.button == 7:
            self.pause()
        elif e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            self.hud_group.event(e)

    # -- mise à jour -----------------------------------------------------------------------------
    def update(self, dt):
        super().update(dt)
        app, w, p = self.app, self.world, self.world.player
        self.pause_k = damp(self.pause_k, 1.0 if self.paused else 0.0, 12, dt)
        self.hud_group.update(dt)
        if self.use_gesture:
            app.gesture.update(dt)
        if self.paused:
            self.pause_group.update(dt)
            if self.use_gesture and self.pause_reason.startswith("MAINS") and not app.gesture.lost and app.gesture.state.present:
                self.resume()               # les mains sont revenues : reprise automatique
            app.audio.engine_update(dt, p.speed_ratio * .4, 0, 0, False)
            return
        if app.scenes.k < 1.0 and self.t < .25:
            return
        self.resume_grace = max(0.0, self.resume_grace - dt)
        # décompte
        running = True
        if self.countdown > 0:
            self.countdown -= dt
            n = math.ceil(self.countdown)
            if n != self.last_count:
                self.last_count = n
                if n <= 3:
                    app.audio.play("ui_count" if n > 0 else "ui_go", .9)
            running = self.countdown <= 0
        c = app.gesture.update(0) if self.use_gesture else app.keyboard.update(dt)
        if self.use_gesture:
            k = app.keyboard.update(dt)         # le clavier reste utilisable en secours
            if abs(k.steer) > .05 or k.throttle or k.brake or k.nitro:
                c = k
        if not running:
            c = Controls()
        self.controls = c
        scale = self.view.warp.update(dt)
        sdt = dt * scale
        if running:
            w.update(sdt, c)
        elif w.stats.time == 0:
            self._idle(sdt)
        for e in w.drain_events():
            self.view.on_event(e)
            self.hud.on_event(e, w)
            self._audio(e)
        if running or w.stats.time == 0:
            self.view.update(sdt, dt)
        self.hud.update(dt, w)
        app.audio.engine_update(dt, p.speed_ratio, c.throttle + p.nitro_on, p.brake if p.v > 18 and running else 0.0, p.nitro_on)
        if running and self.use_gesture and not w.over and self.resume_grace <= 0 and app.gesture.lost:
            self.pause("MAINS NON DÉTECTÉES" if app.gesture.status != "error" else "WEBCAM INTERROMPUE")
        if p.hp < 28 and p.alive and running:
            self.warn_t -= dt
            if self.warn_t <= 0:
                self.warn_t = 1.5
                app.audio.play("warning", .5)
        if w.over:
            self._ending(dt)

    def _idle(self, dt):
        """Roulage d'approche pendant le décompte : la voiture avance sans danger."""
        w, p = self.world, self.world.player
        p.v = 24.0
        p.s += p.v * dt
        w.dt = dt
        w.spawner.update(w)
        w.ai.update(dt, w.vehicles, w.obstacles, p, 1.0)
        p.spin = (p.spin + p.v / .345 * dt) % math.tau

    def _ending(self, dt):
        app = self.app
        if self.over_t == 0:
            app.audio.duck_target = .25
            if self.world.over_reason == "time":
                self.hud.show_banner("TEMPS ÉCOULÉ", "Distance validée", GOLD)
                app.audio.play("level_up", .8)
        self.over_t += dt
        limit = 3.4 if self.world.over_reason == "destroyed" else 2.2
        if self.world.over_reason == "time":
            self.world.player.v = damp(self.world.player.v, 12, .8, dt)
        if self.over_t > limit and self.result is None:
            self.result = finish_run(app.store, self.world)
            app.scenes.go("gameover", world=self.world, view=self.view, result=self.result)

    def _audio(self, e):
        a, p = self.app.audio, self.world.player
        pan = clamp((e.x - p.x) / 6, -.8, .8) if e.x else 0.0
        k = e.kind
        if k == "coin":
            a.play("coin_big" if e.data and e.data >= 5 else "coin", .55 + .03 * e.power, pan * .4)
        elif k == "pickup":
            a.play(f"pk_{e.data}", .85)
        elif k == "crash":
            a.play("crash", .6 + .4 * e.power, pan)
        elif k == "bump":
            a.play("cone" if e.data in ("cone", "debris") else "bump", .5 + .5 * e.power, pan)
        elif k == "destroyed":
            a.play("destroyed", 1.0)
        elif k == "scrape":
            a.play("scrape", .5, pan)
        elif k == "splash":
            a.play("splash", .7, pan)
        elif k == "near_miss":
            a.play("near_miss", .55 + .35 * e.power, pan)
        elif k == "shield_hit":
            a.play("shield_hit", .9)
        elif k == "nitro_start":
            a.play("nitro_start", .9)
        elif k == "nitro_end":
            a.play("nitro_end", .5)
        elif k == "level":
            a.play("level_up", .7)
        elif k == "environment":
            a.play("portal", .9)
            a.music(e.data.id)
            a.ambience(e.data.id)
        elif k == "tick":
            a.play("ui_tick", .8)

    # -- dessin -------------------------------------------------------------------------------------
    def draw(self, c):
        self.view.fx = self.app.settings["effects"]
        fade = 1.0
        if self.over_t > 0 and self.world.over_reason == "destroyed":
            fade = 1 - .35 * clamp((self.over_t - 2.4) / 1.0)
        self.view.render(fade=fade)
        t, W, H = self.t, c.W, c.H
        a = 1 - self.pause_k
        if a > .02 and self.over_t < 2.0:
            c.alpha = a * clamp(1 - (self.over_t - 1.2) * 2) if self.over_t else a
            base = c.alpha
            self.hud.draw(c, self.world, t, self.pause_btn)
            c.alpha = base
            self._keys_hint(c, t)
            c.alpha = 1
        if self.use_gesture and self.app.settings["gesture_preview"]:
            self.cam_seq = draw_camera(c, self.app, W - 400, 128, 340, t, self.cam_seq)
        if 0 < self.countdown <= 3.0:
            self._countdown(c, W, H)
        if self.world.stats.time < .9 and self.countdown <= 0 and not self.world.over:
            k = self.world.stats.time / .9
            c.text(W / 2, H * .40, "GO !", 150 + 130 * k, alpha(WHITE, 1 - k), color2=alpha(GREEN, 1 - k), align="c", glow=1 - k, glow_col=GREEN, skew=.16)
        if not self.world.player.alive and self.over_t > .7:
            k = ease_out((self.over_t - .7) / .8)
            c.text(W / 2, H * .34, "VÉHICULE DÉTRUIT", 88, alpha(WHITE, k), color2=alpha(RED, k), align="c", glow=k, glow_col=RED, skew=.16, spacing=14 * (1 - k) + 4)
        if self.pause_k > .01:
            self._draw_pause(c, t, W, H)

    def _keys_hint(self, c, t):
        a = clamp((self.countdown + .2) / .8) if self.world.stats.time == 0 else clamp(1 - self.world.stats.time / 3)
        if a <= 0 or self.use_gesture:
            return
        k = self.app.settings["keys"]
        parts = [(f"{key_label(k['left'][0])} {key_label(k['right'][0])}", "DIRIGER"), (key_label(k["up"][0]), "ACCÉLÉRER"), (key_label(k["down"][0]), "RALENTIR"), (key_label(k["nitro"][0]), "NITRO")]
        base = c.alpha
        c.alpha = base * a
        x = c.W / 2 - 360
        for lab, name in parts:
            w = max(52, c.measure(lab, 22) + 30)
            c.glass(x, c.H - 92, w, 46, (.04, .07, .14, .7), 8, 1.4, alpha(CYAN, .6))
            c.text(x + w / 2, c.H - 69, lab, 22, WHITE, align="c")
            c.text(x + w + 12, c.H - 69, name, 18, MUTED, "text")
            x += w + 130
        c.alpha = base

    def _countdown(self, c, W, H):
        n = math.ceil(self.countdown)
        f = n - self.countdown
        a = clamp(1.15 - f)
        s = 250 * (1.5 - .5 * ease_out(f * 3))
        col = (RED, GOLD, CYAN)[min(2, n - 1)]
        c.arc(W / 2, H * .40, 170, 8, 0, math.tau * (1 - f) * .999, alpha(col, a), alpha(WHITE, a), 0, 1)
        c.text(W / 2, H * .40, str(n), s, alpha(WHITE, a), color2=alpha(col, a), align="c", glow=a, glow_col=col)

    def _draw_pause(self, c, t, W, H):
        k = self.pause_k
        c.alpha = 1
        c.rect(0, 0, W, H, (.008, .014, .034, .66 * k))
        c.alpha = k
        s = ease_back(k)
        c.panel(W / 2 - 330 * s, H / 2 - 330, 660 * s, 690, (.035, .058, .12, .80), (.02, .03, .075, .86), 34, 1.8, alpha(CYAN, .45), 30)
        c.text(W / 2, H / 2 - 262, "PAUSE", 68, WHITE, color2=CYAN, align="c", glow=.7, glow_col=CYAN, skew=.16, spacing=8)
        if self.pause_reason:
            c.text(W / 2, H / 2 - 200, self.pause_reason, 24, alpha(RED, .7 + .3 * math.sin(t * 5)), align="c", spacing=2)
            if self.use_gesture:
                c.text(W / 2, H / 2 - 172, "Replacez vos mains devant la webcam pour reprendre", 18, MUTED, "text", "c")
        else:
            st = self.world.stats
            c.text(W / 2, H / 2 - 198, f"{int(st.score):,} PTS   ·   {st.distance / 1000:.2f} KM".replace(",", " "), 24, MUTED, align="c")
        self.pause_group.draw(c, t)
        c.alpha = 1


def draw_camera(c, app, x, y, w, t, seq, title=True):
    """Panneau d'aperçu de la webcam avec points de détection."""
    g = app.gesture
    h = w * .75
    tr = g.tracker
    if tr is not None:
        pv = tr.preview(seq)
        if pv:
            seq, data = pv
            c.load_image("webcam", data, (320, 240))
    st = g.state
    ok = st.present and g.status == "running"
    col = GREEN if ok else RED if g.status == "error" else GOLD
    c.panel(x - 8, y - 8, w + 16, h + (64 if title else 16), (.02, .035, .08, .88), None, 16, 1.6, alpha(col, .7), 14)
    if tr is not None and g.status == "running" and "webcam" in c.images:
        c.draw_image("webcam", x, y, w, h, (1, 1, 1, 1), 12)
        cal = tr.interp.cal
        for v, cc in ((cal.center, WHITE), (cal.left, CYAN), (cal.right, CYAN)):
            c.rect(x + w * v - 1, y, 2, h, alpha(cc, .35))
        c.triangle(x + w * st.raw_x, y + h - 10, 18, 16, alpha(col, .9), -math.pi / 2)
    else:
        icons.draw(c, "camera", x + w / 2, y + h / 2 - 16, 60, alpha(col, .5 + .3 * math.sin(t * 4)))
        msg = g.error if g.status == "error" else "DÉMARRAGE DE LA WEBCAM…" if g.status != "off" else "WEBCAM ARRÊTÉE"
        c.paragraph(x + w / 2, y + h / 2 + 36, msg, 16, MUTED, w - 30, align="c")
    if title:
        from computer_vision.gestures import LABELS
        lab = ("VOLANT · " if st.wheel else "") + LABELS[st.label] if ok else "AUCUNE MAIN" if g.status == "running" else "…"
        c.circle(x + 14, y + h + 26, 6, col, 0, alpha(col, .9), 8)
        c.text(x + 30, y + h + 26, lab, 18, WHITE)
        c.text(x + w - 6, y + h + 26, f"{tr.fps:.0f} IPS" if tr and g.status == "running" else "", 15, MUTED, "text", "r")
    return seq
