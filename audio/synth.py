"""Synthétiseur hors ligne (NumPy) : oscillateurs, filtres, batterie, effets.

Sert uniquement à fabriquer les fichiers de assets/audio ; le jeu ne synthétise rien
pendant une partie.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 32000


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def freq(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def saw(f, t, detune=0.0, phase=0.0):
    p = (f * (1 + detune) * t + phase) % 1.0
    return 2 * p - 1


def square(f, t, duty=.5):
    return np.where((f * t) % 1.0 < duty, 1.0, -1.0) - (2 * duty - 1)


def sine(f, t, phase=0.0):
    return np.sin(2 * np.pi * (f * t + phase))


def noise(n, rng):
    return rng.standard_normal(n)


def filt(x, low=None, high=None, order=4, reso=0.0):
    """Filtre passe-bas / passe-haut dans le domaine fréquentiel."""
    n = len(x)
    size = 1 << int(np.ceil(np.log2(max(2, n + 2048))))
    X = np.fft.rfft(x, size)
    f = np.fft.rfftfreq(size, 1 / SR)
    g = np.ones_like(f)
    if low:
        g *= 1 / np.sqrt(1 + (f / low) ** (2 * order))
        if reso:
            g *= 1 + reso * np.exp(-((f - low) / (low * .18)) ** 2)
    if high:
        g *= 1 / np.sqrt(1 + (high / np.maximum(f, 1e-6)) ** (2 * order))
    return np.fft.irfft(X * g, size)[:n]


def loop_filt(x, low=None, high=None, order=3):
    """Filtre circulaire : préserve le bouclage parfait."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if low:
        g *= 1 / np.sqrt(1 + (f / low) ** (2 * order))
    if high:
        g *= 1 / np.sqrt(1 + (high / np.maximum(f, 1e-6)) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def env(n, a=.005, d=.1, s=.6, r=.1, dur=None):
    """Enveloppe ADSR sur n échantillons."""
    t = np.arange(n) / SR
    total = n / SR
    out = np.minimum(1, t / max(a, 1e-4))
    out *= s + (1 - s) * np.exp(-np.maximum(0, t - a) / max(d, 1e-4))
    out *= np.clip((total - t) / max(r, 1e-4), 0, 1)
    return out


def exp_env(n, tau):
    return np.exp(-np.arange(n) / SR / tau)


def drive(x, k=1.5):
    return np.tanh(x * k) / np.tanh(k)


class Song:
    """Piste stéréo bouclée : les queues de notes sont repliées sur le début."""

    def __init__(self, bars: int, bpm: float, seed=0):
        self.bpm = bpm
        self.beat = 60 / bpm
        self.n = int(round(bars * 4 * self.beat * SR))
        self.buf = np.zeros((self.n, 2))
        self.rng = np.random.default_rng(seed)

    def put(self, x, beat, gain=1.0, pan=0.0):
        i = int(round(beat * self.beat * SR)) % self.n
        l, r = gain * np.sqrt((1 - pan) / 2) * 1.414, gain * np.sqrt((1 + pan) / 2) * 1.414
        pos = 0
        while pos < len(x):
            m = min(len(x) - pos, self.n - i)
            self.buf[i:i + m, 0] += x[pos:pos + m] * l
            self.buf[i:i + m, 1] += x[pos:pos + m] * r
            pos += m
            i = 0

    def echo(self, beats, fb=.4, mix=.3, cross=True):
        d = int(beats * self.beat * SR)
        wet = np.zeros_like(self.buf)
        tap = self.buf.copy()
        for _ in range(5):
            tap = np.roll(tap, d, axis=0) * fb
            if cross:
                tap = tap[:, ::-1]
            wet += tap
        for c in (0, 1):
            wet[:, c] = loop_filt(wet[:, c], low=4200, high=250)
        self.buf += wet * mix / fb

    def reverb(self, mix=.25, size=1.6):
        n = int(size * SR)
        for c in (0, 1):
            ir = self.rng.standard_normal(n) * np.exp(-np.arange(n) / SR / (size * .28))
            ir = filt(ir, low=5200, high=200, order=2)
            pad = np.zeros(self.n)
            m = min(n, self.n)
            pad[:m] = ir[:m] / np.sqrt(np.sum(ir**2))
            self.buf[:, c] += mix * np.fft.irfft(np.fft.rfft(self.buf[:, c]) * np.fft.rfft(pad), self.n)

    def sidechain(self, depth=.6, every=1.0, rel=.30):
        t = np.arange(self.n) / SR / (self.beat * every) % 1.0
        g = 1 - depth * np.exp(-t / rel) * (t < 1)
        self.buf *= g[:, None]

    def out(self, peak=.85):
        x = self.buf / (np.max(np.abs(self.buf)) + 1e-9) * 1.25
        return np.tanh(x) * peak


# -- instruments ----------------------------------------------------------------------
def kick(dur=.34):
    t = t_axis(dur)
    f = 46 + 130 * np.exp(-t / .028)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / .13)
    x[:60] += np.linspace(.6, 0, 60)
    return drive(x, 1.8)


def snare(rng, dur=.26, tone=190):
    t = t_axis(dur)
    x = filt(noise(len(t), rng), low=8200, high=900, order=2) * np.exp(-t / .075) * .8
    return x + np.sin(2 * np.pi * tone * t) * np.exp(-t / .06) * .5


def clap(rng, dur=.30):
    t = t_axis(dur)
    e = sum(np.where(t > d, np.exp(-(t - d) / .012), 0) for d in (0, .011, .022)) * .6 + np.where(t > .03, np.exp(-(t - .03) / .08), 0)
    return filt(noise(len(t), rng), low=6500, high=1000, order=2) * e * .7


def hat(rng, dur=.07, tau=.022):
    t = t_axis(dur)
    return filt(noise(len(t), rng), high=7200, order=3) * np.exp(-t / tau) * .7


def bass(note, dur, cutoff=700, grit=1.6):
    t = t_axis(dur)
    f = freq(note)
    x = saw(f, t) * .6 + square(f, t, .48) * .3 + sine(f / 2, t) * .7
    n = len(t)
    bright = filt(x, low=cutoff * 2.4, order=2)
    dark = filt(x, low=cutoff * .6, order=2)
    e = np.exp(-t / .12)
    return drive(bright * e + dark * (1 - e), grit) * env(n, .003, .2, .75, .03)


def pad(notes, dur, cutoff=1400, rng=None):
    t = t_axis(dur)
    x = np.zeros((len(t)))
    for nt in notes:
        for k, det in enumerate((-.006, -.002, .003, .007)):
            x += saw(freq(nt), t, det, (k * .37 + nt * .13) % 1)
    x = filt(x / (len(notes) * 4), low=cutoff, order=2)
    return x * env(len(t), .35, 1.0, .85, .5) * (1 + .12 * np.sin(2 * np.pi * .27 * t))


def pluck(note, dur=.35, bright=3200, wave_="saw"):
    t = t_axis(dur)
    f = freq(note)
    x = saw(f, t) + saw(f, t, .004, .3) if wave_ == "saw" else square(f, t, .25) + square(f, t, .27)
    a, b = filt(x, low=bright, order=2, reso=.6), filt(x, low=bright * .25, order=2)
    e = np.exp(-t / .07)
    return (a * e + b * (1 - e)) * np.exp(-t / (dur * .42)) * np.clip((dur - t) / .02, 0, 1) * .45


def lead(note, dur, bright=2600, vib=.004):
    t = t_axis(dur)
    f = freq(note) * (1 + vib * np.sin(2 * np.pi * 5.2 * t) * np.clip(t * 3 - .4, 0, 1))
    ph = np.cumsum(f) / SR
    x = (2 * (ph % 1) - 1) + (2 * ((ph * 1.005 + .25) % 1) - 1) + .5 * np.sign(np.sin(np.pi * ph))
    return filt(x, low=bright, order=2, reso=.4) * env(len(t), .015, .25, .7, .12) * .32


def koto(note, dur=1.1):
    t = t_axis(dur)
    f = freq(note)
    x = sum(np.sin(2 * np.pi * f * k * t * (1 + .0006 * k * k)) * np.exp(-t * (2.2 + 1.5 * k)) / k for k in range(1, 8))
    return x * np.minimum(1, t / .002) * np.clip((dur - t) / .05, 0, 1) * .55


def bell(note, dur=1.4):
    t = t_axis(dur)
    f = freq(note)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) for a, r, d in ((1, 1, 2.6), (.5, 2.76, 4.5), (.3, 5.4, 8), (.2, 8.9, 12)))
    return x * np.clip((dur - t) / .05, 0, 1) * .5


def guitar(note, dur=.5):
    t = t_axis(dur)
    f = freq(note)
    x = sum(saw(f * r, t, d, d * 50) for r, d in ((1, 0), (1, .004), (1.5, .002), (2, .003)))
    return filt(drive(filt(x, low=3500, order=1), 2.6), low=3000, order=2) * env(len(t), .004, .3, .6, .05) * .4


def save(path: Path, x: np.ndarray, peak: float | None = None):
    x = np.asarray(x, float)
    if peak:
        x = x / (np.max(np.abs(x)) + 1e-9) * peak
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else 2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
