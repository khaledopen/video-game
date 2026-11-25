"""Pilote automatique : fond du menu, démonstration et tests d'équité."""
from __future__ import annotations

from engine.mathx import clamp
from engine.track import LANES, lane_x, nearest_lane
from entities.player import Controls


class Autopilot:
    def __init__(self, pace: float = 1.0):
        self.target = None
        self.hold = 0.0
        self.pace = pace

    def _time_to_block(self, world, lane) -> float:
        """Secondes avant de rencontrer quelque chose dans cette voie."""
        p = world.player
        x, best = lane_x(lane), 9.0
        for v in world.vehicles:
            gap = v.rear - (p.s + p.length / 2)
            if gap < -v.length - p.length - 1.5 or gap > 260:
                continue
            fx = v.x + clamp(lane_x(v.target_lane) - v.x, -2.2, 2.2)
            if min(abs(v.x - x), abs(fx - x)) < (v.width + p.width) / 2 + .35:
                if gap <= 1.5:
                    return 0.0
                best = min(best, gap / max(1.0, p.v - v.v) if p.v > v.v else 9.0)
        for o in world.obstacles:
            if o.dead or o.kind == "puddle":
                continue
            gap = o.s - o.half_l - (p.s + p.length / 2)
            if -p.length - 1 < gap < 260 and abs(o.x - x) < o.half_w + p.width / 2 + .3:
                best = min(best, max(0.0, gap) / max(1.0, p.v))
        return best

    def control(self, world, dt: float) -> Controls:
        p = world.player
        cur = nearest_lane(p.x)
        self.hold -= dt
        times = [self._time_to_block(world, l) for l in range(LANES)]
        best, score = cur, -1e9
        for l in range(LANES):
            step = 1 if l > cur else -1
            path = times[l] if l == cur else min([times[m] + (.35 if m != l else 0) for m in range(cur + step, l + step, step)] + [times[l]])
            if l != cur and any(times[m] < .30 for m in range(cur + step, l + step, step)):
                path = -1
            sc = min(path, 4.0) - .16 * abs(l - cur) - (.12 if l in (0, 3) else 0)
            if l == self.target:
                sc += .30
            if sc > score:
                best, score = l, sc
        if self.target is None or self.hold <= 0 or times[self.target] < .8:
            if best != self.target:
                self.target, self.hold = best, .35
        tx = lane_x(self.target)
        c = Controls()
        c.steer = clamp((tx - p.x) * .85 - p.vx * .09, -1, 1)
        t = min(times[cur], max(times[self.target], .0) if self.target == cur else times[cur])
        if t < 1.0:
            c.brake = clamp((1.15 - t) * 1.4)
        elif t > 1.8:
            c.throttle = self.pace
        return c
