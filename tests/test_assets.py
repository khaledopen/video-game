"""Ressources : présence, validité audio, icônes, aucune référence manquante."""
import ast
import json
import re
import wave
from pathlib import Path

import numpy as np
import pytest

from config.environments import PLAYABLE
from config.paths import AUDIO, FONTS, ICONS, MODELS, SHADERS
from config.vehicles import VEHICLES
from entities.obstacles import PICKUP_KINDS

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".venv", ".runtime", "build", "dist"}
SOURCES = [p for p in ROOT.rglob("*.py") if not SKIP & set(p.relative_to(ROOT).parts)]
LOOPS = sorted(p for g in ("engine_*", "music_*", "amb_*", "nitro_loop*", "brake*") for p in AUDIO.glob(g + ".wav"))


def read(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float) / 32768
        return x.reshape(-1, w.getnchannels()), w.getframerate()


@pytest.mark.parametrize("path", sorted(AUDIO.glob("*.wav")), ids=lambda p: p.stem)
def test_audio_file_is_healthy(path):
    x, sr = read(path)
    assert sr == 32000 and len(x) > 300
    assert .15 < np.abs(x).max() <= 1.0
    assert np.sqrt((x**2).mean()) > .004
    assert abs(x.mean()) < .04
    assert (np.abs(x) > .999).mean() < .01                    # pas d'écrêtage


@pytest.mark.parametrize("path", LOOPS, ids=lambda p: p.stem)
def test_loops_are_seamless(path):
    x, _ = read(path)
    jump = np.abs(x[0] - x[-1]).max()
    usual = np.abs(np.diff(x, axis=0)).max()
    assert jump <= usual * 1.05 + .01


def test_expected_sounds():
    names = {p.stem for p in AUDIO.glob("*.wav")}
    need = {f"pk_{k}" for k in PICKUP_KINDS} | {f"amb_{e.id}" for e in PLAYABLE} | {"music_menu_base"}
    need |= {f"music_{e.id}_{s}" for e in PLAYABLE for s in ("base", "full")}
    need |= {f"engine_{v.engine}_{i}" for v in VEHICLES for i in range(7)}
    need |= {"boot", "ui_hover", "ui_click", "coin", "crash", "brake", "nitro_start", "new_record"}
    assert need <= names


def test_distinct_pickup_sounds():
    assert len({(AUDIO / f"pk_{k}.wav").read_bytes() for k in PICKUP_KINDS}) == len(PICKUP_KINDS)


def test_every_played_sound_exists():
    names = {p.stem for p in AUDIO.glob("*.wav")}
    for p in SOURCES:
        if "tests" not in p.parts:
            for m in re.finditer(r'(?:play|sound)\("([a-z_0-9]+)"', p.read_text(encoding="utf-8")):
                assert m.group(1) in names, (p.name, m.group(1))


def test_fonts_icons_shaders_model():
    assert (FONTS / "NeonDrive-Display.ttf").stat().st_size > 5000 and (FONTS / "NeonDrive-Light.ttf").exists()
    meta = json.loads((ICONS / "icons.json").read_text())
    assert (ICONS / "icons.png").exists() and (ICONS / "app.ico").exists() and len(meta) >= 40
    assert len(list(SHADERS.glob("*.*"))) >= 20
    assert (MODELS / "hand_landmarker.task").stat().st_size > 5_000_000
    for p in SOURCES:
        for m in re.finditer(r'icons\.draw\(c, "([a-z]+)"|icon="([a-z]+)"', p.read_text(encoding="utf-8")):
            assert (m.group(1) or m.group(2)) in meta, (p.name, m.groups())


def test_no_unfinished_code():
    for p in SOURCES:
        src = p.read_text(encoding="utf-8")
        ast.parse(src)
        if p.name != "test_assets.py":
            assert not re.search(r"\b(TODO|FIXME)\b", src), p
