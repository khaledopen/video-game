"""Rendu hors écran d'aperçus, pour vérifier les modèles et les univers.

Usage : python tools/preview.py cars|envs|traffic|props [dossier]
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import moderngl                                                        # noqa: E402
import numpy as np                                                     # noqa: E402
from PIL import Image                                                  # noqa: E402

from config.environments import ENVIRONMENTS, PLAYABLE                 # noqa: E402
from config.palette import linear, rgb                                 # noqa: E402
from config.vehicles import VEHICLES                                   # noqa: E402
from engine.mathx import look_angles                                   # noqa: E402
from engine.renderer import FrameView, Renderer, row                   # noqa: E402
from engine.scenery import Scenery                                     # noqa: E402
from engine.track import Track                                         # noqa: E402
from engine.vehicle_draw import Look, draw_player, draw_traffic        # noqa: E402


def main():
    what = sys.argv[1]
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "docs")
    ctx = moderngl.create_standalone_context()
    size = (1280, 720)
    r = Renderer(ctx, size, "high")
    tex = ctx.texture(size, 4)
    fbo = ctx.framebuffer([tex])
    track = Track(3)

    def shot(v, bend, decals, name, **kw):
        r.render(v, bend, decals=decals, target=fbo, **kw)
        img = Image.frombytes("RGBA", size, tex.read()).transpose(Image.FLIP_TOP_BOTTOM).convert("RGB")
        img.save(out / f"{name}.png")
        return img

    flat = np.zeros((320, 2), "f4")
    if what == "cars":
        sheet = Image.new("RGB", (640 * 4, 360 * 4))
        for i, spec in enumerate(VEHICLES):
            for j, ang in enumerate((2.55, -.6)):
                decals = []
                draw_player(r, Look(spec.id, spec.paint, spec.accent, i % 4), (0, 0, 0), ang, decals=decals, steer=.0)
                cam = (0., 1.35, -6.6)
                yaw, pitch = look_angles(cam, (0, .55, 0))
                v = FrameView(env=ENVIRONMENTS[5], cam=cam, yaw=yaw, pitch=pitch, fov=42, studio=True, accent=linear(rgb(spec.accent)), headlights=0)
                img = shot(v, flat, decals, f"_car_{spec.id}_{j}").resize((640, 360))
                sheet.paste(img, ((i % 4) * 640, (i // 4) * 720 + j * 360))
                (out / f"_car_{spec.id}_{j}.png").unlink()
        sheet.save(out / "_cars.png")
    elif what in ("traffic", "props"):
        from engine.models import props as P, traffic as T
        names = list(T.MODELS) if what == "traffic" else [n for n in P.BUILDERS if n not in ("torii", "gantry", "portal", "ring", "wires", "pole", "billboard", "lamp", "antenna", "sign") and not n.startswith("bld")]
        cols = 4
        sheet = Image.new("RGB", (480 * cols, 270 * math.ceil(len(names) / cols)))
        for i, n in enumerate(names):
            decals = []
            if what == "traffic":
                draw_traffic(r, n, (0, 0, 0), .45, 0, 0, linear(rgb("#B8C4D8")), (0, .7, 1.), 0, .4, decals, True, True)
                L = T.MODELS[n]().length
                cam = (0, 1.2 + L * .22, -3.5 - L * 1.15)
            else:
                r.queue(n, [row((0, 0, 0), .5, c1=(.9, .35, .05) if "rock" not in n else (.4, .3, .25), c2=(0, .7, 1.), seed=.3)])
                cam = (0, 1.5, -4.2) if "pine" not in n and "cactus" not in n else (0, 4, -13)
            yaw, pitch = look_angles(cam, (0, .8 if what == "props" and "pine" not in n else 1.0, 0))
            v = FrameView(env=ENVIRONMENTS[5], cam=cam, yaw=yaw, pitch=pitch, fov=42, studio=True, headlights=0, time=1.)
            sheet.paste(shot(v, flat, decals, "_tmp").resize((480, 270)), ((i % cols) * 480, (i // cols) * 270))
        (out / "_tmp.png").unlink()
        sheet.save(out / f"_{what}.png")
    else:
        sc = Scenery(r)
        for env in PLAYABLE:
            track.set_environment(env.index, True)
            s = 1500.0
            bend = track.bend_table(s)
            decals = []
            draw_player(r, Look("inferno", "#FF5A1F", "#00E5FF", 1), (-1.8, 0, 0), .0, decals=decals, glow=.3 if env.index in (1, 3) else 1.)
            cols = ["#D9DEE8", "#6D3BEF", "#C81E3A", "#1440C8", "#8E99AD", "#14161F"]
            lights = []
            for i, (k, lane, z) in enumerate((("sedan", 1.8, 16), ("truck", 5.4, 30), ("bus", -5.4, 45), ("coupe", -1.8, 60), ("van", 1.8, 75), ("roadster", -5.4, 18))):
                draw_traffic(r, k, (lane, 0, z), 0, 0, 0, linear(rgb(cols[i])), (0, .7, 1.), 0, i * .16, decals, True, env.index in (0, 2, 4))
                lights.append((lane, z - 3, 1., 0))
            for i in range(6):
                r.queue("coin", [row((1.8, .8, 8 + i * 4.), .4 + i * .3, c1=(.5, .28, .03), c2=(1, .7, .1))])
            r.queue("pk_nitro", [row((-5.4, 0.1, 12), .3, c1=(0, .8, 1), c2=(0, .8, 1.))])
            sc.queue(env, s, 3.)
            v = FrameView(env=env, time=3., s=s, speed=60, cam=(-1.5, 2.75, -6.4), yaw=0.0, pitch=-.135, fov=66, player_x=-1.8, slope=track.slope(s),
                          curvature=float(track.curvature(np.float64(s))), rain=env.rain, dust=env.dust, lights=lights, accent=(0, .8, 1.))
            shot(v, bend, decals, f"_env_{env.id}")
    print("ok")


main()
