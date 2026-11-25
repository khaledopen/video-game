"""Chemins du projet, valables en source comme dans l'exécutable PyInstaller."""
from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
AUDIO = ASSETS / "audio"
TEXTURES = ASSETS / "textures"
ICONS = ASSETS / "icons"
MODELS = ASSETS / "models"
SHADERS = ROOT / "engine" / "shaders"


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """Dossier des sauvegardes : à côté du jeu, sinon dans LOCALAPPDATA."""
    override = os.environ.get("NEON_DRIVE_DATA")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    base = Path(sys.executable).parent if FROZEN else ROOT
    if _writable(base / "data"):
        return base / "data"
    path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NeonDrive"
    path.mkdir(parents=True, exist_ok=True)
    return path
