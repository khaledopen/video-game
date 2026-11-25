"""Construction de maillages procéduraux.

Sommet = position (3), normale (3), uv (2), matériau (1) : 9 flottants.
"""
from __future__ import annotations

import math

import numpy as np

STRIDE = 9
# Matériaux (voir shaders/object.frag)
(PAINT, GLASS, CARBON, CHROME, TAIL, HEAD, ACCENT, TIRE, RIM, MATTE, EMIT, PLATE, STRIPE,
 BUILDING, FOLIAGE, ROCK, HOLO, SIGN, WOOD, CONE, WATER, CONCRETE, AMBER, TRUNK) = range(24)


class MeshBuilder:
    def __init__(self) -> None:
        self.tris: list[np.ndarray] = []   # (n, 3, 3)
        self.norms: list[np.ndarray] = []
        self.uvs: list[np.ndarray] = []
        self.mats: list[np.ndarray] = []

    # -- primitives ---------------------------------------------------------
    def add(self, tris, mat, uvs=None, norms=None, crease: float | None = None) -> None:
        tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
        face = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        area = np.linalg.norm(face, axis=1)
        keep = area > 1e-10
        tris, face, area = tris[keep], face[keep], area[keep]
        if not len(tris):
            return
        unit = face / area[:, None]
        if norms is not None:
            n = np.asarray(norms, dtype=np.float64).reshape(-1, 3, 3)[keep]
        elif crease is not None:
            n = _smooth_normals(tris, unit, face, crease)
        else:
            n = np.repeat(unit[:, None, :], 3, axis=1)
        uv = (np.asarray(uvs, dtype=np.float64).reshape(-1, 3, 2)[keep]
              if uvs is not None else np.zeros((len(tris), 3, 2)))
        m = np.broadcast_to(np.asarray(mat, dtype=np.float64).reshape(-1), (len(keep),))[keep] \
            if np.size(mat) == len(keep) and np.size(mat) > 1 else np.full(len(tris), float(np.ravel(mat)[0]))
        self.tris.append(tris)
        self.norms.append(n)
        self.uvs.append(uv)
        self.mats.append(np.asarray(m, float))

    def quad(self, a, b, c, d, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1))) -> None:
        self.add([[a, b, c], [a, c, d]], mat, [[uv[0], uv[1], uv[2]], [uv[0], uv[2], uv[3]]])

    def box(self, center, size, mat, taper=(1.0, 1.0), shift=(0.0, 0.0)) -> None:
        """Pavé ; `taper` réduit la face haute, `shift` la décale en (x, z)."""
        cx, cy, cz = center
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        tx, tz = hx * taper[0], hz * taper[1]
        sx, sz = shift
        b = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
             (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz)]
        t = [(cx - tx + sx, cy + hy, cz - tz + sz), (cx + tx + sx, cy + hy, cz - tz + sz),
             (cx + tx + sx, cy + hy, cz + tz + sz), (cx - tx + sx, cy + hy, cz + tz + sz)]
        self.quad(b[0], b[1], t[1], t[0], mat)
        self.quad(b[1], b[2], t[2], t[1], mat)
        self.quad(b[2], b[3], t[3], t[2], mat)
        self.quad(b[3], b[0], t[0], t[3], mat)
        self.quad(t[0], t[1], t[2], t[3], mat)
        self.quad(b[3], b[2], b[1], b[0], mat)

    def cylinder(self, center, radius, length, axis, mat, seg=16, cap_mat=None, r2=None,
                 caps=(True, True)) -> None:
        c = np.asarray(center, float)
        r2 = radius if r2 is None else r2
        ax = {"x": 0, "y": 1, "z": 2}[axis]
        u, v = [i for i in range(3) if i != ax]
        ang = np.linspace(0, 2 * math.pi, seg + 1)
        tris, norms, uvs = [], [], []

        def pt(a, r, h):
            p = c.copy()
            p[u] += math.cos(a) * r
            p[v] += math.sin(a) * r
            p[ax] += h
            return p

        def nm(a):
            n = np.zeros(3)
            n[u], n[v], n[ax] = math.cos(a), math.sin(a), (radius - r2) / max(length, 1e-6)
            return n / np.linalg.norm(n)

        for i in range(seg):
            a0, a1 = ang[i], ang[i + 1]
            p0, p1 = pt(a0, radius, -length / 2), pt(a1, radius, -length / 2)
            q0, q1 = pt(a0, r2, length / 2), pt(a1, r2, length / 2)
            n0, n1 = nm(a0), nm(a1)
            tris += [[p0, p1, q1], [p0, q1, q0]]
            norms += [[n0, n1, n1], [n0, n1, n0]]
            f0, f1 = i / seg, (i + 1) / seg
            uvs += [[(f0, 0), (f1, 0), (f1, 1)], [(f0, 0), (f1, 1), (f0, 1)]]
        self.add(tris, mat, uvs, norms)
        cap = mat if cap_mat is None else cap_mat
        for side, r, on in ((-1, radius, caps[0]), (1, r2, caps[1])):
            if not on or r < 1e-4:
                continue
            n = np.zeros(3)
            n[ax] = side
            ct, cn, cu = [], [], []
            for i in range(seg):
                a0, a1 = ang[i], ang[i + 1]
                ct.append([pt(0, 0, side * length / 2), pt(a0, r, side * length / 2), pt(a1, r, side * length / 2)])
                cn.append([n, n, n])
                cu.append([(.5, .5), (.5 + .5 * math.cos(a0), .5 + .5 * math.sin(a0)),
                           (.5 + .5 * math.cos(a1), .5 + .5 * math.sin(a1))])
            self.add(ct, cap, cu, cn)

    def torus(self, center, radius, tube, axis, mat, seg=28, sides=8) -> None:
        ax = {"x": 0, "y": 1, "z": 2}[axis]
        u, v = [i for i in range(3) if i != ax]
        c = np.asarray(center, float)
        grid = np.zeros((seg + 1, sides + 1, 3))
        nrm = np.zeros_like(grid)
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            for j in range(sides + 1):
                b = 2 * math.pi * j / sides
                n = np.zeros(3)
                n[u], n[v], n[ax] = math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b)
                p = c.copy()
                p[u] += math.cos(a) * radius
                p[v] += math.sin(a) * radius
                grid[i, j], nrm[i, j] = p + n * tube, n
        self.grid(grid, mat, nrm)

    def grid(self, pts: np.ndarray, mat, norms: np.ndarray | None = None,
             crease: float | None = 40.0) -> None:
        """Nappe (n, m, 3) de points ; `mat` scalaire ou (n-1, m-1)."""
        n, m = pts.shape[:2]
        a, b, c, d = pts[:-1, :-1], pts[1:, :-1], pts[1:, 1:], pts[:-1, 1:]
        tris = np.stack([np.stack([a, b, c], 2), np.stack([a, c, d], 2)], 2).reshape(-1, 3, 3)
        u, v = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, m), indexing="ij")
        uv = np.stack([u, v], -1)
        ua, ub, uc, ud = uv[:-1, :-1], uv[1:, :-1], uv[1:, 1:], uv[:-1, 1:]
        uvs = np.stack([np.stack([ua, ub, uc], 2), np.stack([ua, uc, ud], 2)], 2).reshape(-1, 3, 2)
        mats = mat
        if np.ndim(mat) == 2:
            mats = np.repeat(np.asarray(mat, float).reshape(-1), 2)
        nn = None
        if norms is not None:
            na, nb, nc, nd = norms[:-1, :-1], norms[1:, :-1], norms[1:, 1:], norms[:-1, 1:]
            nn = np.stack([np.stack([na, nb, nc], 2), np.stack([na, nc, nd], 2)], 2).reshape(-1, 3, 3)
        self.add(tris, mats, uvs, nn, None if nn is not None else crease)

    def tube(self, points, radius, mat, sides=6, closed=False) -> None:
        """Tube le long d'une polyligne."""
        pts = [np.asarray(p, float) for p in points]
        rings = []
        for i, p in enumerate(pts):
            prev = pts[i - 1] if i > 0 else (pts[-1] if closed else p)
            nxt = pts[i + 1] if i < len(pts) - 1 else (pts[0] if closed else p)
            t = nxt - prev
            t = t / max(np.linalg.norm(t), 1e-9)
            ref = np.array([0, 1, 0]) if abs(t[1]) < .9 else np.array([1, 0, 0])
            s = np.cross(ref, t)
            s /= np.linalg.norm(s)
            w = np.cross(t, s)
            rings.append([p + radius * (math.cos(a) * s + math.sin(a) * w)
                          for a in np.linspace(0, 2 * math.pi, sides + 1)])
        if closed:
            rings.append(rings[0])
        self.grid(np.array(rings), mat, crease=80)

    def extrude(self, outline, z0, z1, mat, axis="z", side_mat=None) -> None:
        """Polygone convexe 2D (x, y) extrudé le long de z (ou x : outline = (z, y))."""
        o = np.asarray(outline, float)

        def P(p, h):
            return (p[0], p[1], h) if axis == "z" else (h, p[1], p[0])

        n = len(o)
        for h in (z0, z1):
            self.add([[P(o[0], h), P(o[i], h), P(o[i + 1], h)] for i in range(1, n - 1)], mat)
        for i in range(n):
            p, q = o[i], o[(i + 1) % n]
            self.quad(P(p, z0), P(q, z0), P(q, z1), P(p, z1), mat if side_mat is None else side_mat)

    def merge(self, other: "MeshBuilder", offset=(0, 0, 0), scale=(1, 1, 1), yaw: float = 0.0) -> None:
        c, s = math.cos(yaw), math.sin(yaw)
        rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        sc, off = np.asarray(scale, float), np.asarray(offset, float)
        for t, n, u, m in zip(other.tris, other.norms, other.uvs, other.mats):
            self.tris.append((t * sc) @ rot.T + off)
            nn = (n / sc) @ rot.T
            self.norms.append(nn / np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-9))
            self.uvs.append(u)
            self.mats.append(m)

    def mirror_x(self) -> None:
        """Ajoute le symétrique de tout ce qui a été construit."""
        for t, n, u, m in list(zip(self.tris, self.norms, self.uvs, self.mats)):
            f = np.array([-1.0, 1.0, 1.0])
            self.tris.append((t * f)[:, ::-1])
            self.norms.append((n * f)[:, ::-1])
            self.uvs.append(u[:, ::-1])
            self.mats.append(m)

    # -- sortie -------------------------------------------------------------
    @property
    def triangles(self) -> int:
        return sum(len(t) for t in self.tris)

    def build(self) -> np.ndarray:
        if not self.tris:
            return np.zeros((0, STRIDE), dtype="f4")
        t = np.concatenate(self.tris).reshape(-1, 3)
        n = np.concatenate(self.norms).reshape(-1, 3)
        u = np.concatenate(self.uvs).reshape(-1, 2)
        m = np.repeat(np.concatenate(self.mats), 3)[:, None]
        return np.concatenate([t, n, u, m], axis=1).astype("f4")


def _smooth_normals(tris, unit, weighted, crease_deg):
    """Normales lissées par position, en coupant aux arêtes vives."""
    cos_lim = math.cos(math.radians(crease_deg))
    keys = np.round(tris.reshape(-1, 3), 4) + 0.0
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = np.ravel(inv)
    faces = np.repeat(np.arange(len(tris)), 3)
    order = np.argsort(inv, kind="stable")
    out = np.zeros((len(tris) * 3, 3))
    starts = np.flatnonzero(np.r_[True, np.diff(inv[order]) > 0])
    ends = np.r_[starts[1:], len(order)]
    for s, e in zip(starts, ends):
        idx = order[s:e]
        f = faces[idx]
        dots = unit[f] @ unit[f].T
        acc = (dots >= cos_lim).astype(float) @ weighted[f]
        ln = np.linalg.norm(acc, axis=1, keepdims=True)
        out[idx] = np.where(ln > 1e-12, acc / np.maximum(ln, 1e-12), unit[f])
    return out.reshape(-1, 3, 3)
