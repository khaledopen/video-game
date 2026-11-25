"""Mesure les performances réelles dans une fenêtre, univers par univers.

Usage : python tools/bench.py [qualité] [largeur hauteur]
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["NEON_DRIVE_DATA"] = tempfile.mkdtemp()

import pygame                                    # noqa: E402

from core.app import App                         # noqa: E402
from entities.autopilot import Autopilot         # noqa: E402


def main():
    quality = sys.argv[1] if len(sys.argv) > 1 else "medium"
    size = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1600, 900)
    app = App(size=size, audio=False, start="menu")
    s = app.settings
    s["vsync"] = False
    s["auto_scale"] = False
    s["quality"] = quality
    app.renderer.set_quality(quality)
    print("GPU", app.ctx.info["GL_RENDERER"], "fenêtre", app.size, "interne", app.renderer.iw, app.renderer.ih)

    def measure(label, sec=5.0, warm=1.2):
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < warm:
            app.frame()
        n, t0, cpu = 0, time.perf_counter(), 0.0
        worst = 0.0
        while time.perf_counter() - t0 < sec:
            a = time.perf_counter()
            app.frame()
            worst = max(worst, time.perf_counter() - a)
            cpu += app.work_ms
            n += 1
        el = time.perf_counter() - t0
        print(f"{label:16s} {n / el:6.1f} FPS   CPU {cpu / n:5.2f} ms   pire image {worst * 1000:5.1f} ms")

    measure("menu", 3)
    for env in ("neon_city", "desert_highway", "rainy_tokyo", "mountain_road", "cyber_tunnel"):
        s["environment"] = env
        app.scenes.set("game", mode_id="endless", seed=5)
        g = app.scenes.scene
        g.countdown = 0
        g.event = lambda e: None
        pilot = Autopilot(1.0)
        app.keyboard.update = lambda dt: pilot.control(g.world, dt)
        g.world.player.s = 6000.0
        for a in ("next_obstacle", "next_coins", "next_pickup"):
            setattr(g.world.spawner, a, 6200.0)
        measure(env)
    app.scenes.set("garage")
    measure("garage", 3)
    app.shutdown()


main()

