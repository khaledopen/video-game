"""Interprétation des mains : doigts, filtrage, zone neutre, volant virtuel.

Ce module ne dépend ni de la webcam ni de MediaPipe : il est entièrement testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from engine.mathx import clamp

WRIST, THUMB_TIP, INDEX_MCP, MIDDLE_MCP, PINKY_MCP = 0, 4, 5, 9, 17
FINGERS = ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20))
OPEN, FIST, TWO, OTHER = "open", "fist", "two", "other"
LABELS = {OPEN: "MAIN OUVERTE", FIST: "POING", TWO: "DEUX DOIGTS", OTHER: "NEUTRE"}


@dataclass
class Hand:
    """Une main détectée, en repère miroir (x croît vers la droite du joueur)."""
    image: np.ndarray            # (21, 3) normalisé 0..1
    world: np.ndarray            # (21, 3) mètres
    score: float = 1.0

    @property
    def center(self) -> tuple[float, float]:
        p = self.image[[WRIST, INDEX_MCP, MIDDLE_MCP, PINKY_MCP], :2].mean(axis=0)
        return float(p[0]), float(p[1])

    @property
    def size(self) -> float:
        return float(np.linalg.norm(self.image[MIDDLE_MCP, :2] - self.image[WRIST, :2]))


def _angle(a, b, c) -> float:
    u, v = a - b, c - b
    n = np.linalg.norm(u) * np.linalg.norm(v)
    return 180.0 if n < 1e-12 else float(np.degrees(np.arccos(np.clip(np.dot(u, v) / n, -1, 1))))


def finger_scores(p: np.ndarray) -> np.ndarray:
    """Extension 0..1 de l'index à l'auriculaire, indépendante de la rotation de la main."""
    out = np.zeros(4)
    for i, (mcp, pip, dip, tip) in enumerate(FINGERS):
        bend = clamp((_angle(p[mcp], p[pip], p[dip]) - 105) / 50)
        reach = np.linalg.norm(p[tip] - p[WRIST]) / max(np.linalg.norm(p[pip] - p[WRIST]), 1e-6)
        out[i] = .55 * bend + .45 * clamp((reach - .92) / .26)
    return out


def classify(scores: np.ndarray) -> str:
    up = scores > .5
    if up.all():
        return OPEN
    if not up.any():
        return FIST
    if up[0] and up[1] and not up[2] and not up[3]:
        return TWO
    if up.sum() >= 3:
        return OPEN
    return OTHER


class OneEuro:
    """Filtre 1 € : lisse les tremblements sans retarder les vrais gestes."""

    def __init__(self, min_cutoff=1.6, beta=.9, d_cutoff=1.2):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x = None
        self.dx = 0.0
        self.t = 0.0

    @staticmethod
    def _a(cutoff, dt):
        tau = 1 / (2 * math.pi * cutoff)
        return 1 / (1 + tau / dt)

    def __call__(self, v: float, t: float) -> float:
        if self.x is None:
            self.x, self.t = v, t
            return v
        dt = max(1e-3, t - self.t)
        self.t = t
        self.dx += self._a(self.d_cutoff, dt) * ((v - self.x) / dt - self.dx)
        self.x += self._a(self.min_cutoff + self.beta * abs(self.dx), dt) * (v - self.x)
        return self.x

    def reset(self):
        self.x, self.dx = None, 0.0


class StableLabel:
    """Un geste n'est retenu qu'après plusieurs images identiques."""

    def __init__(self, frames=3, initial=OTHER):
        self.frames, self.value, self.candidate, self.n = frames, initial, initial, 0

    def update(self, label: str) -> str:
        if label == self.candidate:
            self.n += 1
        else:
            self.candidate, self.n = label, 1
        if self.n >= self.frames:
            self.value = self.candidate
        return self.value


@dataclass
class Calibration:
    center: float = .5            # position neutre de la main
    left: float = .26             # position main à fond à gauche
    right: float = .74
    tilt: float = 0.0             # inclinaison neutre du volant (rad)

    def to_dict(self) -> dict:
        return dict(center=self.center, left=self.left, right=self.right, tilt=self.tilt)

    @classmethod
    def from_dict(cls, d) -> "Calibration":
        try:
            c = cls(float(d["center"]), float(d["left"]), float(d["right"]), float(d.get("tilt", 0)))
            return c if c.right - c.center > .04 and c.center - c.left > .04 else cls()
        except (TypeError, KeyError, ValueError):
            return cls()


@dataclass
class GestureState:
    present: bool = False         # mains visibles (avec tolérance)
    lost_for: float = 99.0
    steer: float = 0.0
    throttle: float = 0.0
    brake: float = 0.0
    nitro: bool = False
    hands: int = 0
    wheel: bool = False
    label: str = OTHER
    raw_x: float = .5
    raw_tilt: float = 0.0
    centers: list = field(default_factory=list)


class GestureInterpreter:
    GRACE = .35                   # s pendant lesquelles une perte est ignorée

    def __init__(self, calibration: Calibration | None = None, sensitivity=.5, deadzone=.12, hands="auto"):
        self.cal = calibration or Calibration()
        self.sensitivity, self.deadzone, self.hands_mode = sensitivity, deadzone, hands
        self.fx, self.ft = OneEuro(), OneEuro(1.4, .6)
        self.labels = [StableLabel(), StableLabel()]
        self.state = GestureState()
        self.last_seen = -99.0
        self.last_x = None
        self.jumps = 0
        self.wheel_frames = 0
        self.scores = [None, None]

    def reset(self):
        self.__init__(self.cal, self.sensitivity, self.deadzone, self.hands_mode)

    # -- courbe de direction -----------------------------------------------------------
    def _shape(self, v: float) -> float:
        """Zone neutre, sensibilité et courbe douce au centre."""
        a = abs(v)
        if a <= self.deadzone:
            return 0.0
        a = (a - self.deadzone) / (1 - self.deadzone) * (.65 + .9 * self.sensitivity)
        return math.copysign(clamp(a) ** 1.25, v)

    def update(self, hands: list[Hand], t: float) -> GestureState:
        st = self.state
        hands = sorted((h for h in hands if h.score > .4 and h.size > .03), key=lambda h: h.center[0])[:2]
        if self.hands_mode == "one" and len(hands) > 1:
            hands = [max(hands, key=lambda h: h.size)]
        if not hands:
            st.lost_for = t - self.last_seen
            if st.lost_for > self.GRACE:
                st.present, st.hands, st.wheel, st.nitro = False, 0, False, False
                st.throttle = st.brake = 0.0
                st.steer *= .8
                st.centers = []
                self.fx.reset()
                self.ft.reset()
                self.last_x = None
                self.wheel_frames = 0
            return st
        # mode volant : deux mains stables pendant quelques images
        two = len(hands) == 2 and abs(hands[0].center[0] - hands[1].center[0]) > .10 and self.hands_mode != "one"
        self.wheel_frames = min(8, self.wheel_frames + 1) if two else max(0, self.wheel_frames - 2)
        wheel = two and self.wheel_frames >= 4
        if self.hands_mode == "two" and not two:
            st.lost_for = t - self.last_seen
            if st.lost_for > self.GRACE:
                st.present = False
            return st

        # rejet des sauts : une main ne traverse pas l'image entre deux trames
        cx = float(np.mean([h.center[0] for h in hands]))
        if not wheel and self.last_x is not None and abs(cx - self.last_x) > .30 and self.jumps < 2:
            self.jumps += 1
            return st
        self.jumps = 0
        self.last_x = cx
        self.last_seen, st.lost_for = t, 0.0
        st.present, st.hands, st.wheel = True, len(hands), wheel
        st.centers = [h.center for h in hands]

        if wheel:
            (x0, y0), (x1, y1) = hands[0].center, hands[1].center
            tilt = math.atan2(y1 - y0, (x1 - x0) * 4 / 3)       # rotation du volant
            st.raw_tilt = self.ft(tilt, t)
            v = (st.raw_tilt - self.cal.tilt) / .62
            st.raw_x = cx
            self.fx.reset()
        else:
            st.raw_x = x = self.fx(cx, t)
            c = self.cal
            v = (x - c.center) / max(.05, (c.right - c.center) if x > c.center else (c.center - c.left))
            self.ft.reset()
        st.steer = self._shape(clamp(v, -1.4, 1.4))

        labels = []
        for i, h in enumerate(hands):
            raw = finger_scores(h.world)
            self.scores[i] = raw if self.scores[i] is None else .55 * raw + .45 * self.scores[i]
            labels.append(self.labels[i].update(classify(self.scores[i])))
        if len(hands) == 1:
            self.scores[1] = None
        if TWO in labels:
            st.label = TWO
        elif FIST in labels:
            st.label = FIST
        elif OPEN in labels:
            st.label = OPEN
        else:
            st.label = OTHER
        st.nitro = st.label == TWO
        st.throttle = 1.0 if st.label in (OPEN, TWO) else 0.0
        st.brake = 1.0 if st.label == FIST else 0.0
        return st


class Calibrator:
    """Assistant en trois temps : centre, gauche, droite."""
    STEPS = ("center", "left", "right")
    HOLD = 1.3

    def __init__(self):
        self.step = 0
        self.progress = 0.0
        self.samples: list[float] = []
        self.tilts: list[float] = []
        self.values: dict[str, float] = {}
        self.tilt = 0.0

    @property
    def done(self) -> bool:
        return self.step >= len(self.STEPS)

    @property
    def current(self) -> str:
        return self.STEPS[min(self.step, 2)]

    def update(self, dt: float, st: GestureState):
        if self.done:
            return
        ok = st.present and st.lost_for < .1
        if ok and self.step > 0:
            c = self.values["center"]
            ok = st.raw_x < c - .07 if self.current == "left" else st.raw_x > c + .07
        if ok and self.samples and abs(st.raw_x - float(np.median(self.samples))) > .06:
            ok = False
            self.samples.clear()                       # main pas encore stable
        if not ok:
            self.progress = max(0.0, self.progress - dt * 1.6)
            if self.progress <= 0:
                self.samples.clear()
                self.tilts.clear()
            if st.present:
                self.samples.append(st.raw_x)
                del self.samples[:-6]
            return
        self.samples.append(st.raw_x)
        self.tilts.append(st.raw_tilt if st.wheel else 0.0)
        self.progress += dt / self.HOLD
        if self.progress >= 1:
            self.values[self.current] = float(np.median(self.samples[-25:]))
            if self.current == "center":
                self.tilt = float(np.median(self.tilts)) if self.tilts else 0.0
            self.step += 1
            self.progress = 0.0
            self.samples.clear()
            self.tilts.clear()

    def result(self) -> Calibration:
        v = self.values
        return Calibration(v["center"], v["left"], v["right"], self.tilt)
