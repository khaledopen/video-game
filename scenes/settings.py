"""Paramètres : image, son, commandes, gestes."""
from __future__ import annotations

import pygame

from config.palette import CYAN, GOLD, GREEN, MUTED, RED, VIOLET, WHITE, alpha
from config.settings import ACTION_NAMES, ACTIONS, RESOLUTIONS
from core.scene_manager import Scene
from effects.animation import ease_out
from scenes import backdrop
from ui import icons
from ui.widgets import Button, Group, KeyBind, Selector, Slider, Toggle, header

TABS = (("IMAGE", "screen", CYAN), ("SON", "sound", VIOLET), ("COMMANDES", "keyboard", GREEN), ("GESTES", "hand", GOLD))
QUAL = {"low": "FAIBLE", "medium": "MOYEN", "high": "ÉLEVÉ"}
HANDS = {"auto": "AUTOMATIQUE", "one": "UNE MAIN", "two": "VOLANT (2 MAINS)"}
HELP = {
    0: "Le profil FAIBLE coupe les reflets et réduit la résolution interne : idéal pour les PC modestes. La résolution dynamique vise 60 images par seconde.",
    1: "La musique a deux couches : la seconde monte avec votre vitesse.",
    2: "Cliquez sur une touche puis appuyez sur la nouvelle. Échap annule. Une manette branchée fonctionne aussi.",
    3: "Les images de la webcam sont traitées en mémoire sur cet ordinateur : rien n'est enregistré ni envoyé.",
}


class SettingsScene(Scene):
    def __init__(self, app, tab: int = 0):
        super().__init__(app)
        self.backdrop = backdrop.get(app)
        self.tab = tab
        self.tab_btns = [Button(n, lambda i=i: self.set_tab(i), icon=ic, color=col, w=300, h=66, size=22) for i, (n, ic, col) in enumerate(TABS)]
        self.back_btn = Button("RETOUR", self.back, icon="home", color=VIOLET, w=300, sound="ui_back")
        self.group = Group(app)
        self.binding: KeyBind | None = None
        self.pt = 0.0
        self.need_apply = False
        self.build()

    def enter(self):
        super().enter()
        self.backdrop.set_shot("wide")

    def leave(self):
        self.app.settings.save()

    def resized(self):
        self.build()

    def set_tab(self, i):
        self.tab, self.pt = i, 0.0
        self.build()

    # -- écriture des réglages ------------------------------------------------------------
    def put(self, key, apply=None):
        def f(v, *_):
            self.app.settings[key] = v
            if apply:
                apply(v)
        return f

    def build(self):
        app, s, c = self.app, self.app.settings, self.app.canvas
        for i, b in enumerate(self.tab_btns):
            b.x, b.y, b.selected = 90, 226 + i * 84, i == self.tab
        self.back_btn.x, self.back_btn.y = 90, c.H - 108
        x, w = 470, min(1180., c.W - 470 - 130)
        y0, dy = 262, 70
        rows = []

        def add(r):
            r.y = y0 + len(rows) * dy
            rows.append(r)
        if self.tab == 0:
            res = [tuple(r) for r in RESOLUTIONS if r[0] <= app.desktop[0] and r[1] <= app.desktop[1]]
            cur = tuple(s["resolution"])
            if cur not in res:
                res.append(cur)
            res.sort()
            add(Selector("Résolution (fenêtre)", [f"{a} × {b}" for a, b in res], res.index(cur), lambda v, i: self._video("resolution", list(res[i])), x, 0, w))
            add(Toggle("Plein écran", s["fullscreen"], lambda v: self._video("fullscreen", v), x, 0, w))
            q = list(QUAL)
            add(Selector("Qualité graphique", list(QUAL.values()), q.index(s["quality"]), lambda v, i: self._video("quality", q[i]), x, 0, w))
            add(Slider("Intensité des effets visuels", s["effects"], self.put("effects", lambda v: setattr(app.renderer, "fx", v)), x, 0, w))
            add(Toggle("Résolution dynamique (60 FPS)", s["auto_scale"], self.put("auto_scale", lambda v: app.renderer.set_dynamic_scale(1.0)), x, 0, w))
            add(Toggle("Synchronisation verticale (au redémarrage)", s["vsync"], self.put("vsync"), x, 0, w))
            add(Toggle("Afficher les FPS (F3)", s["show_fps"], self.put("show_fps"), x, 0, w))
        elif self.tab == 1:
            vol = lambda *_: app.audio.set_volumes(s["music"], s["sfx"])
            add(Slider("Volume de la musique", s["music"], self.put("music", vol), x, 0, w, color=VIOLET))
            add(Slider("Volume des effets sonores", s["sfx"], self.put("sfx", vol), x, 0, w, color=VIOLET))
            for lab, name in (("Écouter : moteur V8", "engine_v8_5"), ("Écouter : collision", "crash"), ("Écouter : nitro", "nitro_start"), ("Écouter : nouveau record", "new_record")):
                b = Button(lab.upper(), lambda n=name: app.audio.play(n, 1.0), icon="sound", color=VIOLET, w=460, h=56, size=19, sound="ui_hover")
                b.x = x
                add(b)
        elif self.tab == 2:
            names = ["AZERTY", "QWERTY", "PERSO"]
            add(Selector("Disposition", names, names.index(s["preset"]) if s["preset"] in names else 2, self._preset, x, 0, w, GREEN))
            add(Slider("Sensibilité des commandes", s["sensitivity"], self.put("sensitivity"), x, 0, w, color=GREEN))
            for a in ACTIONS:
                add(KeyBind(ACTION_NAMES[a], a, s["keys"][a], None, x, 0, w))
        else:
            ok, why = app.gesture.available()
            add(Toggle("Activer le contrôle gestuel", s["gesture_enabled"] and ok, self._gesture, x, 0, w, GOLD))
            add(Slider("Sensibilité des gestes", s["gesture_sensitivity"], self.put("gesture_sensitivity"), x, 0, w, color=GOLD))
            add(Slider("Zone neutre", s["gesture_deadzone"], self.put("gesture_deadzone"), x, 0, w, 0., .4, .02, color=GOLD))
            h = list(HANDS)
            add(Selector("Mode de direction", list(HANDS.values()), h.index(s["gesture_hands"]) if s["gesture_hands"] in h else 0, lambda v, i: self.put("gesture_hands")(h[i]), x, 0, w, GOLD))
            add(Toggle("Aperçu de la webcam en jeu", s["gesture_preview"], self.put("gesture_preview"), x, 0, w, GOLD))
            add(Selector("Caméra", [f"CAMÉRA {i}" for i in range(4)], int(s["camera"]) % 4, lambda v, i: self.put("camera")(i), x, 0, w, GOLD))
            b = Button("CALIBRER LES GESTES", lambda: app.scenes.go("calibration", then="settings"), icon="camera", color=GOLD, w=460, h=62, size=21)
            b.x, b.enabled = x, ok and s["gesture_enabled"]
            add(b)
            self.gesture_why = why
        self.rows = rows
        self.group.widgets = [*self.tab_btns, self.back_btn, *rows]
        if self.group.focus not in self.group.widgets:
            self.group.focus = None

    def _video(self, key, v):
        self.app.settings[key] = v
        self.need_apply = True

    def _preset(self, v, i):
        if v != "PERSO":
            self.app.settings.apply_preset(v)
            self.app.keyboard.reload()
            for r in self.rows:
                if isinstance(r, KeyBind):
                    r.keys = self.app.settings["keys"][r.action]

    def _gesture(self, v):
        ok, why = self.app.gesture.available()
        self.app.settings["gesture_enabled"] = bool(v and ok)
        self.build()

    def back(self):
        self.app.scenes.go("menu")

    def event(self, e):
        if self.binding is not None:
            if e.type == pygame.KEYDOWN:
                b = self.binding
                if e.key != pygame.K_ESCAPE:
                    self.app.settings.bind(b.action, b.waiting, pygame.key.name(e.key))
                    self.app.keyboard.reload()
                    self.app.audio.play("ui_click", .8)
                else:
                    self.app.audio.play("ui_back", .7)
                b.waiting = -1
                self.binding = None
                self.build()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self.binding.waiting = -1
                self.binding = None
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.audio.play("ui_back", .7)
            return self.back()
        self.group.event(e)
        self.binding = next((r for r in self.rows if isinstance(r, KeyBind) and r.waiting >= 0), None)

    def update(self, dt):
        super().update(dt)
        self.pt += dt
        self.backdrop.update(dt)
        self.group.update(dt)
        if self.need_apply:
            self.need_apply = False
            self.app.settings.save()
            self.app.apply_video()

    def draw(self, c):
        self.backdrop.draw(fade=.38)
        W, H, t = c.W, c.H, self.t
        c.rect(0, 0, W, H, (.01, .016, .04, .35), (.01, .016, .04, .65))
        name, ic, col = TABS[self.tab]
        header(c, t, "PARAMÈTRES", "Chaque changement est appliqué et enregistré immédiatement", VIOLET, ease_out(t / .5))
        n = max(len(r.label) > 0 for r in self.rows)
        x = 470
        w = min(1180., W - 470 - 130)
        ph = 70 * len(self.rows) + 60
        c.glass(x - 34, 226, w + 68, ph, (.028, .045, .098, .60), 30, 1.5, alpha(col, .32 * n))
        for i, r in enumerate(self.rows):
            r.appear = ease_out((self.pt - i * .03) / .35)
        self.group.draw(c, t)
        y = 226 + ph + 34
        icons.draw(c, ic, x - 14, y + 4, 26, col)
        c.paragraph(x + 16, y, HELP[self.tab], 18, MUTED, w - 20)
        if self.tab == 2:
            un = self.app.settings.unbound()
            if un:
                c.text(x + 16, y + 62, "Sans touche : " + ", ".join(ACTION_NAMES[a] for a in un), 18, RED, "text")
        elif self.tab == 3 and getattr(self, "gesture_why", ""):
            c.text(x + 16, y + 62, self.gesture_why, 18, RED, "text")
        elif self.tab == 0:
            r = self.app.renderer
            c.text(x + 16, y + 66, f"{self.app.ctx.info['GL_RENDERER']}   ·   rendu interne {r.iw} × {r.ih}   ·   fenêtre {self.app.size[0]} × {self.app.size[1]}", 16, alpha(WHITE, .6), "text")
