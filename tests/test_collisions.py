"""Collisions : boîtes orientées, chocs, obstacles, bonus, pièces."""
import math
import random

import pytest

from config.modes import BY_ID as MODES
from config.vehicles import VEHICLES
from entities.collision import circle_hit, obb_overlap
from entities.obstacles import Coin, Pickup, make_obstacle
from entities.player import Controls
from entities.traffic import make_vehicle
from entities.world import World


def put_vehicle(w, kind="sedan", ds=20.0, lane=1, v=20.0):
    a = make_vehicle(random.Random(1), kind, w.player.s + ds, lane, 0)
    a.v = a.want_v = v
    w.vehicles.append(a)
    return a


def run(w, sec, c=None):
    ev = []
    for _ in range(round(sec * 60)):
        w.update(1 / 60, c or Controls())
        ev += w.drain_events()
    return ev


def kinds(ev):
    return [e.kind for e in ev]


def test_obb_separating_axis():
    assert obb_overlap(0, 0, 1, 2, 0, 1.9, 0, 1, 2, 0)
    assert not obb_overlap(0, 0, 1, 2, 0, 2.1, 0, 1, 2, 0)
    # deux rectangles en biais dont les boîtes alignées se touchent mais pas les formes
    assert not obb_overlap(0, 0, .2, 3, math.pi / 4, 2.2, -2.2, .2, 3, math.pi / 4)
    pen, nx, ns = obb_overlap(0, 0, 1, 2, 0, 1.5, 0, 1, 2, 0)
    assert pen == pytest.approx(.5) and nx == pytest.approx(-1) and abs(ns) < 1e-9


def test_circle_hit():
    assert circle_hit(0, 0, 1, 2, 1.4, 0, .5)
    assert not circle_hit(0, 0, 1, 2, 1.6, 2.6, .5)


def test_rear_end_hurts_slows_and_pushes(world):
    p = world.player
    p.v = 60
    a = put_vehicle(world, v=20)
    ev = run(world, .6, Controls(throttle=1))
    assert "crash" in kinds(ev)
    assert p.hp < 85 and p.v < 50
    assert a.v > 20 or a.hit > 0


def test_side_swipe_is_lighter(world):
    p = world.player
    p.x, p.v = 0.0, 30
    put_vehicle(world, ds=0, lane=2, v=30)
    ev = run(world, .5, Controls(steer=1))
    assert "bump" in kinds(ev) and 75 < p.hp < 100


def test_no_tunnelling_at_full_speed(world):
    p = world.player
    p.v = 120
    world.obstacles.append(make_obstacle("barrier", p.s + 30, p.x))
    ev = []
    for _ in range(40):
        world.update(1 / 15, Controls())            # 15 images/s : pas physique fixe
        ev += world.drain_events()
    assert "crash" in kinds(ev)


def test_no_false_collision_in_next_lane(world):
    put_vehicle(world, ds=15, lane=2, v=10)
    world.obstacles.append(make_obstacle("barrier", world.player.s + 60, 5.4))
    ev = run(world, 2.5, Controls())
    assert not {"crash", "bump"} & set(kinds(ev)) and world.player.hp == 100


@pytest.mark.parametrize("kind,lo,hi", (("barrier", 8, 60), ("roadworks", 8, 60), ("debris", 2, 20), ("cone", .5, 8)))
def test_obstacle_damage(world, kind, lo, hi):
    p = world.player
    p.v = 45
    world.obstacles.append(make_obstacle(kind, p.s + 20, p.x))
    run(world, 1)
    assert lo < 100 - p.hp < hi


def test_puddle_reduces_grip(world):
    p = world.player
    world.obstacles.append(make_obstacle("puddle", p.s + 8, p.x))
    ev = run(world, .4)
    assert "splash" in kinds(ev) and p.slip > 0 and p.hp == 100


def test_invulnerability_after_crash(world):
    p = world.player
    world._hurt(20, 0, 0, "barrier", 1.0)
    hp = p.hp
    world._hurt(20, 0, 0, "barrier", 1.0)
    assert p.hp == hp < 100


def test_shield_absorbs(world):
    p = world.player
    p.give("shield")
    p.v = 60
    put_vehicle(world, v=20)
    ev = run(world, 1.0, Controls(throttle=1))
    assert "shield_hit" in kinds(ev) and p.hp == 100


def test_wall_contact(world):
    p = world.player
    p.v = 50
    ev = run(world, 2, Controls(steer=-1))
    assert {"bump", "scrape"} & set(kinds(ev)) and p.hp < 100


def test_destruction_ends_game(world):
    world.player.hp = 1
    world._hurt(50, 0, 0, "barrier", 1.0)
    assert world.over and not world.player.alive and "destroyed" in kinds(world.drain_events())
    run(world, 4)
    assert world.player.v < 5


def test_time_attack_is_not_lethal():
    w = World(VEHICLES[0], MODES["time_attack"], seed=1)
    w.spawner.update = lambda *_: None
    t = w.time_left
    w._hurt(80, 0, 0, "barrier", 1.0)
    assert w.player.alive and w.player.hp == 100 and w.time_left < t - 1.5
    run(w, 92)
    assert w.over and w.over_reason == "time"


def test_coin_and_score(world):
    p = world.player
    world.coins.append(Coin(p.s + 10, p.x))
    world.coins.append(Coin(p.s + 10, p.x + 5))
    ev = run(world, .8)
    assert kinds(ev).count("coin") == 1 and world.stats.coins == 1


def test_magnet_attracts(world):
    p = world.player
    p.give("magnet")
    world.coins.append(Coin(p.s + 30, p.x + 4))
    run(world, 1.6)
    assert world.stats.coins == 1


@pytest.mark.parametrize("kind", ("nitro", "shield", "magnet", "repair", "multi", "slow"))
def test_every_pickup(world, kind):
    p = world.player
    p.hp, p.nitro = 40, .1
    m = world.multiplier
    world.pickups.append(Pickup(kind, p.s + 8, p.x))
    ev = run(world, .6)
    assert "pickup" in kinds(ev)
    if kind == "nitro":
        assert p.nitro > .5
    elif kind == "repair":
        assert p.hp == 75
    else:
        assert p.active(kind)
    if kind == "multi":
        assert world.multiplier == pytest.approx(m * 2)


def test_slow_bonus_slows_traffic(world):
    a = put_vehicle(world, ds=150, lane=3, v=30)
    world.player.give("slow")
    run(world, 4)
    assert a.v < 22


def test_near_miss_rewards(world):
    p = world.player
    p.x, p.v = -.35, 60
    put_vehicle(world, ds=30, lane=2, v=15)
    n = p.nitro
    ev = run(world, 1.2, Controls(throttle=1))
    assert "near_miss" in kinds(ev) and world.combo == 1 and p.nitro > n and world.stats.near_misses == 1
