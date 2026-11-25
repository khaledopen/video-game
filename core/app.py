"""Application : fenêtre, boucle principale, ressources partagées, qualité adaptative."""
from __future__ import annotations

import ctypes
import logging
import sys
import time

import moderngl
import pygame

from audio.manager import AudioManager
from config.paths import ICONS
from config.settings import Settings
from config.vehicles import BY_ID, LIGHTS, PAINTS
from controllers.gesture import GestureController
from controllers.keyboard import KeyboardController
from core.scene_manager import SceneManager
from database.store import Store
from engine.canvas import Canvas
from engine.mathx import damp
from engine.renderer import Renderer
from engine.vehicle_draw import Look
from ui import icons

log = logging.getLogger(__name__)
TITLE = "NEON DRIVE"


class App:
    def __init__(self, headless: bool = False, size=None, db_path=None, audio: bool = True, start: str = "loading"):
        self.headless = headless
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                log.debug("DPI non réglable")
        pygame.display.init()
        pygame.font.init()
        self.store = Store(db_path)
        self.settings = Settings(self.store)
        self.desktop = pygame.display.get_desktop_sizes()[0] if not headless else (1920, 1080)
        self._open_window(size)
        self.audio = AudioManager(audio)
        self.audio.set_volumes(self.settings["music"], self.settings["sfx"])
        self.renderer = Renderer(self.ctx, self.size, self.settings["quality"])
        self.renderer.fx = self.settings["effects"]
        self.renderer.out = self.target
        self.canvas = Canvas(self.ctx, self.size)
        icons.load(self.canvas)
        self.keyboard = KeyboardController(self.settings)
        self.gesture = GestureController(self.settings)
        self.clock = pygame.time.Clock()
        self.running = True
        self.time = 0.0
        self.fps = 60.0
        self._slow = 0.0
        self._fast = 0.0
        self._gpu_time = 0.0
        self.scenes = SceneManager(self)
        self.scenes.set(start)

    # -- fenêtre -----------------------------------------------------------------------
    def _open_window(self, size):
        s = self.settings
        if self.headless:
            self.size = tuple(size or (1280, 720))
            self.ctx = moderngl.create_standalone_context()
            self._tex = self.ctx.texture(self.size, 4)
            self.target = self.ctx.framebuffer([self._tex])
            return
        self.target = None
        want = tuple(size or s["resolution"])
        if not s["fullscreen"]:
            # une fenêtre plus grande que l'écran est ramenée à une taille visible
            while want[0] > self.desktop[0] or want[1] > self.desktop[1]:
                want = (int(want[0] * .85), int(want[1] * .85))
        for a, v in ((pygame.GL_CONTEXT_MAJOR_VERSION, 3), (pygame.GL_CONTEXT_MINOR_VERSION, 3),
                     (pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE), (pygame.GL_DOUBLEBUFFER, 1), (pygame.GL_DEPTH_SIZE, 0)):
            pygame.display.gl_set_attribute(a, v)
        try:
            pygame.display.set_icon(pygame.image.load(str(ICONS / "app.png")))
        except (pygame.error, FileNotFoundError) as exc:
            log.warning("Icône : %s", exc)
        flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
        if s["fullscreen"]:
            want, flags = self.desktop, pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN
        try:
            pygame.display.set_mode(want, flags, vsync=1 if s["vsync"] else 0)
        except pygame.error:
            pygame.display.set_mode(want, flags)
        pygame.display.set_caption(TITLE)
        self.size = pygame.display.get_window_size()
        self.ctx = moderngl.create_context()
        log.info("GPU : %s, OpenGL %s", self.ctx.info["GL_RENDERER"], self.ctx.version_code)

    def apply_video(self):
        """Applique résolution, plein écran et qualité sans perdre le contexte OpenGL."""
        s = self.settings
        if not self.headless:
            win = pygame.Window.from_display_module()
            try:
                if s["fullscreen"]:
                    win.set_fullscreen(True)
                else:
                    win.set_windowed()
                    w, h = s["resolution"]
                    k = min(1.0, (self.desktop[0] - 10) / w, (self.desktop[1] - 70) / h)
                    win.size = (int(w * k), int(h * k))
                    win.position = pygame.WINDOWPOS_CENTERED
            except pygame.error as exc:
                log.warning("Changement de mode vidéo : %s", exc)
            pygame.event.pump()
            self._resized(pygame.display.get_window_size())
        self.renderer.set_quality(s["quality"])
        self.renderer.fx = s["effects"]
        self.renderer.set_dynamic_scale(1.0)

    def _resized(self, size):
        size = (max(320, size[0]), max(180, size[1]))
        if tuple(size) != tuple(self.size):
            self.size = tuple(size)
            self.renderer.resize(self.size)
            self.canvas.resize(self.size)
            self.scenes.resized()

    # -- apparence du joueur ----------------------------------------------------------------
    def custom(self, vid: str) -> dict:
        spec = BY_ID[vid]
        c = dict(paint=spec.paint, light=spec.accent, rim=0, nitro=0, trail=0)
        for k, v in self.store.custom(vid).items():
            if k in c and isinstance(v, type(c[k])):
                c[k] = v
        return c

    def look(self, vid: str | None = None) -> Look:
        vid = vid or self.settings["vehicle"]
        c = self.custom(vid)
        return Look(vid, c["paint"], c["light"], c["rim"] % 4)

    @property
    def vehicle(self):
        vid = self.settings["vehicle"]
        if vid not in BY_ID or vid not in self.store.unlocked():
            vid = "neon_gt"
            self.settings["vehicle"] = vid
        return BY_ID[vid]

    # -- boucle ---------------------------------------------------------------------------------
    def run(self):
        while self.running:
            self.frame()
        self.shutdown()

    def frame(self, dt: float | None = None, events=None):
        if dt is None:
            ms = self.clock.tick(0 if self.settings["vsync"] else 144)
            dt = min(ms / 1000, .1)
        t0 = time.perf_counter()
        self.time += dt
        for e in (pygame.event.get() if events is None else events):
            if e.type == pygame.QUIT:
                self.quit()
            elif e.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED) and not self.headless:
                self._resized(pygame.display.get_window_size())
            elif e.type == pygame.KEYDOWN and (e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT)):
                self.settings["fullscreen"] = not self.settings["fullscreen"]
                self.settings.save()
                self.apply_video()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F3:
                self.settings["show_fps"] = not self.settings["show_fps"]
            else:
                self.scenes.event(e)
        self.scenes.update(dt)
        self.audio.update(dt, self.scenes.music_intensity())
        self.canvas.begin(self.renderer.blur_texture, self.time, self.target)
        self.scenes.draw()
        if self.settings["show_fps"]:
            self.canvas.text(self.canvas.W - 20, 20, f"{self.fps:.0f} FPS  {self.renderer.iw}x{self.renderer.ih}", 16, (.5, 1, .7, 1), "text", "r")
        self.canvas.end()
        self.work_ms = (time.perf_counter() - t0) * 1000
        if not self.headless:
            pygame.display.flip()
            if dt > 0:
                self.fps = damp(self.fps, 1 / dt, 3, dt)
            self._adapt(dt)

    def _adapt(self, dt):
        """Résolution dynamique : vise 60 images par seconde."""
        if not self.settings["auto_scale"] or self.time < 4:
            return
        if self.fps < 54:
            self._slow, self._fast = self._slow + dt, 0.0
        elif self.fps > 59:
            self._slow, self._fast = max(0.0, self._slow - dt), self._fast + dt
        r = self.renderer
        if self._slow > 1.2 and r.dyn_scale > .6:
            r.set_dynamic_scale(r.dyn_scale - .10)
            self._slow = 0.0
        elif self._fast > 25 and r.dyn_scale < 1.0:
            r.set_dynamic_scale(r.dyn_scale + .05)
            self._fast = 0.0

    def screenshot(self):
        """Image PIL de la dernière image rendue (mode sans fenêtre)."""
        from PIL import Image
        return Image.frombytes("RGBA", self.size, self._tex.read()).transpose(Image.FLIP_TOP_BOTTOM).convert("RGB")

    def quit(self):
        self.running = False

    def shutdown(self):
        self.gesture.stop(wait=True)
        self.settings.save()
        self.store.close()
        self.audio.quit()
        if not self.headless:
            pygame.quit()


def default_paint_index(paint: str) -> int:
    return next((i for i, (_, c) in enumerate(PAINTS) if c.lower() == paint.lower()), 0)


def light_index(light: str) -> int:
    return next((i for i, (_, c) in enumerate(LIGHTS) if c.lower() == light.lower()), 0)
