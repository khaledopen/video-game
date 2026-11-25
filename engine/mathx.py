"""Petites fonctions mathématiques partagées (repère : x droite, y haut, z avant)."""
from __future__ import annotations

import math

import numpy as np


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def damp(current, target, rate, dt):
    """Lissage exponentiel indépendant du nombre d'images par seconde."""
    return target + (current - target) * math.exp(-rate * dt)


def approach(v, target, step):
    return min(v + step, target) if v < target else max(v - step, target)


def perspective(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fov_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (far - near), -2 * far * near / (far - near)
    m[3, 2] = 1.0
    return m


def camera_axes(yaw: float, pitch: float, roll: float):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    fwd = np.array([sy * cp, sp, cy * cp])
    right = np.array([cy, 0.0, -sy])
    up = np.cross(fwd, right)
    c, s = math.cos(roll), math.sin(roll)
    return right * c + up * s, up * c - right * s, fwd


def view_matrix(pos, right, up, fwd) -> np.ndarray:
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = right, up, fwd
    m[:3, 3] = -m[:3, :3] @ np.asarray(pos, float)
    return m


def look_angles(src, dst):
    d = np.asarray(dst, float) - np.asarray(src, float)
    return math.atan2(d[0], d[2]), math.atan2(d[1], math.hypot(d[0], d[2]))


def hash01(i, salt: float = 0.0) -> np.ndarray:
    """Pseudo-aléatoire déterministe par emplacement (vectorisé)."""
    v = np.sin(np.asarray(i, dtype=np.float64) * 127.1 + salt * 311.7) * 43758.5453
    return v - np.floor(v)
