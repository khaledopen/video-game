"""Fabrique toute la bande-son originale du jeu dans assets/audio.

Usage : python tools/build_audio.py        (environ une minute)
Tout est synthétisé : aucune ressource externe, aucun droit d'auteur tiers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np                          # noqa: E402

from audio import synth as S                # noqa: E402
from config.paths import AUDIO              # noqa: E402

SR = S.SR


# -- musique ------------------------------------------------------------------------------
TRACKS = {
    # bpm, accords (4), gamme d'arpège, style
    "menu": (96, [(45, 52, 57, 60, 64), (41, 48, 53, 57, 60), (48, 52, 55, 60, 64), (43, 50, 55, 59, 62)], "menu"),
    "neon_city": (118, [(42, 49, 54, 57, 61), (38, 45, 50, 54, 57), (45, 49, 52, 57, 61), (40, 47, 52, 56, 59)], "city"),
    "desert_highway": (106, [(40, 47, 52, 55, 59), (43, 50, 55, 59, 62), (38, 45, 50, 54, 57), (45, 52, 57, 60, 64)], "desert"),
    "rainy_tokyo": (122, [(44, 51, 56, 59, 63), (40, 47, 52, 56, 59), (47, 51, 54, 59, 63), (42, 49, 54, 58, 61)], "tokyo"),
    "mountain_road": (112, [(38, 45, 50, 54, 57), (43, 50, 55, 59, 62), (47, 50, 54, 59, 62), (45, 52, 57, 61, 64)], "mountain"),
    "cyber_tunnel": (132, [(41, 48, 53, 56, 60), (41, 48, 53, 56, 60), (37, 44, 49, 53, 56), (39, 46, 51, 55, 58)], "tunnel"),
}


def compose(name):
    bpm, chords, style = TRACKS[name]
    bars = 16
    base, full = S.Song(bars, bpm, 1), S.Song(bars, bpm, 2)
    rng = np.random.default_rng(abs(hash(style)) % 1000 if False else sum(map(ord, style)))
    k, sn, cl, hh, oh = S.kick(), S.snare(rng), S.clap(rng), S.hat(rng), S.hat(rng, .22, .07)
    beat = base.beat
    padcut = {"menu": 1300, "city": 1500, "desert": 1100, "tokyo": 1700, "mountain": 2100, "tunnel": 1000}[style]
    for bar in range(bars):
        ch = chords[bar % 4]
        b0 = bar * 4
        second = bar >= 8
        # nappe
        pd = S.pad(ch[2:], 4 * beat + .5, padcut)
        base.put(pd, b0, .95, -.25)
        base.put(S.pad([n + 12 for n in ch[2:4]], 4 * beat + .5, padcut * 1.2), b0, .45, .35)
        # basse
        root = ch[0] - 12 if ch[0] > 43 else ch[0]
        if style == "menu":
            for p in (0, 1.5, 2.5):
                base.put(S.bass(root, beat * .9, 420), b0 + p, .75)
        elif style == "tunnel":
            for i in range(16):
                if i % 4 != 0:
                    base.put(S.bass(root + (12 if i % 8 == 6 else 0), beat * .22, 700 + 500 * np.sin(bar * .8 + i * .3) ** 2, 2.2), b0 + i * .25, .75)
        elif style == "desert":
            for p, o in ((0, 0), (.75, 0), (1.5, 7), (2, 0), (2.75, 0), (3.5, 5)):
                base.put(S.bass(root + o, beat * .55, 520), b0 + p, .8)
        else:
            for i in range(8):
                o = 12 if (i in (3, 6) and style != "mountain") else 0
                base.put(S.bass(root + o, beat * .42, 640 if style != "tokyo" else 820), b0 + i * .5 + (.0 if style != "tokyo" else 0), .75)
        # batterie légère
        if style == "menu":
            for p in (0, 2):
                base.put(k, b0 + p, .75)
            base.put(cl, b0 + 2, .16)
            for i in range(8):
                base.put(hh, b0 + i * .5, .10 + .05 * (i % 2), .2)
        else:
            for p in range(4):
                base.put(k, b0 + p, .95)
            for p in (1, 3):
                base.put(sn if style in ("desert", "mountain") else cl, b0 + p, .55)
        # pistes intenses
        if style != "menu":
            for i in range(16):
                full.put(hh, b0 + i * .25, .20 + .12 * (i % 4 == 2), .25 * (-1) ** i)
            for p in (.5, 1.5, 2.5, 3.5):
                full.put(oh, b0 + p, .32, -.15)
            if bar % 4 == 3:
                for i in range(6):
                    full.put(sn, b0 + 3 + i / 6, .20 + .07 * i, (-.4 + .15 * i))
            if bar % 8 == 0:
                cr = S.filt(S.noise(int(1.8 * SR), rng), high=3500, order=2) * S.exp_env(int(1.8 * SR), .5)
                full.put(cr, b0, .30)
        # arpèges et mélodies
        tones = list(ch[2:]) + [ch[2] + 12, ch[3] + 12]
        if style in ("city", "menu"):
            pat = (0, 2, 1, 3, 2, 4, 3, 1, 0, 3, 2, 4, 1, 3, 2, 4)
            tgt = full if style == "city" else base
            for i in range(16):
                tgt.put(S.pluck(tones[pat[i] % len(tones)] + 12, .34, 2600 + 900 * np.sin(bar * .5)), b0 + i * .25, .50 if style == "city" else .26, .45 * np.sin(i * 1.3))
        elif style == "desert":
            for p, n in ((0, 2), (.5, 2), (1.5, 3), (2.5, 4), (3, 3)):
                full.put(S.guitar(tones[n - 2] + 0, beat * .7), b0 + p, .55, -.3)
            if second:
                for p, n in ((0, 4), (1, 3), (1.5, 2), (2.5, 3)):
                    full.put(S.lead(tones[n] + 12, beat * 1.1), b0 + p, .42, .3)
        elif style == "tokyo":
            penta = [ch[2] + 12, ch[2] + 15, ch[3] + 12, ch[4] + 12, ch[4] + 15]
            pat = (0, -1, 2, 3, -1, 4, 3, -1, 2, -1, 3, 1, -1, 2, 0, -1)
            for i, n in enumerate(pat):
                if n >= 0:
                    full.put(S.koto(penta[n]), b0 + i * .25, .55, .4 * np.sin(i * 2.1))
            if second:
                for i in range(8):
                    full.put(S.pluck(tones[(i * 2) % len(tones)] + 24, .25, 4200, "sq"), b0 + i * .5 + .25, .22, -.4)
        elif style == "mountain":
            for i in range(8):
                full.put(S.bell(tones[(i * 3 + bar) % len(tones)] + 12, .9), b0 + i * .5, .32, .5 * np.sin(i * 1.7))
            if second:
                mel = ((0, 3), (1.5, 4), (2, 3), (3, 2)) if bar % 2 == 0 else ((0, 2), (1, 3), (2, 1))
                for p, n in mel:
                    full.put(S.lead(tones[n] + 12, beat * 1.3, 3000), b0 + p, .45, 0)
        else:
            for i in range(16):
                if (i * 5 + bar) % 8 < 5:
                    full.put(S.pluck(tones[(i * 3) % len(tones)] + (12 if i % 3 else 24), .20, 2000 + 2600 * (bar % 8) / 8), b0 + i * .25, .46, .6 * (-1) ** i)
            if bar % 2 == 1:
                full.put(S.lead(ch[4] + 12, beat * 1.8, 1800), b0 + 2, .30, .2)
        if style == "city" and second:
            mel = ((0, 4, 1.4), (1.5, 3, .4), (2, 2, 1.2), (3.25, 3, .7))
            for p, n, d in mel:
                full.put(S.lead(tones[n] + 12, beat * d, 3000), b0 + p, .40, -.1)
        if style == "menu" and bar % 2 == 0:
            for p, n, d in ((0, 4, 2.6), (3, 3, .9)):
                base.put(S.lead(tones[n], beat * d, 1500), b0 + p, .30, .1)
    full.echo(.75, .42, .34)
    base.reverb(.20, 1.8)
    full.reverb(.16, 1.4)
    if style != "menu":
        base.sidechain(.38, 1.0, .22)
    S.save(AUDIO / f"music_{name}_base.wav", base.out(.80))
    if style != "menu":
        S.save(AUDIO / f"music_{name}_full.wav", full.out(.62))


# -- moteurs ------------------------------------------------------------------------------------
def engine(kind, idx, count):
    n = SR
    t = np.arange(n) / SR
    rng = np.random.default_rng(idx)
    r = idx / (count - 1)
    if kind == "electric":
        f = round(120 + 820 * r)
        x = .5 * np.sin(2 * np.pi * f * t) + .35 * np.sin(2 * np.pi * round(f * 1.5) * t) + .20 * np.sin(2 * np.pi * round(f * 2.98) * t + .6 * np.sin(2 * np.pi * 24 * t))
        x += .30 * np.sin(2 * np.pi * round(f * .25) * t)
        x += .18 * S.loop_filt(rng.standard_normal(n), low=1200 + 2500 * r, high=300)
    else:
        f = round((34 if kind == "v8" else 46) + (112 if kind == "v8" else 168) * r)       # fréquence d'allumage
        jit = np.zeros(n)
        for h in range(1, 4):
            jit += np.sin(2 * np.pi * h * t * 3 + rng.random() * 6) * .010
        ph = 2 * np.pi * (f * t + jit)
        x = np.zeros(n)
        harm = {"v8": (1, .9, .55, .75, .42, .3, .34, .2, .16, .12, .1, .08), "turbo": (.8, 1, .75, .45, .6, .35, .25, .3, .2, .16, .13, .1)}[kind]
        for h, a in enumerate(harm, 1):
            x += a * np.sin(ph * h + h * 1.3) / (1 + .12 * h * (1 - r))
        if kind == "v8":
            x *= 1 + .38 * np.sin(2 * np.pi * round(f / 2) * t) + .15 * np.sin(2 * np.pi * round(f / 4) * t)
        x = np.tanh(x * (.7 + .7 * r))
        nz = S.loop_filt(rng.standard_normal(n), low=900 + 2600 * r, high=180)
        x += nz / np.max(np.abs(nz)) * (.16 + .22 * r) * (1 + .5 * np.sin(ph))
        if kind == "turbo":
            x += .10 * r * np.sin(2 * np.pi * round(1500 + 2600 * r) * t)
        x = S.loop_filt(x, low=1300 + 3600 * r, high=38, order=2)
    S.save(AUDIO / f"engine_{kind}_{idx}.wav", x, .72)


# -- effets ---------------------------------------------------------------------------------------
def whoosh(dur, f0, f1, rng, tau=None, up=True):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    parts = 24
    for i in range(parts):
        c = f0 * (f1 / f0) ** (i / (parts - 1))
        w = np.exp(-((np.arange(n) / n - i / (parts - 1)) * parts * .7) ** 2)
        out += S.filt(x, low=c * 1.5, high=c * .6, order=2) * w
    e = np.sin(np.pi * np.clip(np.arange(n) / n, 0, 1)) ** .8
    return out * e


def effects():
    rng = np.random.default_rng(7)

    def mix(*parts):
        n = max(len(x) + int(d * SR) for x, d, _ in parts)
        out = np.zeros(n)
        for x, d, g in parts:
            i = int(d * SR)
            out[i:i + len(x)] += x * g
        return out

    def tone(f0, f1, dur, shape="sine", tau=None):
        t = S.t_axis(dur)
        f = f0 * (f1 / f0) ** (t / dur)
        ph = np.cumsum(f) / SR
        x = np.sin(2 * np.pi * ph) if shape == "sine" else 2 * (ph % 1) - 1 if shape == "saw" else np.sign(np.sin(2 * np.pi * ph))
        return x * np.minimum(1, t / .004) * np.exp(-t / (tau or dur * .4)) * np.clip((dur - t) / .01, 0, 1)

    P = AUDIO
    # interface
    S.save(P / "ui_hover.wav", mix((tone(1500, 1900, .06, tau=.02), 0, .6), (tone(3000, 3600, .04, tau=.012), 0, .2)), .35)
    S.save(P / "ui_click.wav", mix((tone(520, 1040, .10, tau=.04), 0, .7), (tone(1560, 2080, .16, tau=.06), .03, .5), (S.hat(rng, .05, .01), 0, .4)), .55)
    S.save(P / "ui_back.wav", mix((tone(980, 460, .14, tau=.05), 0, .7), (tone(1960, 900, .10, tau=.03), 0, .25)), .5)
    S.save(P / "ui_denied.wav", mix((S.filt(tone(190, 180, .12, "square"), low=1400), 0, .6), (S.filt(tone(150, 140, .18, "square"), low=1200), .11, .6)), .5)
    S.save(P / "ui_unlock.wav", mix(*[(S.bell(n, 1.3), i * .07, .6) for i, n in enumerate((69, 73, 76, 81, 85))], (whoosh(.7, 300, 5000, rng), 0, .25)), .7)
    S.save(P / "ui_transition.wav", mix((whoosh(.6, 240, 3800, rng), 0, .8), (tone(70, 40, .5, tau=.2), .12, .7)), .45)
    S.save(P / "ui_tick.wav", tone(1320, 1320, .09, tau=.03), .5)
    S.save(P / "ui_go.wav", mix((S.lead(81, .6, 4000), 0, .9), (S.lead(69, .6, 3000), 0, .6), (S.kick(), 0, .7)), .7)
    S.save(P / "ui_count.wav", mix((S.lead(69, .22, 3000), 0, 1), (S.kick(), 0, .6)), .6)
    # démarrage : montée, impact, accord
    boot = mix((whoosh(2.2, 90, 5200, rng), 0, .55), (tone(40, 160, 2.2, "saw", 3.0) * np.linspace(0, 1, int(2.2 * SR)) ** 2, 0, .30),
               (S.kick(.6), 2.15, 1.3), (tone(55, 32, 1.8, tau=.7), 2.15, .9),
               (S.pad((57, 64, 69, 73, 76), 2.6, 2600), 2.15, .9), *[(S.bell(n, 1.8), 2.2 + i * .12, .35) for i, n in enumerate((81, 85, 88, 93))])
    S.save(P / "boot.wav", boot, .85)
    # conduite
    S.save(P / "coin.wav", mix((S.bell(88, .30), 0, .6), (S.bell(95, .42), .055, .7)), .42)
    S.save(P / "coin_big.wav", mix(*[(S.bell(n, .6), i * .05, .6) for i, n in enumerate((83, 88, 92, 95))]), .55)
    t = S.t_axis(1.4)
    jet = S.filt(rng.standard_normal(len(t)), low=2600, high=140, order=2) * np.minimum(1, t / .05) * np.exp(-np.maximum(0, t - .25) / .5)
    S.save(P / "nitro_start.wav", mix((jet, 0, .8), (tone(60, 240, .5, "saw", .5), 0, .25), (S.kick(.5), 0, .8), (whoosh(.8, 400, 6000, rng), 0, .5)), .85)
    n = 2 * SR
    x = S.loop_filt(rng.standard_normal(n), low=2300, high=110) * 1.0
    x /= np.max(np.abs(x))
    tt = np.arange(n) / SR
    x = x * (1 + .25 * np.sin(2 * np.pi * 17 * tt)) + .18 * np.sin(2 * np.pi * 92 * tt) + .08 * np.sin(2 * np.pi * 368 * tt + np.sin(2 * np.pi * 5 * tt))
    S.save(P / "nitro_loop.wav", x, .55)
    S.save(P / "nitro_end.wav", whoosh(.5, 3000, 220, rng), .45)
    x = S.loop_filt(rng.standard_normal(SR), low=2600, high=900)
    x = x / np.max(np.abs(x)) * .5
    tt = np.arange(SR) / SR
    for f, a in ((880, .34), (1174, .22), (1320, .16)):
        x += a * np.sin(2 * np.pi * f * tt + 2.4 * np.sin(2 * np.pi * 23 * tt) + 1.3 * np.sin(2 * np.pi * 41 * tt))
    S.save(P / "brake.wav", S.loop_filt(x, low=4200, high=500), .38)

    def crash(dur, deep, glass):
        n = int(dur * SR)
        t_ = np.arange(n) / SR
        x_ = S.filt(rng.standard_normal(n), low=2400, high=60, order=2) * np.exp(-t_ / (dur * .18)) * 1.1
        x_ += np.sin(2 * np.pi * np.cumsum(38 + 90 * np.exp(-t_ / .05)) / SR) * np.exp(-t_ / .22) * deep
        for _ in range(9):
            f, d = rng.uniform(500, 3800), rng.uniform(0, .14)
            x_ += np.where(t_ > d, np.sin(2 * np.pi * f * t_) * np.exp(-np.maximum(0, t_ - d) / rng.uniform(.03, .16)), 0) * .10
        for _ in range(int(26 * glass)):
            d, f = rng.uniform(.05, dur * .6), rng.uniform(3200, 8500)
            x_ += np.where(t_ > d, np.sin(2 * np.pi * f * t_) * np.exp(-np.maximum(0, t_ - d) / .018), 0) * .07
        return np.tanh(x_ * 1.4)
    S.save(P / "crash.wav", crash(1.5, 1.0, 1.0), .95)
    S.save(P / "bump.wav", crash(.55, .7, .2), .75)
    S.save(P / "destroyed.wav", mix((crash(2.6, 1.4, 1.6), 0, 1), (tone(220, 28, 2.2, "saw", .8), .05, .4), (whoosh(1.6, 2400, 90, rng), .1, .6)), .98)
    sc = S.filt(rng.standard_normal(int(.30 * SR)), low=5200, high=1500, order=2)
    S.save(P / "scrape.wav", sc * np.hanning(len(sc)) * (1 + .7 * np.sin(2 * np.pi * 83 * np.arange(len(sc)) / SR)), .45)
    S.save(P / "cone.wav", mix((tone(420, 120, .16, tau=.04), 0, .8), (S.hat(rng, .10, .02), 0, .5)), .6)
    sp = S.filt(rng.standard_normal(int(.7 * SR)), low=3600, high=400, order=2)
    S.save(P / "splash.wav", sp * np.exp(-np.arange(len(sp)) / SR / .18) * np.minimum(1, np.arange(len(sp)) / SR / .02), .6)
    S.save(P / "near_miss.wav", mix((whoosh(.42, 700, 3600, rng), 0, 1), (tone(980, 1470, .25, tau=.1), .1, .25)), .55)
    S.save(P / "shield_hit.wav", mix((tone(300, 900, .5, tau=.2), 0, .5), (S.bell(64, .9), 0, .6), (whoosh(.4, 4000, 400, rng), 0, .5)), .7)
    # bonus : un motif par type
    motif = {"nitro": (64, 71, 76, 83), "shield": (57, 64, 69, 76), "magnet": (72, 67, 72, 79), "repair": (65, 69, 72, 77), "multi": (76, 80, 83, 88), "slow": (81, 76, 69, 57)}
    for kind, notes in motif.items():
        step = .10 if kind == "slow" else .06
        parts = [(S.pluck(nt, .5, 4200, "sq" if kind in ("multi", "magnet") else "saw"), i * step, .8) for i, nt in enumerate(notes)]
        parts += [(S.bell(notes[-1] + 12, .9), len(notes) * step, .35), (whoosh(.5, 500, 4200, rng) if kind != "slow" else whoosh(.9, 4200, 200, rng), 0, .25)]
        S.save(P / f"pk_{kind}.wav", mix(*parts), .6)
    # progression
    S.save(P / "level_up.wav", mix(*[(S.lead(nt, .30, 4200), i * .09, .7) for i, nt in enumerate((69, 73, 76, 81))], (S.pad((69, 73, 76), 1.2, 3000), .2, .6)), .6)
    S.save(P / "portal.wav", mix((whoosh(1.3, 120, 7000, rng), 0, .9), (tone(90, 45, 1.2, tau=.5), .3, .8), *[(S.bell(nt, 1.4), .35 + i * .06, .35) for i, nt in enumerate((76, 83, 88))]), .75)
    rec = [(S.lead(nt, d, 4600), p, .8) for nt, p, d in ((69, 0, .16), (73, .16, .16), (76, .32, .16), (81, .48, .5), (80, .98, .14), (81, 1.12, .9))]
    rec += [(S.pad((57, 64, 69, 73, 76), 2.4, 3600), .48, .9), (S.kick(.5), .48, .9)] + [(S.bell(nt, 1.4), .5 + i * .08, .4) for i, nt in enumerate((81, 85, 88, 93, 97))]
    S.save(P / "new_record.wav", mix(*rec), .85)
    S.save(P / "achievement.wav", mix(*[(S.bell(nt, 1.0), i * .08, .6) for i, nt in enumerate((76, 81, 88))]), .6)
    S.save(P / "game_over.wav", mix((S.pad((45, 52, 57, 60), 3.0, 900), 0, 1), *[(S.lead(nt, .7, 1600), .3 + i * .45, .5) for i, nt in enumerate((64, 60, 57, 52))], (tone(60, 30, 2.4, tau=1), 0, .8)), .75)
    S.save(P / "warning.wav", mix((S.filt(tone(880, 880, .12, "square", .5), low=3200), 0, .5), (S.filt(tone(660, 660, .12, "square", .5), low=3200), .16, .5)), .4)


def ambiences():
    rng = np.random.default_rng(3)
    n = 6 * SR
    t = np.arange(n) / SR

    def nz(low, high):
        x = S.loop_filt(rng.standard_normal(n), low=low, high=high)
        return x / np.max(np.abs(x))
    rain = nz(7000, 900) * .5 + nz(1400, 200) * .4
    for _ in range(420):
        i = rng.integers(0, n - 400)
        rain[i:i + 400] += np.sin(2 * np.pi * rng.uniform(1800, 5200) * np.arange(400) / SR) * np.exp(-np.arange(400) / 60) * rng.uniform(.05, .22)
    S.save(AUDIO / "amb_rainy_tokyo.wav", rain, .55)
    wind = nz(520, 70) * (1 + .45 * np.sin(2 * np.pi * t / 6) + .3 * np.sin(2 * np.pi * t / 2 + 1))
    S.save(AUDIO / "amb_desert_highway.wav", wind, .50)
    S.save(AUDIO / "amb_mountain_road.wav", nz(900, 150) * (1 + .5 * np.sin(2 * np.pi * t / 3 + 2)) * .7, .40)
    hum = .5 * np.sin(2 * np.pi * 55 * t) + .3 * np.sin(2 * np.pi * 110 * t + np.sin(2 * np.pi * t / 2)) + nz(420, 60) * .7
    S.save(AUDIO / "amb_neon_city.wav", hum, .38)
    tun = .5 * np.sin(2 * np.pi * 73 * t) * (1 + .4 * np.sin(2 * np.pi * t * .5)) + nz(800, 120) * .8 * (1 + .5 * np.sin(2 * np.pi * t * 1.5))
    S.save(AUDIO / "amb_cyber_tunnel.wav", tun, .45)


def main():
    AUDIO.mkdir(parents=True, exist_ok=True)
    effects()
    ambiences()
    for kind in ("v8", "turbo", "electric"):
        for i in range(7):
            engine(kind, i, 7)
    for name in TRACKS:
        compose(name)
        print("musique", name)
    files = list(AUDIO.glob("*.wav"))
    print(len(files), "fichiers,", round(sum(f.stat().st_size for f in files) / 1e6, 1), "Mo")


if __name__ == "__main__":
    main()
