"""Canevas 2D accéléré : panneaux SDF, verre dépoli, texte, arcs, barres, images.

Coordonnées virtuelles : au moins 1920 x 1080, plus larges selon le format d'écran.
Le texte est positionné par le centre vertical de ses capitales.
"""
from __future__ import annotations

import math
from pathlib import Path

import moderngl
import numpy as np
import pygame
from PIL import Image, ImageFilter

from config.paths import FONTS, SHADERS

ATLAS = 2048
FLOATS = 28
WHITE = (1.0, 1.0, 1.0, 1.0)
ZERO = (0.0, 0.0, 0.0, 0.0)


def _text_font() -> str:
    for p in (Path(r"C:\Windows\Fonts\bahnschrift.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")):
        if p.exists():
            return str(p)
    return str(FONTS / "NeonDrive-Light.ttf")


class GlyphAtlas:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.tex = ctx.texture((ATLAS, ATLAS), 1)
        self.glow = ctx.texture((ATLAS, ATLAS), 1)
        for t in (self.tex, self.glow):
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
            t.repeat_x = t.repeat_y = False
        self.paths = {"display": str(FONTS / "NeonDrive-Display.ttf"), "light": str(FONTS / "NeonDrive-Light.ttf"), "text": _text_font()}
        self.fonts: dict = {}
        self.glyphs: dict = {}
        self.layouts: dict = {}
        self.x = self.y = self.row = 0
        self.generation = 0

    def font(self, name: str, px: int):
        f = self.fonts.get((name, px))
        if f is None:
            f = self.fonts[(name, px)] = pygame.font.Font(self.paths[name], px)
            f.align = pygame.FONT_LEFT
        return f

    def reset(self):
        self.glyphs.clear()
        self.layouts.clear()
        self.fonts.clear()
        self.x = self.y = self.row = 0
        blank = bytes(ATLAS * ATLAS)
        self.tex.write(blank)
        self.glow.write(blank)
        self.generation += 1

    def glyph(self, name: str, px: int, ch: str):
        key = (name, px, ch)
        g = self.glyphs.get(key)
        if g is not None:
            return g
        f = self.font("light" if name == "text" and ch in "←→↑↓" else name, px)
        met = f.metrics(ch)
        adv = met[0][4] if met and met[0] else f.size(ch)[0]
        surf = f.render(ch, True, (255, 255, 255))
        a = pygame.surfarray.array_alpha(surf).T
        h, w = a.shape
        pad = max(3, int(px * .34))
        cell = np.zeros((h + 2 * pad, w + 2 * pad), np.uint8)
        cell[pad:pad + h, pad:pad + w] = a
        ch_, cw = cell.shape
        if self.x + cw + 1 > ATLAS:
            self.x, self.y, self.row = 0, self.y + self.row + 1, 0
        if self.y + ch_ + 1 > ATLAS:
            self.reset()
        blur = np.asarray(Image.fromarray(cell).filter(ImageFilter.GaussianBlur(max(1.2, px * .13))), dtype=np.float32)
        blur = np.clip(blur * 1.6, 0, 255).astype(np.uint8)
        box = (self.x, self.y, cw, ch_)
        self.tex.write(cell.tobytes(), viewport=box, alignment=1)
        self.glow.write(blur.tobytes(), viewport=box, alignment=1)
        g = (adv, w, h, pad, (self.x / ATLAS, self.y / ATLAS, (self.x + cw) / ATLAS, (self.y + ch_) / ATLAS), max(f.get_ascent(), met[0][3] if met and met[0] else 0))
        self.glyphs[key] = g
        self.x += cw + 1
        self.row = max(self.row, ch_)
        return g

    def layout(self, text: str, name: str, px: int, spacing: float, mono: bool):
        """Glyphes d'une chaîne : tableau (dx, dy, w, h, uv) et largeur totale, en pixels."""
        key = (text, name, px, spacing, mono)
        lay = self.layouts.get(key)
        if lay is not None:
            return lay
        gen = self.generation
        x, rows = 0.0, []
        mono_w = max(self.glyph(name, px, c)[0] for c in "0123456789") if mono else 0
        cap = px * (.70 if name != "text" else .715)
        for ch in text:
            adv, w, h, pad, uv, asc = self.glyph(name, px, ch)
            off = 0.0
            if mono and ch.isdigit():
                off, adv = (mono_w - adv) / 2, mono_w
            if ch.strip():
                rows.append((x + off - pad, -asc + cap / 2 - pad, w + 2 * pad, h + 2 * pad, *uv))
            x += adv + spacing
        if gen != self.generation:          # l'atlas a été vidé en route : on recommence
            return self.layout(text, name, px, spacing, mono)
        lay = (np.array(rows, "f4").reshape(-1, 8), max(0.0, x - spacing))
        if len(self.layouts) > 4000:
            self.layouts.clear()
        self.layouts[key] = lay
        return lay


class Canvas:
    def __init__(self, ctx: moderngl.Context, size: tuple[int, int]):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=(SHADERS / "canvas.vert").read_text(), fragment_shader=(SHADERS / "canvas.frag").read_text())
        for n, u in (("u_atlas", 0), ("u_glow", 1), ("u_image", 2), ("u_blur", 3)):
            if n in self.prog:
                self.prog[n].value = u
        self.quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())
        self.cap = 4096
        self.buf = ctx.buffer(reserve=self.cap * FLOATS * 4, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, [(self.quad, "2f", "in_pos"), (
            self.buf, "4f 4f 4f 4f 4f 4f 4f/i", "i_rect", "i_uv", "i_c0", "i_c1", "i_c2", "i_par", "i_par2")])
        self.atlas = GlyphAtlas(ctx)
        self.images: dict[str, moderngl.Texture] = {}
        self.white = ctx.texture((1, 1), 4, b"\xff" * 4)
        self.rows: list = []
        self.blocks: list = []
        self.image = None
        self.blur = None
        self.alpha = 1.0
        self.ox = self.oy = 0.0
        self.target = None
        self.time = 0.0
        self.resize(size)

    def resize(self, size):
        self.size = size
        self.k = min(size[0] / 1920, size[1] / 1080)
        self.W, self.H = size[0] / self.k, size[1] / self.k
        self.atlas.reset()

    def to_virtual(self, pos):
        return pos[0] / self.k, pos[1] / self.k

    # -- cycle ---------------------------------------------------------------------
    def begin(self, blur_texture=None, time: float = 0.0, target=None):
        self.rows, self.blocks, self.image = [], [], None
        self.blur, self.time, self.target = blur_texture, time, target
        self.alpha, self.ox, self.oy = 1.0, 0.0, 0.0

    def end(self):
        self.flush()

    def _seal(self):
        if self.rows:
            self.blocks.append(np.array(self.rows, "f4"))
            self.rows = []

    def flush(self):
        self._seal()
        if not self.blocks:
            return
        data = np.concatenate(self.blocks) if len(self.blocks) > 1 else self.blocks[0]
        self.blocks = []
        ctx = self.ctx
        (self.target or ctx.screen).use()
        ctx.viewport = (0, 0, *self.size)
        ctx.enable_only(moderngl.BLEND)
        ctx.blend_func = (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        self.prog["u_size"].value = self.size
        self.atlas.tex.use(0)
        self.atlas.glow.use(1)
        (self.image or self.white).use(2)
        (self.blur or self.white).use(3)
        for i in range(0, len(data), self.cap):
            part = data[i:i + self.cap]
            self.buf.orphan()
            self.buf.write(part.tobytes())
            self.vao.render(moderngl.TRIANGLE_STRIP, instances=len(part))

    def _add(self, x, y, w, h, kind, c0=WHITE, c1=None, c2=ZERO, par=ZERO, skew=0., rot=0., opt=0., uv=ZERO):
        k, a = self.k, self.alpha
        c1 = c0 if c1 is None else c1
        self.rows.append(((x + self.ox) * k, (y + self.oy) * k, w * k, h * k, *uv, c0[0], c0[1], c0[2], c0[3] * a, c1[0], c1[1], c1[2], c1[3] * a,
                          c2[0], c2[1], c2[2], c2[3] * a, *par, kind, skew, rot, opt))

    # -- primitives --------------------------------------------------------------------
    def panel(self, x, y, w, h, c0, c1=None, cut=14., border=0., bcol=ZERO, glow=0., style=1, skew=0., horizontal=False, rot=0.):
        """Panneau à coins coupés. style : 0 quatre coins, 1 diagonale, 2 arrondi."""
        k = self.k
        self._add(x, y, w, h, 0, c0, c1, bcol, (cut * k, border * k, glow * k, style), skew, rot, 1. if horizontal else 0.)

    def glass(self, x, y, w, h, tint=(.04, .07, .13, .62), cut=18., border=1.5, bcol=(.55, .8, 1., .35), glow=0., style=1, skew=0., tint2=None):
        k = self.k
        if self.alpha < .999:               # en fondu, le verre devient un panneau translucide
            self._add(x, y, w, h, 0, (*tint[:3], .85), tint2, bcol, (cut * k, border * k, glow * k, style), skew)
        else:
            self._add(x, y, w, h, 5, tint, tint2, bcol, (cut * k, border * k, glow * k, style), skew)

    def rect(self, x, y, w, h, c0, c1=None, horizontal=False, skew=0.):
        self._add(x, y, w, h, 0, c0, c1, ZERO, (0., 0., 0., 2.), skew, 0., 1. if horizontal else 0.)

    def line(self, x0, y0, x1, y1, color, width=2., color2=None):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        self._add((x0 + x1) / 2 - ln / 2, (y0 + y1) / 2 - width / 2, ln, width, 0, color, color2, ZERO, (0, 0, 0, 2), 0., math.atan2(dy, dx), 1.)

    def halo(self, x, y, r, color):
        self._add(x - r, y - r, 2 * r, 2 * r, 6, color)

    def circle(self, x, y, r, color, border=0., bcol=ZERO, glow=0.):
        k = self.k
        self._add(x - r, y - r, 2 * r, 2 * r, 0, color, None, bcol, (r * k, border * k, glow * k, 2.))

    def arc(self, x, y, r, thick, a0, a1, color, color2=None, ticks=0, glow=0.):
        """Arc d'angles en radians (0 = haut, sens horaire)."""
        if abs(a1 - a0) < 1e-3:
            return
        e = r + thick / 2 + 14
        self._add(x - e, y - e, 2 * e, 2 * e, 3, color, color2, (0, 0, 0, glow), (r * self.k, thick * self.k, a0, a1), 0., 0., float(ticks))

    def bar(self, x, y, w, h, value, c0, c1=None, back=(.10, .14, .22, .85), segments=0, cut=6., skew=0.):
        self._add(x, y, w, h, 8, c0, c1, back, (max(0., min(1., value)), float(segments), cut * self.k, 0.), skew)

    def triangle(self, x, y, w, h, color, rot=0.):
        self._add(x - w / 2, y - h / 2, w, h, 7, color, rot=rot)

    # -- texte -----------------------------------------------------------------------------
    def measure(self, text, size, font="display", spacing=0., mono=False) -> float:
        px = max(6, round(size * self.k))
        return self.atlas.layout(text, font, px, spacing * self.k, mono)[1] / self.k

    def text(self, x, y, text, size, color=WHITE, font="display", align="l", color2=None, glow=0., glow_col=None, skew=0.,
             spacing=0., mono=False, max_w=0., shadow=False) -> float:
        if not text:
            return 0.0
        if max_w:
            w0 = self.measure(text, size, font, spacing, mono)
            if w0 > max_w:
                size *= max_w / w0
        px = max(6, round(size * self.k))
        lay, width = self.atlas.layout(text, font, px, spacing * self.k, mono)
        if not len(lay):
            return width / self.k
        if shadow:
            self.text(x + size * .04, y + size * .06, text, size, (0, 0, 0, .55 * color[3]), font, align, None, 0., None, skew, spacing, mono)
        self._seal()
        bx, by = (x + self.ox) * self.k, (y + self.oy) * self.k
        if align == "c":
            bx -= width / 2
        elif align == "r":
            bx -= width
        bx, by = round(bx), round(by)
        a = self.alpha
        n = len(lay)
        d = np.zeros((n, FLOATS), "f4")
        d[:, 0] = lay[:, 0] + bx
        d[:, 1] = lay[:, 1] + by
        if skew:
            d[:, 0] -= (lay[:, 1] + lay[:, 3] / 2) * skew
        d[:, 2:8] = lay[:, 2:8]
        d[:, 25] = skew
        if glow > 0:
            g = d.copy()
            gc = glow_col or color
            g[:, 8:12] = (gc[0], gc[1], gc[2], gc[3] * a * glow)
            g[:, 24] = 2
            self.blocks.append(g)
        c1 = color2 or color
        d[:, 8:12] = (color[0], color[1], color[2], color[3] * a)
        d[:, 12:16] = (c1[0], c1[1], c1[2], c1[3] * a)
        d[:, 24] = 1
        self.blocks.append(d)
        return width / self.k

    def paragraph(self, x, y, text, size, color, width, font="text", leading=1.35, align="l") -> float:
        """Texte sur plusieurs lignes ; retourne la hauteur occupée."""
        lines, cur = [], ""
        for para in text.split("\n"):
            for word in para.split():
                test = f"{cur} {word}".strip()
                if cur and self.measure(test, size, font) > width:
                    lines.append(cur)
                    cur = word
                else:
                    cur = test
            lines.append(cur)
            cur = ""
        for i, line in enumerate(lines):
            self.text(x, y + i * size * leading, line, size, color, font, align)
        return len(lines) * size * leading

    # -- images -------------------------------------------------------------------------------
    def load_image(self, key: str, data: bytes | None = None, size=None, path: Path | None = None, components=4) -> moderngl.Texture:
        tex = self.images.get(key)
        if path is not None and tex is None:
            img = Image.open(path).convert("RGBA")
            data, size = img.tobytes(), img.size
        if data is not None:
            if tex is not None and tex.size != tuple(size):
                tex.release()
                tex = None
            if tex is None:
                tex = self.ctx.texture(size, components, data, alignment=1)
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                tex.repeat_x = tex.repeat_y = False
                if path is not None:
                    tex.build_mipmaps()
                    tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
                self.images[key] = tex
            else:
                tex.write(data, alignment=1)
        return tex

    def draw_image(self, key: str, x, y, w, h, color=WHITE, cut=0., uv=(0., 0., 1., 1.), rot=0.):
        tex = self.images.get(key)
        if tex is None:
            return
        if self.image is not tex:
            if self.image is not None:
                self.flush()
            self.image = tex
        self._add(x, y, w, h, 4, color, None, ZERO, (cut * self.k, 0., 0., 1. if cut else 0.), 0., rot, 0., uv)
