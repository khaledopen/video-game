"""Diagnostic intégré : `main.py --selftest rapport.json` (fonctionne aussi avec l'exécutable).

Ouvre chaque écran, joue quelques secondes avec le pilote automatique, vérifie le son,
la sauvegarde et, avec --selftest-camera, le suivi des mains. Utilise une sauvegarde
temporaire : la progression du joueur n'est jamais touchée.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path


def run(report: str, camera: bool = False) -> int:
    from core.app import App
    from entities.autopilot import Autopilot
    out: dict = {"ok": False}
    tmp = tempfile.mkdtemp(prefix="neon_selftest_")
    try:
        app = App(size=(1280, 720), db_path=Path(tmp) / "t.db", start="loading")
        out.update(gpu=app.ctx.info["GL_RENDERER"], opengl=app.ctx.version_code, audio=app.audio.ok, screens={})

        def frames(sec):
            t, n = time.perf_counter(), 0
            while time.perf_counter() - t < sec:
                app.frame()
                n += 1
            return round(n / sec, 1)

        t0 = time.perf_counter()
        while app.scenes.name != "menu" and time.perf_counter() - t0 < 30:
            app.frame()
        out["loading_seconds"] = round(time.perf_counter() - t0, 1)
        frames(1.2)
        for name in ("menu", "modes", "garage", "leaderboard", "stats", "settings"):
            app.scenes.set(name)
            out["screens"][name] = frames(1.0)
        for env in ("neon_city", "desert_highway", "rainy_tokyo", "mountain_road", "cyber_tunnel"):
            app.settings["environment"] = env
            app.scenes.set("game", mode_id="endless", seed=4)
            g = app.scenes.scene
            g.countdown, g.event = 0, lambda e: None
            pilot = Autopilot()
            app.keyboard.update = lambda dt, g=g, pilot=pilot: pilot.control(g.world, dt)
            out["screens"]["jeu:" + env] = frames(2.0)
            out["distance"] = round(g.world.player.s)
        out["gl_error"] = app.ctx.error
        out["gestures"] = {"installed": app.gesture.available()[0]}
        if camera and out["gestures"]["installed"]:
            app.scenes.set("calibration")
            t0 = time.perf_counter()
            while app.gesture.status == "starting" and time.perf_counter() - t0 < 30:
                app.frame()
            frames(3)
            tr = app.gesture.tracker
            out["gestures"].update(status=app.gesture.status, error=app.gesture.error, camera_fps=round(tr.fps, 1) if tr else 0)
        app.scenes.set("menu")
        app.shutdown()
        out["ok"] = out["gl_error"] == "GL_NO_ERROR" and min(out["screens"].values()) > 5
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        Path(report).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0 if out["ok"] else 1
