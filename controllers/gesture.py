"""Contrôleur gestuel : pont entre le suivi des mains et les commandes du jeu."""
from __future__ import annotations

import threading

from computer_vision.gestures import Calibration, GestureState
from computer_vision.tracker import ProcessTracker, available
from config.settings import Settings
from engine.mathx import damp
from entities.player import Controls


class GestureController:
    name = "Gestes"
    PAUSE_AFTER = .9               # s sans main avant la pause automatique

    def __init__(self, settings: Settings):
        self.settings = settings
        self.tracker: ProcessTracker | None = None
        self.steer = 0.0
        self._closing: threading.Thread | None = None
        self.state = GestureState()

    @staticmethod
    def available():
        return available()

    @property
    def calibrated(self) -> bool:
        return isinstance(self.settings["gesture_calibration"], dict)

    def start(self):
        s = self.settings
        if self._closing is not None:             # la caméra doit être rendue avant d'être reprise
            self._closing.join(timeout=5)
            self._closing = None
        if self.tracker is None:
            self.tracker = ProcessTracker(int(s["camera"]))
        self.tracker.configure(Calibration.from_dict(s["gesture_calibration"]), s["gesture_sensitivity"], s["gesture_deadzone"], s["gesture_hands"])
        self.tracker.start()

    def stop(self, wait: bool = False):
        """Libère la webcam ; en tâche de fond pour ne pas figer l'image."""
        if self.tracker is not None:
            self._closing = threading.Thread(target=self.tracker.stop, daemon=True)
            self._closing.start()
            self.tracker = None
        if wait and self._closing is not None:
            self._closing.join(timeout=6)
            self._closing = None
        self.state = GestureState()

    @property
    def status(self) -> str:
        return self.tracker.status if self.tracker else "off"

    @property
    def error(self) -> str:
        return self.tracker.error if self.tracker else ""

    @property
    def lost(self) -> bool:
        """Mains perdues assez longtemps pour mettre en pause."""
        return self.status == "error" or not self.state.present and self.state.lost_for > self.PAUSE_AFTER

    def update(self, dt: float) -> Controls:
        if self.tracker is None:
            return Controls()
        self.state = st = self.tracker.state
        # interpolation entre deux images de webcam (30 Hz) et le jeu (60 Hz)
        self.steer = damp(self.steer, st.steer if st.present else 0.0, 14, dt)
        return Controls(steer=self.steer, throttle=st.throttle, brake=st.brake, nitro=st.nitro)
