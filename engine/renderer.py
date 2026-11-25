"""Moteur de rendu OpenGL 3.3 : scène 3D instanciée, reflets, bloom et composition.

Le rendu vise les puces graphiques intégrées : résolution interne réglable, culling
par distance, instanciation, et repli propre quand un effet est désactivé.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import moderngl
import numpy as np

from config.environments import ENVIRONMENTS, Environment
from config.paths import SHADERS
from engine.mathx import camera_axes, perspective, view_matrix
from engine.mesh import STRIDE
from engine.models import props, traffic
from engine.models.cars import CarModel, wheel
from engine.track import ROAD_HALF, SAMPLES, WRAP, Z_RANGE

INST = 19       # flottants par instance
FAR = 700.0


@dataclass(frozen=True)
class Quality:
    name: str
    scale: float          # résolution interne relative à la fenêtre
    reflect: float        # résolution des reflets (0 = désactivés)
    bloom: int            # niveaux
    far: float
    particles: int
    streaks: int
    fxaa: bool
    density: float        # densité du décor


QUALITY = {
    "low": Quality("low", .56, 0.0, 4, 360., 350, 260, False, .6),
    "medium": Quality("medium", .72, .30, 5, 500., 800, 500, True, .85),
    "high": Quality("high", .92, .50, 6, 660., 1500, 900, True, 1.0),
}


@dataclass
class FrameView:
    """Tout ce qu'il faut savoir pour dessiner une image."""
    env: Environment = ENVIRONMENTS[0]
    time: float = 0.0
    s: float = 0.0
    speed: float = 0.0
    cam: tuple = (0.0, 3.0, -7.0)
    yaw: float = 0.0
    pitch: float = -0.12
    roll: float = 0.0
    fov: float = 62.0
    slope: float = 0.0
    curvature: float = 0.0
    sky_yaw: float = 0.0
    hour: float = 0.3
    night: float = 0.0
    player_x: float = 0.0
    head_z: float = 2.0
    headlights: float = 1.0
    accent: tuple = (0.0, 0.8, 1.0)
    nitro: float = 0.0
    speed_lines: float = 0.0
    rain: float = 0.0
    dust: float = 0.0
    studio: bool = False
    sun_col: tuple | None = None
    lights: list = field(default_factory=list)       # (x, z, intensité, 0 rouge | 1 accent)
    # post-traitement
    blur: float = 0.0
    aberration: float = 0.0
    vignette: float = 0.55
    flash: float = 0.0
    flash_col: tuple = (1.0, 1.0, 1.0)
    tint: tuple = (1.0, 1.0, 1.0)
    desat: float = 0.0
    fade: float = 1.0
    glitch: float = 0.0
    drops: float = 0.0
    bloom: float = 1.0
    grain: float = 0.02
    center: tuple = (0.5, 0.5)


class Mesh:
    def __init__(self, r: "Renderer", data: np.ndarray):
        self.r = r
        self.count = len(data)
        self.vbo = r.ctx.buffer(data.tobytes())
        self.cap = 8
        self.inst = r.ctx.buffer(reserve=self.cap * INST * 4, dynamic=True)
        self.n = 0
        self._bind()

    def _bind(self):
        self.vao = self.r.ctx.vertex_array(self.r.prog["object"], [
            (self.vbo, "3f 3f 2f 1f", "in_pos", "in_norm", "in_uv", "in_mat"),
            (self.inst, "3f 3f 3f 3f 3f 4f/i", "i_pos", "i_rot", "i_scale", "i_c1", "i_c2", "i_par")])

    def upload(self, data: np.ndarray):
        self.n = len(data)
        if not self.n:
            return
        if self.n > self.cap:
            self.cap = int(self.n * 1.6) + 4
            self.vao.release()
            self.inst.release()
            self.inst = self.r.ctx.buffer(reserve=self.cap * INST * 4, dynamic=True)
            self._bind()
        self.inst.orphan(self.cap * INST * 4)
        self.inst.write(data.astype("f4").tobytes())

    def draw(self):
        if self.n:
            self.vao.render(moderngl.TRIANGLES, vertices=self.count, instances=self.n)

    def release(self):
        self.vao.release()
        self.vbo.release()
        self.inst.release()


class Renderer:
    def __init__(self, ctx: moderngl.Context, size: tuple[int, int], quality: str = "medium"):
        self.ctx = ctx
        self.size = size
        self.quality = QUALITY[quality]
        self.fx = 1.0                      # intensité des effets visuels
        self.out: moderngl.Framebuffer | None = None      # sortie par défaut (écran si None)
        self.dyn_scale = 1.0               # résolution dynamique
        self.prog: dict[str, moderngl.Program] = {}
        self.meshes: dict[str, Mesh] = {}
        self._models: dict = {}
        self._queue: dict[str, list] = {}
        self._ubo = ctx.buffer(reserve=64 + 16 * 16, dynamic=True)
        self._load_programs()
        self._load_static()
        self.targets: dict = {}
        self._make_targets()
        self.draw_calls = 0

    # -- programmes --------------------------------------------------------------
    def _src(self, name: str) -> str:
        return (SHADERS / name).read_text(encoding="utf-8")

    def _load_programs(self):
        common = self._src("common.glsl")
        for name, vs, fs in (("object", "object.vert", "object.frag"), ("sky", "sky.vert", "sky.frag"),
                             ("ground", "ground.vert", "ground.frag"), ("decal", "decal.vert", "decal.frag"),
                             ("particle", "particle.vert", "particle.frag"), ("streak", "streak.vert", "streak.frag"),
                             ("ribbon", "ribbon.vert", "ribbon.frag")):
            p = self.ctx.program(vertex_shader=common + self._src(vs), fragment_shader=common + self._src(fs))
            p["Frame"].binding = 0
            self.prog[name] = p
        fsv = self._src("fs.vert")
        for name in ("down", "up", "composite"):
            self.prog[name] = self.ctx.program(vertex_shader=fsv, fragment_shader=self._src(name + ".frag"))
        self._set("object", u_bend=0)
        self._set("ground", u_bend=0, u_reflect=1)
        for n in ("decal", "particle", "ribbon"):
            self._set(n, u_bend=0)

    def _set(self, prog: str, **kw):
        p = self.prog[prog]
        for k, v in kw.items():
            if k in p:
                p[k].value = v

    def _load_static(self):
        ctx = self.ctx
        self.bend = ctx.texture((SAMPLES, 1), 2, dtype="f4")
        self.bend.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.bend.repeat_x = self.bend.repeat_y = False
        quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4")
        self.quad = ctx.buffer(quad.tobytes())
        self.fs_vao = {n: ctx.vertex_array(self.prog[n], [(self.quad, "2f", "in_pos")]) for n in ("sky", "down", "up", "composite")}
        # route : bandes resserrées près de la caméra
        rows = 150
        z = -24 + (FAR + 10) * (np.linspace(0, 1, rows) ** 1.75)
        xs = np.array([-ROAD_HALF - .35, -7.3, -3.6, 0, 3.6, 7.3, ROAD_HALF + .35])
        self.road = self._strip(np.array([[(x, 0, zz) for x in xs] for zz in z]))
        # glissières : profil extrudé de chaque côté
        prof = [(8.42, 0.0), (8.42, .34), (8.56, .52), (8.56, .70), (8.66, .84), (8.92, .84), (8.98, .0)]
        g = [np.array([[(sx * x, y, zz) for x, y in prof] for zz in z[::2]]) for sx in (1, -1)]
        self.rail = [self._strip(a) for a in g]
        us = np.concatenate([-np.linspace(1, 1e-4, 16), np.linspace(1e-4, 1, 16)])
        tz = np.arange(-25, FAR, 5.0)
        self.terrain = self._strip(np.array([[(u, 0, zz) for u in us] for zz in tz]), step_x=True, skip=15)
        tu = np.linspace(0, 1, 34)
        self.tunnel = self._strip(np.array([[(u, 0, zz) for u in tu] for zz in z[::2]]))
        r = np.linspace(-26, 26, 14)
        self.floor = self._strip(np.array([[(x, 0, zz) for x in r] for zz in r]))
        # instanciés 2D
        self._dyn = {}
        for name, fmt, names, size in (("decal", "4f 4f 2f/i", ("i_rect", "i_col", "i_kind"), 10),
                                       ("particle", "4f 4f 4f/i", ("i_pos", "i_col", "i_vel"), 12)):
            buf = ctx.buffer(reserve=4 * size * 2048, dynamic=True)
            vao = ctx.vertex_array(self.prog[name], [(self.quad, "2f", "in_pos"), (buf, fmt, *names)])
            self._dyn[name] = (buf, vao, size)
        rng = np.random.default_rng(1)
        self.seeds = ctx.buffer(rng.random((1000, 4)).astype("f4").tobytes())
        self.streak_vao = ctx.vertex_array(self.prog["streak"], [(self.quad, "2f", "in_pos"), (self.seeds, "4f/i", "i_seed")])
        self.rib_buf = ctx.buffer(reserve=8 * 4 * 4096, dynamic=True)
        self.rib_vao = ctx.vertex_array(self.prog["ribbon"], [(self.rib_buf, "3f 4f 1f", "in_pos", "in_col", "in_u")])

    def _strip(self, pts: np.ndarray, step_x=False, skip=-1):
        n, m = pts.shape[:2]
        idx = []
        for j in range(m - 1):
            if j == skip:
                continue
            i = np.arange(n - 1)
            a = i * m + j
            idx.append(np.stack([a, a + 1, a + m, a + 1, a + m + 1, a + m], 1).reshape(-1))
        ibo = self.ctx.buffer(np.concatenate(idx).astype("i4").tobytes())
        vbo = self.ctx.buffer(pts.reshape(-1, 3).astype("f4").tobytes())
        return self.ctx.vertex_array(self.prog["ground"], [(vbo, "3f", "in_pos")], index_buffer=ibo)

    # -- maillages --------------------------------------------------------------------
    def load_mesh(self, name: str) -> Mesh:
        """Charge à la demande (props, trafic, voitures `car:id`, roues `wheel:n`)."""
        m = self.meshes.get(name)
        if m is None:
            if name.startswith("car:"):
                data = self.car_model(name[4:]).mesh
            elif name.startswith("wheel:"):
                data = wheel(int(name[6:]))
            elif name.startswith("trf:"):
                data = self.traffic_model(name[4:]).mesh
            else:
                data = props.BUILDERS[name]()
            assert data.shape[1] == STRIDE
            m = self.meshes[name] = Mesh(self, data)
        return m

    def car_model(self, vid: str) -> CarModel:
        key = ("car", vid)
        if key not in self._models:
            from config.vehicles import BY_ID
            self._models[key] = CarModel(BY_ID[vid].shape)
        return self._models[key]

    def traffic_model(self, kind: str):
        key = ("trf", kind)
        if key not in self._models:
            self._models[key] = traffic.MODELS[kind]()
        return self._models[key]

    def preload_names(self) -> list[str]:
        from config.vehicles import VEHICLES
        return ([f"car:{v.id}" for v in VEHICLES] + [f"trf:{k}" for k in traffic.MODELS]
                + [f"wheel:{i}" for i in range(4)] + list(props.BUILDERS))

    # -- cibles ---------------------------------------------------------------------------
    def _make_targets(self):
        for t in self.targets.values():
            for o in t if isinstance(t, (list, tuple)) else [t]:
                o.release()
        ctx, q = self.ctx, self.quality
        sc = max(.35, q.scale * self.dyn_scale)
        w, h = max(320, int(self.size[0] * sc)) & ~1, max(180, int(self.size[1] * sc)) & ~1
        self.iw, self.ih = w, h

        def tex(tw, th):
            t = ctx.texture((tw, th), 4, dtype="f2")
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            t.repeat_x = t.repeat_y = False
            return t
        scene, depth = tex(w, h), ctx.depth_renderbuffer((w, h))
        self.targets = {"scene": (scene, depth, ctx.framebuffer([scene], depth))}
        if q.reflect > 0:
            rw, rh = max(64, int(w * q.reflect)), max(64, int(h * q.reflect))
            rt, rd = tex(rw, rh), ctx.depth_renderbuffer((rw, rh))
            self.targets["reflect"] = (rt, rd, ctx.framebuffer([rt], rd))
        chain, cw, ch = [], w, h
        for _ in range(q.bloom):
            cw, ch = max(4, cw // 2), max(4, ch // 2)
            t = tex(cw, ch)
            chain += [t, ctx.framebuffer([t])]
        self.targets["bloom"] = chain
        bt = tex(max(8, w // 8), max(8, h // 8))
        bt2 = tex(max(8, w // 8), max(8, h // 8))
        self.targets["blur"] = [bt, ctx.framebuffer([bt]), bt2, ctx.framebuffer([bt2])]

    def resize(self, size):
        self.size = size
        self._make_targets()

    def set_quality(self, name: str):
        if QUALITY[name] is not self.quality:
            self.quality = QUALITY[name]
            self._make_targets()

    def set_dynamic_scale(self, v: float):
        v = round(max(.6, min(1.0, v)), 2)
        if v != self.dyn_scale:
            self.dyn_scale = v
            self._make_targets()

    # -- file de dessin --------------------------------------------------------------------
    def queue(self, name: str, rows) -> None:
        if len(rows):
            self._queue.setdefault(name, []).append(np.asarray(rows, dtype="f4").reshape(-1, INST))

    def clear_queue(self):
        self._queue.clear()

    # -- rendu ------------------------------------------------------------------------------
    def _write_frame(self, v: FrameView, size, mirror: float, vp, axes):
        e = v.env
        right, up, fwd = axes
        tf = math.tan(math.radians(v.fov) / 2)
        n = v.night
        d = np.zeros(16 + 64, "f4")
        d[:16] = vp.T.reshape(-1)
        d[16:] = np.array([
            [*v.cam, v.time % 3600.], [v.s % WRAP, v.speed, Z_RANGE, mirror],
            [*(np.array(e.fog) * (1 - .9 * n)), max(e.fog_density, 2.2 / self.quality.far * .9) * (1 + .5 * n)],
            [*e.sun_dir, n], [*(v.sun_col or e.sun_col), v.hour], [*e.amb_sky, e.index], [*e.amb_gnd, e.wet],
            [v.player_x, v.headlights * e.headlight * (1 + 1.2 * n), v.head_z, ROAD_HALF],
            [*e.lamp, e.lamp_power * (1 - .85 * n)], [*e.edge, 40.0], [*e.edge2, v.curvature],
            [*right, tf * size[0] / size[1]], [*up, tf], [*fwd, v.sky_yaw], [size[0], size[1], v.slope, 0.],
            [*v.accent, v.nitro]], "f4").reshape(-1)
        self._ubo.write(d.tobytes())

    def render(self, v: FrameView, bend: np.ndarray, decals=None, particles=None, smoke=None, ribbons=None,
               target: moderngl.Framebuffer | None = None):
        """Dessine la scène complète dans `target` (écran par défaut)."""
        ctx, q = self.ctx, self.quality
        self.draw_calls = 0
        self._ubo.bind_to_uniform_block(0)
        self.bend.write(bend.tobytes())
        self.bend.use(0)
        active = []
        for name, parts in self._queue.items():
            m = self.load_mesh(name)
            m.upload(np.concatenate(parts) if len(parts) > 1 else parts[0])
            active.append(m)
        self._queue.clear()
        axes = camera_axes(v.yaw, v.pitch, v.roll)
        vp = perspective(v.fov, self.iw / self.ih, .3, 1000.) @ view_matrix(v.cam, *axes)

        # 1. reflets planaires
        refl_on = "reflect" in self.targets and v.env.wet > .2
        if refl_on:
            tex, _, fbo = self.targets["reflect"]
            fbo.use()
            ctx.viewport = (0, 0, *tex.size)
            fbo.clear(0, 0, 0, 1, depth=1.0)
            self._write_frame(v, tex.size, -1.0, vp, axes)
            ctx.enable_only(moderngl.DEPTH_TEST)
            ctx.enable_direct(0x3000)                       # GL_CLIP_DISTANCE0
            for m in active:
                m.draw()
            if not v.studio:
                if v.env.index == 4:
                    self._ground(3, self.tunnel)
                for rail in self.rail:
                    self._ground(2, rail)
            ctx.disable_direct(0x3000)
            self.fs_vao["sky"].render(moderngl.TRIANGLE_STRIP)
            tex.use(1)

        # 2. scène
        scene, _, fbo = self.targets["scene"]
        fbo.use()
        ctx.viewport = (0, 0, self.iw, self.ih)
        fbo.clear(0, 0, 0, 1, depth=1.0)
        self._write_frame(v, (self.iw, self.ih), 1.0, vp, axes)
        ctx.enable_only(moderngl.DEPTH_TEST)
        for m in active:
            m.draw()
        lights = np.zeros(32, "f4")
        for i, l in enumerate(v.lights[:8]):
            lights[i * 4:i * 4 + 4] = l
        self.prog["ground"]["u_light"].write(lights.tobytes())
        self._set("ground", u_reflOn=1.0 if refl_on else 0.0)
        if v.studio:
            self._ground(4, self.floor)
        else:
            self._ground(0, self.road)
            for rail in self.rail:
                self._ground(2, rail)
            if v.env.index == 4:
                self._ground(3, self.tunnel)
            else:
                self._ground(1, self.terrain)
        self.fs_vao["sky"].render(moderngl.TRIANGLE_STRIP)

        # 3. transparences (prémultipliées : additif et alpha dans la même passe)
        ctx.enable_only(moderngl.DEPTH_TEST | moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        fbo.depth_mask = False
        self._dynamic("decal", decals)
        if ribbons is not None and len(ribbons):
            for rib in ribbons:
                data = rib.astype("f4").tobytes()
                if len(data) > self.rib_buf.size:
                    continue
                self.rib_buf.orphan()
                self.rib_buf.write(data)
                self.rib_vao.render(moderngl.TRIANGLE_STRIP, vertices=len(rib))
        self._dynamic("particle", smoke)
        self._dynamic("particle", particles)
        for mode, amount in ((0, v.rain), (1, v.dust), (2, v.speed_lines)):
            if amount > .01:
                n = min(q.streaks, 1000) if mode != 2 else min(q.streaks, 130)
                self._set("streak", u_mode=mode, u_amount=float(amount))
                self.streak_vao.render(moderngl.TRIANGLE_STRIP, instances=n)
        fbo.depth_mask = True

        # 4. bloom
        ctx.enable_only(moderngl.NOTHING)
        chain = self.targets["bloom"]
        src = scene
        for i in range(0, len(chain), 2):
            t, f = chain[i], chain[i + 1]
            f.use()
            ctx.viewport = (0, 0, *t.size)
            src.use(0)
            self._set("down", u_tex=0, u_texel=(1 / src.width, 1 / src.height), u_thr=.82 if i == 0 else 0.0)
            self.fs_vao["down"].render(moderngl.TRIANGLE_STRIP)
            src = t
        ctx.enable_only(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE)
        for i in range(len(chain) - 4, -1, -2):
            t, f = chain[i], chain[i + 1]
            s2 = chain[i + 2]
            f.use()
            ctx.viewport = (0, 0, *t.size)
            s2.use(0)
            self._set("up", u_tex=0, u_texel=(1 / s2.width, 1 / s2.height), u_gain=.85)
            self.fs_vao["up"].render(moderngl.TRIANGLE_STRIP)
        ctx.enable_only(moderngl.NOTHING)
        # flou pour le verre dépoli de l'interface
        b0, f0, b1, f1 = self.targets["blur"]
        src = scene
        for t, f, sp in ((b0, f0, 3.), (b1, f1, 1.4), (b0, f0, 2.2), (b1, f1, 3.0)):
            f.use()
            ctx.viewport = (0, 0, *t.size)
            src.use(0)
            self._set("down", u_tex=0, u_texel=(sp / src.width, sp / src.height), u_thr=0.0)
            self.fs_vao["down"].render(moderngl.TRIANGLE_STRIP)
            src = t

        # 5. composition
        out = target or self.out or ctx.screen
        out.use()
        ctx.viewport = (0, 0, *self.size)
        scene.use(0)
        chain[0].use(1)
        self._set("composite", u_scene=0, u_bloom=1, u_texel=(1 / self.iw, 1 / self.ih), u_time=float(v.time % 600.),
                  u_bloomK=.30 * v.bloom * (.5 + .5 * self.fx), u_speed=v.blur * self.fx, u_aberr=v.aberration * self.fx,
                  u_vig=v.vignette, u_flash=v.flash * (.35 + .65 * self.fx), u_flashCol=v.flash_col, u_desat=v.desat,
                  u_fade=v.fade, u_grain=v.grain * self.fx, u_drops=v.drops * self.fx, u_glitch=v.glitch * self.fx,
                  u_fx=1.0 if q.fxaa else 0.0, u_tint=v.tint, u_center=v.center)
        self.fs_vao["composite"].render(moderngl.TRIANGLE_STRIP)

    @property
    def blur_texture(self):
        return self.targets["blur"][2]

    def _ground(self, part: int, vao):
        self.prog["ground"]["u_part"].value = part
        vao.render(moderngl.TRIANGLES)

    def _dynamic(self, name: str, data):
        if data is None or not len(data):
            return
        buf, vao, size = self._dyn[name]
        data = np.asarray(data, "f4").reshape(-1, size)[:2048]
        buf.orphan()
        buf.write(data.tobytes())
        vao.render(moderngl.TRIANGLE_STRIP, instances=len(data))


def row(pos, yaw=0., pitch=0., roll=0., scale=(1., 1., 1.), c1=(1., 1., 1.), c2=(1., 1., 1.), brake=0., lights=1.,
        flash=0., seed=0.) -> list:
    return [*pos, yaw, pitch, roll, *scale, *c1[:3], *c2[:3], brake, lights, flash, seed]
