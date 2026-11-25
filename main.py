"""NEON DRIVE : Endless Racing. Point d'entrée."""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from config.paths import data_dir                        # noqa: E402


def message_box(text: str) -> None:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "NEON DRIVE", 0x10)
    else:
        print(text, file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="NEON DRIVE : Endless Racing")
    ap.add_argument("--quality", choices=("low", "medium", "high"), help="profil graphique pour cette session et les suivantes")
    ap.add_argument("--windowed", action="store_true", help="force le mode fenêtré")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--skip-intro", action="store_true")
    ap.add_argument("--selftest", metavar="RAPPORT", help="diagnostic automatique écrit dans un fichier JSON")
    ap.add_argument("--selftest-camera", action="store_true", help="inclut la webcam dans le diagnostic")
    args = ap.parse_args()
    handler = logging.handlers.RotatingFileHandler(data_dir() / "neon_drive.log", maxBytes=300_000, backupCount=1, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    try:
        if args.selftest:
            from core.selftest import run
            return run(args.selftest, args.selftest_camera)
        from core.app import App
        from config.settings import Settings
        from database.store import Store
        if args.quality or args.windowed:
            store = Store()
            s = Settings(store)
            if args.quality:
                s["quality"] = args.quality
            if args.windowed:
                s["fullscreen"] = False
            s.save()
            store.close()
        App(audio=not args.no_audio, start="menu" if args.skip_intro else "loading").run()
        return 0
    except Exception as exc:
        logging.getLogger("main").exception("Erreur fatale")
        hint = ""
        if "OpenGL" in str(exc) or "GL" in type(exc).__name__ or "context" in str(exc).lower():
            hint = "\n\nLe jeu demande OpenGL 3.3 : mettez à jour le pilote graphique."
        if sys.stderr:
            traceback.print_exc()
        message_box(f"NEON DRIVE a rencontré une erreur :\n{exc}{hint}\n\nDétails : {data_dir() / 'neon_drive.log'}")
        return 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()          # indispensable à l'exécutable PyInstaller
    sys.exit(main())
