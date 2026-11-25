"""Circulation : comportements, évitement et règle d'équité."""
import random

import pytest

from config.modes import MODES as ALL, BY_ID as MODES
from config.vehicles import VEHICLES
from engine.track import LANES, lane_x
from entities.autopilot import Autopilot
from entities.obstacles import make_obstacle
from entities.player import Controls
from entities.traffic import KINDS, make_vehicle, occupied_lanes
from entities.world import World


def add(w, kind, ds, lane, v):
    a = make_vehicle(random.Random(2), kind, w.player.s + ds, lane, 0)
    a.v = a.want_v = v
    w.vehicles.append(a)
    return a


def advanced(vehicle, mode, seed, s):
    """Partie commencée loin : difficulté élevée."""
    w = World(VEHICLES[vehicle], MODES[mode], seed=seed)
    w.player.s = s
    for a in ("next_obstacle", "next_coins", "next_pickup"):
        setattr(w.spawner, a, s + 200.0)
    return w


def test_all_types_exist():
    assert {"sedan", "coupe", "roadster", "truck", "bus", "van"} <= set(KINDS)


def test_behaviours_vary():
    rng = random.Random(1)
    vs = [make_vehicle(rng, "sedan", 0, 0, .5) for _ in range(200)]
    assert len({v.behaviour for v in vs}) == 4
    assert max(v.want_v for v in vs) - min(v.want_v for v in vs) > 8


def test_follows_without_hitting_leader(world):
    slow = add(world, "truck", 200, 0, 15)
    fast = add(world, "sedan", 120, 0, 35)
    world.ai._lane_free = lambda *a, **k: False           # dépassement interdit
    for _ in range(600):
        world.update(1 / 60, Controls(brake=1))
        assert fast.front < slow.rear + .01
    assert fast.v < 20


def test_changes_lane_before_obstacle(world):
    a = add(world, "sedan", 60, 1, 28)
    world.obstacles.append(make_obstacle("barrier", world.player.s + 240, lane_x(1)))
    changed = False
    for _ in range(60 * 9):
        world.update(1 / 60, Controls(brake=1))
        changed |= a.lane != 1
        for o in world.obstacles:
            assert not (abs(o.x - a.x) < o.half_w + a.width / 2 - .1 and abs(o.s - a.s) < o.half_l + a.length / 2 - .1)
    assert changed


def test_never_cuts_off_player(world):
    a = add(world, "sedan", 9, 2, 25)
    world.player.v = 30
    assert not world.ai._lane_free(a, 1, world.vehicles, [], world.player, False)


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("mode", ("endless", "survival"))
def test_static_rows_always_leave_a_lane(mode, seed):
    w = advanced(0, mode, seed, 12000.0)
    for _ in range(60 * 25):
        w.update(1 / 60, Controls(throttle=1))
        w.player.hp, w.player.invuln = 100, 1.0
        w.drain_events()
        rows = [o for o in w.obstacles if o.solid]
        stalled = [v for v in w.vehicles if v.stalled]
        for o in rows:
            assert len(occupied_lanes(stalled, rows, o.s - 12, o.s + 12)) < LANES


@pytest.mark.parametrize("seed", range(5))
def test_road_never_closes_for_long(seed):
    """La circulation ne doit pas former un mur durable devant le joueur."""
    w = advanced(4, "endless", seed, 9000.0)
    bot, closed, worst = Autopilot(.8), 0.0, 0.0
    for _ in range(60 * 70):
        w.update(1 / 60, bot.control(w, 1 / 60))
        w.player.hp = 100
        w.drain_events()
        p = w.player
        wall = any(len(occupied_lanes(w.vehicles, w.obstacles, p.s + d, p.s + d + 9)) == LANES for d in range(6, 60, 9))
        closed = closed + 1 / 60 if wall else 0.0
        worst = max(worst, closed)
    assert worst < 4.0


@pytest.mark.parametrize("mode", [m.id for m in ALL])
def test_autopilot_goes_far(mode):
    """Un pilote simple doit pouvoir avancer : le jeu n'est jamais injouable."""
    dist = []
    for seed in range(4):
        w = World(VEHICLES[0], MODES[mode], seed=seed)
        bot = Autopilot()
        while not w.over and w.stats.time < 100:
            w.update(1 / 60, bot.control(w, 1 / 60))
            w.drain_events()
        dist.append(w.stats.distance)
    assert sorted(dist)[2] > 2500


def test_difficulty_grows(world):
    d = [world.spawner.difficulty(x) for x in (0, 1000, 5000, 20000)]
    assert d == sorted(d) and d[0] == 0 and d[-1] > .85


def test_world_is_bounded():
    w = World(VEHICLES[0], MODES["survival"], seed=8)
    bot = Autopilot()
    for _ in range(60 * 120):
        w.update(1 / 60, bot.control(w, 1 / 60))
        w.player.hp = 100
        w.drain_events()
        assert len(w.vehicles) < 45 and len(w.obstacles) < 160 and len(w.coins) < 160 and len(w.pickups) < 8


def test_environments_chain():
    w = World(VEHICLES[0], MODES["endless"], seed=8)
    w.spawner.update = lambda *_: None
    for _ in range(60 * 400):
        w.player.hp = 100
        w.update(1 / 60, Controls(throttle=1))
    assert len(w.stats.environments) == 5
