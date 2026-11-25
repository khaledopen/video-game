"""Essai réel dans une vraie fenêtre Windows, avec de vrais messages clavier Windows.

Les touches (WM_KEYDOWN) sont envoyées uniquement à la fenêtre du jeu, la souris est injectée dans sa file :
le reste de l'ordinateur n'est pas touché. Usage : python tools/e2e_window.py
"""
from __future__ import annotations

import ctypes
import os
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["NEON_DRIVE_DATA"] = DATA = tempfile.mkdtemp()

import pygame                                    # noqa: E402

from core.app import App                         # noqa: E402

U = ctypes.windll.user32
U.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
VK = {"left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "enter": 0x0D, "esc": 0x1B, "space": 0x20}
EXT = {"left", "up", "right", "down"}
results = []


def check(name, ok, info=""):
    results.append(bool(ok))
    print(("OK   " if ok else "ECHEC"), name, info)


class Driver:
    def __init__(self):
        self.app = App(size=(1280, 720), start="loading")
        self.hwnd = pygame.display.get_wm_info()["window"]
        self.seen = []

    def run(self, sec, until=None):
        t = time.perf_counter()
        while time.perf_counter() - t < sec:
            self.app.frame()
            self.seen.append(self.app.fps)
            if until and until():
                return True
        return until is None

    def key(self, name, down):
        vk = VK.get(name) or ord(name.upper())
        sc = U.MapVirtualKeyW(vk, 0)
        lp = 1 | (sc << 16) | ((1 << 24) if name in EXT else 0)
        U.PostMessageW(self.hwnd, 0x0100 if down else 0x0101, vk, lp if down else lp | 0xC0000000)

    def tap(self, name):
        self.key(name, True)
        self.run(.06)
        self.key(name, False)
        self.run(.06)

    def hold(self, names, sec):
        for n in names:
            self.key(n, True)
        self.run(sec)
        for n in names:
            self.key(n, False)
        self.run(.05)

    def click(self, w):
        k = self.app.canvas.k
        x, y = int((w.x + w.w / 2) * k), int((w.y + w.h / 2) * k)
        E = pygame.event.Event
        pygame.event.post(E(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0), buttons=(0, 0, 0)))
        self.run(.15)
        pygame.event.post(E(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
        self.run(.05)
        pygame.event.post(E(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))
        self.run(.05)

def main():
    d = Driver()
    a = d.app
    sc = a.scenes
    check("audio réel initialisé", a.audio.ok)
    check("intro puis menu automatiquement", d.run(12, lambda: sc.name == "menu" and sc.k >= 1))
    d.run(1.5)
    check("musique du menu lancée", a.audio.track == "menu")
    d.tap("down")
    d.tap("down")
    check("flèches : focus sur GARAGE", sc.scene.group.focus and sc.scene.group.focus.label == "GARAGE")
    d.tap("enter")
    check("Entrée ouvre le garage", d.run(3, lambda: sc.name == "garage" and sc.k >= 1))
    d.run(.8)
    d.tap("right")
    d.run(.8)
    check("flèche droite : véhicule suivant", sc.scene.spec.id == "shadow_x")
    d.tap("esc")
    check("Échap revient au menu", d.run(3, lambda: sc.name == "menu" and sc.k >= 1))
    d.run(1.0)
    d.click(sc.scene.group.widgets[5])
    check("clic souris sur PARAMÈTRES", d.run(3, lambda: sc.name == "settings" and sc.k >= 1))
    d.run(.6)
    d.click(sc.scene.back_btn)
    d.run(3, lambda: sc.name == "menu" and sc.k >= 1)
    d.run(1.0)
    d.click(sc.scene.group.widgets[0])
    check("clic sur JOUER lance la partie", d.run(4, lambda: sc.name == "game" and sc.k >= 1))
    g = sc.scene
    check("décompte puis départ", d.run(6, lambda: g.world.stats.time > .1))
    p = g.world.player
    g.world.spawner.update = lambda *_: None          # route dégagée pour mesurer les commandes
    g.world.vehicles.clear()
    g.world.obstacles.clear()
    p.invuln = 60
    p.x = 0
    v = p.v
    d.hold(["up"], 1.5)
    check("flèche haute accélère", p.v > v + 5, f"{v * 3.6:.0f} -> {p.v * 3.6:.0f} km/h")
    v = p.v
    d.hold(["down"], .8)
    check("flèche basse ralentit", p.v < v - 4, f"{v * 3.6:.0f} -> {p.v * 3.6:.0f} km/h")
    for n, sg in (("left", -1), ("right", 1), ("q", -1), ("d", 1)):
        p.x = p.vx = 0
        d.hold([n], .35)
        check(f"touche {n.upper()} dirige", p.x * sg > .5, f"x = {p.x:+.2f} m")
    v = p.v
    d.hold(["z"], 1.0)
    check("touche Z accélère", p.v > v + 2)
    v = p.v
    d.hold(["s"], .6)
    check("touche S ralentit", p.v < v - 3)
    p.nitro = 1.0
    d.key("space", True)
    d.run(.5)
    on = p.nitro_on
    d.key("space", False)
    d.run(.3)
    check("Espace active la nitro", on and p.nitro < .95 and not p.nitro_on)
    d.tap("esc")
    d.run(.4)
    s0 = p.s
    d.run(.5)
    check("Échap met en pause", g.paused and p.s == s0)
    d.tap("esc")
    check("reprise après la pause", d.run(4, lambda: p.s > s0 + 5))
    d.click(g.pause_btn)
    check("bouton pause à la souris", g.paused)
    d.tap("enter")
    d.run(2.2)
    check("musique et moteur de la partie", a.audio.track == "neon_city" and a.audio.engine_on)
    p.invuln, p.hp = 0, 1
    g.world._hurt(80, p.x + 1, p.s + 2, "barrier", 1.0)
    check("écran Game Over après destruction", d.run(9, lambda: sc.name == "gameover" and sc.k >= 1))
    d.run(3)
    d.click(sc.scene.group.widgets[0])
    check("REJOUER relance", d.run(4, lambda: sc.name == "game" and sc.k >= 1))
    d.run(1)
    a.settings["fullscreen"] = True
    a.apply_video()
    d.run(1.5)
    check("plein écran sans perte de contexte", a.size == tuple(a.desktop) and a.ctx.error == "GL_NO_ERROR", str(a.size))
    a.settings["fullscreen"] = False
    a.settings["resolution"] = [1024, 768]
    a.apply_video()
    d.run(1.0)
    check("retour en fenêtre 1024×768", a.size == (1024, 768) and a.ctx.error == "GL_NO_ERROR", str(a.size))
    db = Path(DATA) / "neon_drive.db"
    games = a.store.totals()["games"]
    a.shutdown()
    from database.store import Store
    s = Store(db)
    check("sauvegarde relue après fermeture", games == 1 and s.totals()["games"] == 1 and s.coins > 0, f"{s.coins} pièces")
    s.close()
    print(f"{sum(results)} / {len(results)} vérifications réussies")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
