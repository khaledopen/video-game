"""Captures hors écran de toutes les scènes, pilotées comme un joueur.

Usage : python tools/screens.py [dossier] [noms...]
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["NEON_DRIVE_DATA"] = tempfile.mkdtemp()
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from core.app import App                         # noqa: E402
from core.progression import finish_run          # noqa: E402
from entities.autopilot import Autopilot         # noqa: E402


def steps(app, seconds, dt=1 / 60, draw_last=True):
    n = int(seconds / dt)
    for i in range(n):
        app.time += dt
        app.scenes.update(dt)
        app.audio.update(dt)
    app.canvas.begin(app.renderer.blur_texture, app.time, app.target)
    app.scenes.draw()
    app.canvas.end()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/shots")
    out.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[2:])
    app = App(headless=True, size=(1600, 900), audio=False)
    app.settings["quality"] = "high"
    app.renderer.set_quality("high")
    st = app.store
    st.add("coins", 6400)
    for i in range(14):
        st.add_run(("endless", "time_attack", "survival", "night")[i % 4], "neon_city", "neon_gt", 9000 + 5200 * ((i * 7) % 5) + i * 900, 3000 + i * 700, 60 + i * 9, 220 + i * 4, 60 + i * 5, 40 + i, 5 + i, 3)
    st.buy("shadow_x", 800)
    st.buy("inferno", 3000)
    st.add("xp", 2600)
    st.unlock_achievement("first_run")
    st.unlock_achievement("km5")

    def want(n):
        return not only or n in only

    def shot(name):
        if want(name):
            app.screenshot().save(out / f"{name}.png")
            print(name)

    if want("loading"):
        steps(app, 3.0)
        shot("loading")
    for name, sec in (("menu", 3), ("modes", 2.5), ("garage", 2.5), ("leaderboard", 2.5), ("stats", 2.5), ("settings", 1.6), ("calibration", .5)):
        if want(name):
            if name == "calibration":
                app.gesture.start = lambda: None
            app.scenes.set(name)
            steps(app, sec)
            shot(name)
    if want("settings_keys"):
        app.scenes.set("settings", tab=2)
        steps(app, 1.6)
        shot("settings_keys")
    if want("stats_ach"):
        app.scenes.set("stats")
        app.scenes.scene.set_page(1)
        steps(app, 2)
        shot("stats_ach")
    if want("garage_locked"):
        app.scenes.set("garage")
        app.scenes.scene.show(7)
        steps(app, 2)
        shot("garage_locked")
    envs = ("neon_city", "desert_highway", "rainy_tokyo", "mountain_road", "cyber_tunnel")
    for env in envs:
        if want("game_" + env) or want("game"):
            app.settings["environment"] = env
            app.settings["vehicle"] = "inferno" if env != "neon_city" else "shadow_x"
            app.scenes.set("game", mode_id="endless", seed=5)
            g = app.scenes.scene
            pilot = Autopilot(1.0)
            g.app.keyboard.update = lambda dt: pilot.control(g.world, dt)
            steps(app, 11)
            shot("game_" + env)
    if want("nitro"):
        app.settings["environment"] = "neon_city"
        app.settings["vehicle"] = "inferno"
        app.scenes.set("game", mode_id="endless", seed=9)
        g = app.scenes.scene
        pilot = Autopilot(1.0)

        def ctl(dt):
            c = pilot.control(g.world, dt)
            c.nitro = g.world.stats.time > 5
            g.world.player.nitro = max(g.world.player.nitro, .5)
            return c
        g.app.keyboard.update = ctl
        steps(app, 5)
        for b in ("shield", "magnet", "multi"):
            g.world.player.give(b)
        steps(app, 5)
        shot("nitro")
    if want("night"):
        app.settings["environment"] = "mountain_road"
        app.scenes.set("game", mode_id="night", seed=4)
        g = app.scenes.scene
        pilot = Autopilot(1.0)
        g.app.keyboard.update = lambda dt: pilot.control(g.world, dt)
        steps(app, 12)
        shot("night")
        g.pause()
        steps(app, 1)
        shot("pause")
    if want("gameover") or want("record"):
        app.settings["environment"] = "auto"
        app.scenes.set("game", mode_id="endless", seed=4)
        g = app.scenes.scene
        pilot = Autopilot(1.0)
        g.app.keyboard.update = lambda dt: pilot.control(g.world, dt)
        g.countdown = 0
        steps(app, 14)
        g.world.stats.score = 91234
        g.world.player.hp = 1
        g.world.player.invuln = 0
        g.world._hurt(90, g.world.player.x, g.world.player.s, "barrier", 1.0)
        steps(app, 1.3)
        shot("destroyed")
        res = finish_run(st, g.world)
        app.scenes.set("gameover", world=g.world, view=g.view, result=res)
        steps(app, 2.9)
        shot("record")
        steps(app, 4)
        shot("gameover")
    app.shutdown()


main()
