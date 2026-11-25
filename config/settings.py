"""Préférences du joueur : valeurs par défaut, validation, sauvegarde."""
from __future__ import annotations

import copy

import pygame

ACTIONS = ("left", "right", "up", "down", "nitro", "pause")
ACTION_NAMES = {"left": "Tourner à gauche", "right": "Tourner à droite", "up": "Accélérer", "down": "Ralentir", "nitro": "Nitro", "pause": "Pause"}
PRESETS = {
    "AZERTY": {"left": ["left", "q"], "right": ["right", "d"], "up": ["up", "z"], "down": ["down", "s"], "nitro": ["space", ""], "pause": ["escape", "p"]},
    "QWERTY": {"left": ["left", "a"], "right": ["right", "d"], "up": ["up", "w"], "down": ["down", "s"], "nitro": ["space", ""], "pause": ["escape", "p"]},
}
RESOLUTIONS = ((1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (1280, 800), (1680, 1050), (1024, 768), (3440, 1440))

DEFAULTS = {
    "resolution": [1600, 900],
    "fullscreen": False,
    "quality": "medium",
    "auto_scale": True,
    "vsync": True,
    "show_fps": False,
    "effects": .85,
    "music": .65,
    "sfx": .85,
    "sensitivity": .5,
    "preset": "AZERTY",
    "keys": PRESETS["AZERTY"],
    "gesture_enabled": True,
    "gesture_sensitivity": .5,
    "gesture_deadzone": .12,
    "gesture_hands": "auto",        # auto, one, two
    "gesture_preview": True,
    "gesture_calibration": None,
    "camera": 0,
    "vehicle": "neon_gt",
    "mode": "endless",
    "environment": "auto",
}


class Settings:
    def __init__(self, store=None):
        self.store = store
        self.values = copy.deepcopy(DEFAULTS)
        if store is not None:
            for k, v in store.load_settings().items():
                if k in DEFAULTS and self._valid(k, v):
                    self.values[k] = v
        self._dirty = False

    @staticmethod
    def _valid(k, v) -> bool:
        d = DEFAULTS[k]
        if d is None:
            return v is None or isinstance(v, dict)
        if isinstance(d, bool):
            return isinstance(v, bool)
        if isinstance(d, (int, float)):
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        if k == "keys":
            return isinstance(v, dict) and all(isinstance(v.get(a), list) and v[a] for a in ACTIONS)
        if k == "resolution":
            return isinstance(v, list) and len(v) == 2 and all(isinstance(n, int) and 640 <= n <= 8000 for n in v)
        if k == "quality":
            return v in ("low", "medium", "high")
        return isinstance(v, type(d))

    def __getitem__(self, k):
        return self.values[k]

    def __setitem__(self, k, v):
        if self.values.get(k) != v:
            self.values[k] = v
            self._dirty = True

    def save(self):
        if self.store is not None and self._dirty:
            self.store.save_settings(self.values)
            self._dirty = False

    def apply_preset(self, name: str):
        self["preset"] = name
        self["keys"] = copy.deepcopy(PRESETS[name])

    def bind(self, action: str, slot: int, key: str):
        """Associe une touche ; la retire des autres actions pour éviter les conflits."""
        keys = copy.deepcopy(self.values["keys"])
        for a in ACTIONS:
            keys[a] = ["" if k == key else k for k in keys[a]]
        row = (keys[action] + ["", ""])[:2]
        row[slot] = key
        keys[action] = row
        self["keys"] = keys
        self["preset"] = "PERSO"

    def unbound(self) -> list[str]:
        return [a for a in ACTIONS if not any(self.values["keys"][a])]


def key_label(name: str) -> str:
    if not name:
        return "—"
    special = {"left": "←", "right": "→", "up": "↑", "down": "↓", "space": "ESPACE", "escape": "ÉCHAP", "return": "ENTRÉE", "left shift": "MAJ G",
               "right shift": "MAJ D", "left ctrl": "CTRL G", "right ctrl": "CTRL D", "tab": "TAB", "left alt": "ALT", "backspace": "RETOUR"}
    return special.get(name, name.upper())


def key_codes(names) -> list[int]:
    out = []
    for n in names:
        if n:
            try:
                out.append(pygame.key.key_code(n))
            except (ValueError, pygame.error):
                continue
    return out
