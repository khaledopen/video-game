"""Logo animé NEON DRIVE."""
from __future__ import annotations

import math

from config.palette import CYAN, RED, VIOLET, WHITE, alpha, mix
from effects.animation import ease_out
from engine.mathx import clamp


def draw_logo(c, x, y, size, t, progress=1.0, align="l", tagline=True):
    """`progress` 0..1 : apparition lettre par lettre puis balayage lumineux."""
    words = (("NEON", WHITE, CYAN), ("DRIVE", WHITE, VIOLET))
    sp = size * .05
    gap = size * .34
    widths = [c.measure(w, size, spacing=sp) for w, _, _ in words]
    total = sum(widths) + gap
    x0 = x - (total / 2 if align == "c" else 0)
    cx = x0
    n = 0
    for (word, top, col), ww in zip(words, widths):
        for ch in word:
            p = clamp(progress * 1.7 - n * .085)
            cw = c.measure(ch, size)
            if p > 0:
                flick = 1.0 if p >= 1 else (.35 + .65 * (math.sin(p * 46 + n * 7) > -.2))
                a = ease_out(p) * flick
                dy = (1 - ease_out(p)) * size * .35 * (1 if n % 2 else -1)
                breathe = .80 + .20 * math.sin(t * 2.1 + n * .4)
                c.text(cx, y + dy, ch, size, alpha(top, a), color2=alpha(mix(top, col, .92), a), glow=1.05 * a * breathe, glow_col=col, skew=.17)
            cx += cw + sp
            n += 1
        cx += gap
    # soulignement énergétique
    k = ease_out(clamp(progress * 1.6 - .6))
    ly = y + size * .56
    if k > 0:
        c.rect(x0 - size * .10, ly, total * k, size * .035, CYAN, VIOLET, True, skew=.17)
        c.halo(x0 - size * .10 + total * k, ly + size * .02, size * .26, alpha(WHITE, .55 * (1 if k < 1 else .25 + .25 * math.sin(t * 3))))
        s = (t * .22) % 1.4
        if progress >= 1 and s < 1:
            c.rect(x0 + (total - 120) * s, ly - size * .012, 120, size * .06, alpha(WHITE, 0), alpha(WHITE, .8 * math.sin(s * math.pi)), True, skew=.17)
        c.rect(x0 + total * .62, ly + size * .075, total * .38 * k, size * .016, alpha(RED, .9), alpha(RED, 0), True, skew=.17)
    if tagline:
        a = clamp(progress * 2.5 - 1.5)
        c.text(x0 + 2, ly + size * .22, "ENDLESS RACING", size * .185, alpha((.78, .88, 1, 1), a), font="light", spacing=size * .085)
    return total
