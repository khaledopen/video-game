"""Système audio : musique adaptative en deux couches, moteur multi-boucles, effets.

Sans périphérique audio, le gestionnaire devient silencieux au lieu de planter.
"""
from __future__ import annotations

import logging
import threading
from collections import OrderedDict

import pygame

from config.paths import AUDIO
from engine.mathx import clamp, damp

log = logging.getLogger(__name__)
RESERVED = 14
CH_MUSIC = (0, 1, 2, 3)            # deux paires (base, intense) pour le fondu entre morceaux
CH_ENGINE = (4, 5)
CH_NITRO, CH_BRAKE, CH_AMB, CH_AMB2 = 6, 7, 8, 9
ENGINE_LOOPS = 7


class AudioManager:
    def __init__(self, enabled: bool = True):
        self.ok = False
        self.music_vol, self.sfx_vol = .7, .85
        self.sounds: OrderedDict[str, pygame.mixer.Sound] = OrderedDict()
        self.duck = 1.0
        self.duck_target = 1.0
        self.pair = 0
        self.track = ""
        self.pair_gain = [0.0, 0.0]
        self.intensity = 0.0
        self.engine_kind = ""
        self.engine_gain = 0.0
        self.engine_on = False
        self._engine_idx = (-1, -1)
        self._loading: dict[str, threading.Thread] = {}
        self._pending: str | None = None
        self.amb = ""
        self.amb_gain = 0.0
        if not enabled:
            return
        try:
            pygame.mixer.init(32000, -16, 2, 512)
            pygame.mixer.set_num_channels(40)
            pygame.mixer.set_reserved(RESERVED)
            self.ok = True
        except pygame.error as exc:
            log.warning("Audio indisponible : %s", exc)

    # -- ressources --------------------------------------------------------------------
    def sound(self, name: str) -> pygame.mixer.Sound | None:
        if not self.ok:
            return None
        s = self.sounds.get(name)
        if s is None:
            path = AUDIO / f"{name}.wav"
            try:
                s = pygame.mixer.Sound(str(path))
            except (pygame.error, FileNotFoundError) as exc:
                log.warning("Son manquant %s : %s", path, exc)
                return None
            self.sounds[name] = s
        return s

    def preload(self, names):
        for n in names:
            self.sound(n)

    def _trim(self, keep: set[str]):
        """Ne garde en mémoire que les musiques utiles."""
        for n in [n for n in self.sounds if n.startswith("music_") and n not in keep]:
            del self.sounds[n]

    # -- effets ---------------------------------------------------------------------------
    def play(self, name: str, volume: float = 1.0, pan: float = 0.0):
        s = self.sound(name)
        if s is None or self.sfx_vol <= 0:
            return
        ch = pygame.mixer.find_channel()
        if ch is None:
            return
        ch.play(s)
        v = clamp(volume) * self.sfx_vol
        ch.set_volume(v * min(1.0, 1 - pan), v * min(1.0, 1 + pan))

    def set_volumes(self, music: float, sfx: float):
        self.music_vol, self.sfx_vol = clamp(music), clamp(sfx)

    # -- musique ------------------------------------------------------------------------------
    def music(self, track: str):
        """Passe à un morceau en fondu. Chargement en tâche de fond pour ne pas figer l'image."""
        if not self.ok or track == self.track and self._pending is None or track == self._pending:
            return
        self._pending = track
        if track not in self._loading:
            def job():
                for suffix in ("base", "full"):
                    if (AUDIO / f"music_{track}_{suffix}.wav").exists():
                        self.sound(f"music_{track}_{suffix}")
            th = threading.Thread(target=job, daemon=True)
            self._loading[track] = th
            th.start()

    def _start_pending(self):
        track = self._pending
        th = self._loading.get(track)
        if th is not None and th.is_alive():
            return
        self._loading.pop(track, None)
        self._pending = None
        self.pair = 1 - self.pair
        self.track = track
        self.pair_gain[self.pair] = 0.0
        for i, suffix in enumerate(("base", "full")):
            s = self.sounds.get(f"music_{track}_{suffix}")
            ch = pygame.mixer.Channel(CH_MUSIC[self.pair * 2 + i])
            ch.stop()
            if s is not None:
                ch.set_volume(0)
                ch.play(s, loops=-1)

    # -- moteur ----------------------------------------------------------------------------------
    def engine_start(self, kind: str):
        if not self.ok:
            return
        self.engine_kind, self.engine_on = kind, True
        self._engine_idx = (-1, -1)
        for i in range(ENGINE_LOOPS):
            self.sound(f"engine_{kind}_{i}")
        for n in ("nitro_loop", "brake"):
            self.sound(n)

    def engine_stop(self):
        self.engine_on = False

    def engine_update(self, dt: float, speed_ratio: float, throttle: float, braking: float, nitro: bool, scrape: bool = False):
        """Régime simulé avec rapports de boîte, fondu entre deux boucles voisines."""
        if not self.ok or not self.engine_kind:
            return
        gears = 6 if self.engine_kind != "electric" else 1
        x = clamp(speed_ratio) * gears * .999
        g = int(x)
        rpm = x - g if gears > 1 else clamp(speed_ratio)
        rpm = (.28 + .62 * rpm + .10 * throttle) if gears > 1 else rpm
        self.rpm = damp(getattr(self, "rpm", rpm), rpm, 10, dt)
        target = (.34 + .30 * throttle + .20 * clamp(speed_ratio)) if self.engine_on else 0.0
        self.engine_gain = damp(self.engine_gain, target, 6, dt)
        f = clamp(self.rpm) * (ENGINE_LOOPS - 1)
        i0 = min(ENGINE_LOOPS - 2, int(f))
        t = f - i0
        want = (i0, i0 + 1) if i0 % 2 == 0 else (i0 + 1, i0)
        gain = (1 - t, t) if i0 % 2 == 0 else (t, 1 - t)
        vol = self.engine_gain * self.sfx_vol * self.duck * .62
        for k in (0, 1):
            ch = pygame.mixer.Channel(CH_ENGINE[k])
            if want[k] != self._engine_idx[k] or not ch.get_busy():
                s = self.sound(f"engine_{self.engine_kind}_{want[k]}")
                if s is not None:
                    ch.play(s, loops=-1)
            ch.set_volume(vol * gain[k] ** .5)
        self._engine_idx = want
        self._loop(CH_NITRO, "nitro_loop", .50 if nitro and self.engine_on else 0.0, dt)
        self._loop(CH_BRAKE, "brake", clamp(braking * 1.1 - .15) * .40 * clamp(speed_ratio * 2.2) if self.engine_on else 0.0, dt)

    def _loop(self, channel: int, name: str, target: float, dt: float):
        gains = self.__dict__.setdefault("_gains", {})
        g = gains[channel] = damp(gains.get(channel, 0.0), target, 12, dt)
        ch = pygame.mixer.Channel(channel)
        if g > .01:
            if not ch.get_busy():
                s = self.sound(name)
                if s is not None:
                    ch.play(s, loops=-1)
            ch.set_volume(g * self.sfx_vol * self.duck)
        elif ch.get_busy():
            ch.stop()

    def ambience(self, env_id: str):
        """Boucle d'ambiance de l'univers ('' pour l'arrêter)."""
        if not self.ok or env_id == self.amb:
            return
        self.amb, self.amb_gain = env_id, 0.0
        ch = pygame.mixer.Channel(CH_AMB)
        ch.fadeout(500)
        if env_id:
            s = self.sound(f"amb_{env_id}")
            if s is not None:
                ch = pygame.mixer.Channel(CH_AMB2)
                ch.stop()
                ch.set_volume(0)
                ch.play(s, loops=-1, fade_ms=600)
        else:
            pygame.mixer.Channel(CH_AMB2).fadeout(500)

    # -- cycle --------------------------------------------------------------------------------------
    def update(self, dt: float, intensity: float = 0.0):
        if not self.ok:
            return
        if self._pending:
            self._start_pending()
        self.intensity = damp(self.intensity, clamp(intensity), 1.4, dt)
        self.duck = damp(self.duck, self.duck_target, 6, dt)
        self.amb_gain = damp(self.amb_gain, 1.0 if self.amb else 0.0, 2.0, dt)
        pygame.mixer.Channel(CH_AMB2).set_volume(self.amb_gain * .55 * self.sfx_vol * self.duck)
        for p in (0, 1):
            self.pair_gain[p] = damp(self.pair_gain[p], 1.0 if p == self.pair and self.track else 0.0, 1.6, dt)
            v = self.pair_gain[p] * self.music_vol * (.35 + .65 * self.duck) * .80
            pygame.mixer.Channel(CH_MUSIC[p * 2]).set_volume(v)
            pygame.mixer.Channel(CH_MUSIC[p * 2 + 1]).set_volume(v * self.intensity)
        old = 1 - self.pair
        if self.pair_gain[old] < .01:
            for i in (0, 1):
                ch = pygame.mixer.Channel(CH_MUSIC[old * 2 + i])
                if ch.get_busy():
                    ch.stop()
                    self._trim({f"music_{self.track}_base", f"music_{self.track}_full"} | {f"music_{self._pending}_{s}" for s in ("base", "full")})

    def quit(self):
        if self.ok:
            pygame.mixer.quit()
            self.ok = False
