"""Webcam + MediaPipe hors de la boucle de jeu, qui n'attend jamais la caméra.

`GestureTracker` travaille dans un thread ; `ProcessTracker` l'isole dans un processus
séparé, pour que ni le verrou global de Python (GIL) ni le pilote graphique ne freinent
la détection.

Confidentialité : chaque image est traitée en mémoire puis jetée. Rien n'est écrit
sur le disque ni envoyé sur le réseau.
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import sys
import threading
import time
from multiprocessing import shared_memory

import numpy as np

from config.paths import MODELS
from computer_vision.gestures import Calibration, GestureInterpreter, GestureState, Hand

log = logging.getLogger(__name__)
PREVIEW = (320, 240)
BONES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
         (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17))


def available() -> tuple[bool, str]:
    """Le contrôle gestuel est-il installé ? (sans charger les bibliothèques)"""
    import importlib.util as iu
    for mod, label in (("cv2", "OpenCV"), ("mediapipe", "MediaPipe")):
        if iu.find_spec(mod) is None:
            return False, f"{label} n'est pas installé."
    if not (MODELS / "hand_landmarker.task").exists():
        return False, "Le modèle hand_landmarker.task est absent de assets/models."
    return True, ""


class HandDetector:
    """Enveloppe MediaPipe Tasks (mode vidéo, processeur uniquement)."""

    def __init__(self, num_hands: int = 2):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
        self.mp = mp
        data = (MODELS / "hand_landmarker.task").read_bytes()        # en mémoire : chemins accentués acceptés
        self.task = HandLandmarker.create_from_options(HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=data, delegate=BaseOptions.Delegate.CPU), running_mode=RunningMode.VIDEO, num_hands=num_hands,
            min_hand_detection_confidence=.55, min_hand_presence_confidence=.5, min_tracking_confidence=.5))
        self.last = -1

    def detect(self, rgb: np.ndarray, t: float) -> list[Hand]:
        """`rgb` déjà en miroir."""
        self.last = max(int(t * 1000), self.last + 1)
        res = self.task.detect_for_video(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)), self.last)
        return [Hand(np.array([(p.x, p.y, p.z) for p in lm]), np.array([(p.x, p.y, p.z) for p in wd]), float(h[0].score))
                for lm, wd, h in zip(res.hand_landmarks, res.hand_world_landmarks, res.handedness)]

    def close(self):
        self.task.close()


def open_camera(index: int):
    import cv2
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


class GestureTracker:
    """Thread de capture et d'inférence. Lire `state`, `preview`, `error`, `status`."""

    def __init__(self, camera: int = 0, calibration: Calibration | None = None, sensitivity=.5, deadzone=.12, hands="auto", opener=open_camera,
                 detector_factory=HandDetector):
        self.camera = camera
        self.interp = GestureInterpreter(calibration, sensitivity, deadzone, hands)
        self._opener, self._factory = opener, detector_factory
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._state = GestureState()
        self._preview: bytes | None = None
        self._seq = 0
        self.error = ""
        self.status = "off"              # off, starting, running, error
        self.fps = 0.0
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self.error, self.status = "", "starting"
        self._thread = threading.Thread(target=self._run, name="gestures", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=4)
            self._thread = None
        self.status = "off"
        with self._lock:
            self._preview = None

    def configure(self, calibration=None, sensitivity=None, deadzone=None, hands=None):
        with self._lock:
            if calibration is not None:
                self.interp.cal = calibration
            if sensitivity is not None:
                self.interp.sensitivity = sensitivity
            if deadzone is not None:
                self.interp.deadzone = deadzone
            if hands is not None:
                self.interp.hands_mode = hands

    @property
    def state(self) -> GestureState:
        with self._lock:
            return GestureState(**{**self._state.__dict__, "centers": list(self._state.centers)})

    def preview(self, last_seq: int):
        """(numéro, octets RGBA) si une nouvelle image est prête, sinon None."""
        with self._lock:
            return (self._seq, self._preview) if self._preview is not None and self._seq != last_seq else None

    def _fail(self, message: str):
        log.warning("Contrôle gestuel : %s", message)
        self.error, self.status = message, "error"

    def _run(self):
        cap = det = None
        try:
            import cv2
            try:
                cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
            except AttributeError:
                pass
            det = self._factory()
            cap = self._opener(self.camera)
            if not cap.isOpened():
                return self._fail("Aucune webcam utilisable. Vérifiez qu'elle est branchée, autorisée dans Windows et libre.")
            fails, t0, last = 0, time.monotonic(), 0.0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    fails += 1
                    if fails > 60:
                        return self._fail("La webcam n'envoie plus d'images (débranchée ou prise par une autre application).")
                    time.sleep(.03)
                    continue
                fails = 0
                frame = cv2.flip(frame, 1)
                t = time.monotonic() - t0
                hands = det.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), t)
                with self._lock:
                    self._state = self.interp.update(hands, t)
                prev = self._draw(cv2, frame, hands)
                with self._lock:
                    self._preview = prev
                    self._seq += 1
                self.status = "running"
                if last:
                    self.fps += ((1 / max(1e-3, t - last)) - self.fps) * .1
                last = t
        except ImportError as exc:
            self._fail(f"Bibliothèque manquante : {exc.name}.")
        except Exception as exc:
            log.exception("Thread gestuel")
            self._fail(f"Erreur de suivi des mains : {exc}")
        finally:
            if cap is not None:
                cap.release()
            if det is not None:
                try:
                    det.close()
                except Exception:
                    log.debug("Fermeture du détecteur", exc_info=True)

    def _draw(self, cv2, frame, hands) -> bytes:
        """Aperçu assombri, teinté, avec squelette lumineux."""
        w, h = PREVIEW
        img = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        out = np.stack([g * .30 + 10, g * .42 + 14, g * .55 + 26], -1)       # RGB bleu nuit
        out = np.clip(out, 0, 255).astype(np.uint8)
        col = [(0, 229, 255), (139, 92, 246)]
        for k, hd in enumerate(hands):
            p = (hd.image[:, :2] * (w, h)).astype(int)
            for a, b in BONES:
                cv2.line(out, tuple(map(int, p[a])), tuple(map(int, p[b])), col[k % 2], 2, cv2.LINE_AA)
            for q in p:
                cv2.circle(out, tuple(map(int, q)), 3, (255, 255, 255), -1, cv2.LINE_AA)
        rgba = np.dstack([out, np.full((h, w), 255, np.uint8)])
        return rgba.tobytes()


class ProcessTracker:
    """Même interface que GestureTracker, mais dans un processus séparé."""

    def __init__(self, camera: int = 0, calibration: Calibration | None = None, sensitivity=.5, deadzone=.12, hands="auto", target=None):
        self.camera = camera
        self.interp = GestureInterpreter(calibration, sensitivity, deadzone, hands)     # copie locale des réglages
        self._target = target or _worker
        self._proc = self._conn = self._shm = None
        self._state = GestureState()
        self._seq = 0
        self.status, self.error, self.fps = "off", "", 0.0
        self._last_msg = 0.0

    def start(self):
        if self._proc is not None and self._proc.is_alive():
            return
        self._cleanup()
        ctx = mp.get_context("spawn")
        self._shm = shared_memory.SharedMemory(create=True, size=PREVIEW[0] * PREVIEW[1] * 4)
        self._conn, child = ctx.Pipe()
        self.status, self.error = "starting", ""
        self._last_msg = time.monotonic()
        self._proc = ctx.Process(target=self._target, args=(child, self._shm.name, self.camera, self._config()), daemon=True)
        self._proc.start()
        child.close()

    def _config(self) -> dict:
        i = self.interp
        return dict(calibration=i.cal, sensitivity=i.sensitivity, deadzone=i.deadzone, hands=i.hands_mode)

    def configure(self, calibration=None, sensitivity=None, deadzone=None, hands=None):
        i = self.interp
        i.cal = calibration if calibration is not None else i.cal
        i.sensitivity = i.sensitivity if sensitivity is None else sensitivity
        i.deadzone = i.deadzone if deadzone is None else deadzone
        i.hands_mode = hands or i.hands_mode
        if self._conn is not None:
            try:
                self._conn.send(self._config())
            except (OSError, ValueError):
                log.debug("Processus gestuel fermé")

    def poll(self):
        """Lit les derniers messages sans jamais attendre."""
        if self._conn is None:
            return
        try:
            while self._conn.poll():
                self.status, self.error, self.fps, self._state, self._seq = self._conn.recv()
                self._last_msg = time.monotonic()
        except (EOFError, OSError):
            if self.status not in ("error", "off"):
                self.status, self.error = "error", "Le suivi des mains s'est arrêté de façon inattendue."
            return
        silent = time.monotonic() - self._last_msg
        if self.status == "running" and silent > .5:            # caméra figée : les mains comptent comme perdues
            self._state.lost_for = silent
            self._state.present = False
        if self.status == "starting" and (silent > 25 or not self._proc.is_alive()):
            self.status, self.error = "error", "La webcam ne répond pas."

    @property
    def state(self) -> GestureState:
        self.poll()
        return self._state

    def preview(self, last_seq: int):
        if self._shm is None or self.status != "running" or self._seq == last_seq:
            return None
        return self._seq, bytes(self._shm.buf[:PREVIEW[0] * PREVIEW[1] * 4])

    def stop(self):
        if self._conn is not None:
            try:
                self._conn.send(None)
            except (OSError, ValueError):
                log.debug("Processus gestuel déjà fermé")
        if self._proc is not None:
            self._proc.join(timeout=3)
            if self._proc.is_alive():
                self._proc.terminate()
                self._proc.join(timeout=2)
        self._cleanup()
        self.status = "off"
        self._state = GestureState()

    def _cleanup(self):
        if self._conn is not None:
            self._conn.close()
        if self._shm is not None:
            self._shm.close()
            try:
                self._shm.unlink()
            except FileNotFoundError:
                log.debug("Mémoire partagée déjà libérée")
        self._proc = self._conn = self._shm = None


def _worker(conn, shm_name: str, camera: int, config: dict, opener=open_camera, factory=HandDetector):
    """Corps du processus : un GestureTracker dont chaque résultat est publié."""
    shm = shared_memory.SharedMemory(name=shm_name)
    tr = GestureTracker(camera, opener=opener, detector_factory=factory)
    tr.configure(**config)
    tr.start()
    seq, status = -1, ""
    try:
        while True:
            if conn.poll(.004):
                msg = conn.recv()
                if msg is None:
                    break
                tr.configure(**msg)
            pv = tr.preview(seq)
            if pv is not None:
                seq = pv[0]
                shm.buf[:len(pv[1])] = pv[1]
            if pv is not None or tr.status != status:
                status = tr.status
                conn.send((status, tr.error, tr.fps, tr.state, seq))
                if status == "error":
                    break
    except (EOFError, OSError, KeyboardInterrupt):
        log.debug("Jeu fermé : arrêt du suivi")
    finally:
        tr.stop()
        shm.close()
        conn.close()