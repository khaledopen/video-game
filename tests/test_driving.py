"""Déplacements : accélération, freinage, inertie, nitro, indépendance aux FPS."""
import math

import pytest

from config.modes import BY_ID as MODES
from config.vehicles import VEHICLES
from entities.player import MIN_SPEED, Controls
from entities.world import World


def drive(w, sec, c, dt=1 / 60):
    for _ in range(round(sec / dt)):
        w.update(dt, c)


def test_progressive_acceleration(world):
    p = world.player
    speeds = []
    for _ in range(8):
        drive(world, .5, Controls(throttle=1))
        speeds.append(p.v)
    assert all(b > a for a, b in zip(speeds, speeds[1:]))
    assert speeds[1] - speeds[0] > speeds[-1] - speeds[-2]        # de moins en moins vite
    assert p.v <= p.top * 1.12


def test_brake_and_minimum_speed(world):
    world.player.v = 60
    drive(world, 1, Controls(brake=1))
    assert world.player.v < 45
    drive(world, 5, Controls(brake=1))
    assert world.player.v == pytest.approx(MIN_SPEED, abs=.5)


def test_coasting_returns_to_cruise(world):
    world.player.v = world.player.top
    drive(world, 12, Controls())
    assert world.player.v == pytest.approx(world.player.cruise, rel=.05)


@pytest.mark.parametrize("side", (-1, 1))
def test_steering_direction_and_inertia(world, side):
    p = world.player
    p.x = 0
    drive(world, .05, Controls(steer=side))
    assert 0 < p.vx * side < p.lateral_max * .75                  # pas de vitesse latérale instantanée
    drive(world, .4, Controls(steer=side))
    assert p.x * side > 1
    v = p.vx
    drive(world, .05, Controls())
    assert 0 < p.vx * side < v * side                             # glisse encore après relâchement


def test_car_leans_and_yaws(world):
    world.player.x = 0
    drive(world, .25, Controls(steer=1))
    assert world.player.roll < -.02 and world.player.yaw > .02


def test_never_leaves_road(world):
    for side in (-1, 1):
        drive(world, 4, Controls(steer=side, throttle=1))
        assert abs(world.player.x) <= world.player.edge + 1e-6


@pytest.mark.parametrize("fps", (30, 60, 144, 240))
def test_frame_rate_independence(fps):
    def run(f):
        w = World(VEHICLES[2], MODES["endless"], seed=3)
        w.spawner.update = lambda *_: None
        w.player.x = -4
        drive(w, 2, Controls(throttle=1, steer=.35), 1 / f)
        return w.player
    a, b = run(120), run(fps)
    assert b.s == pytest.approx(a.s, rel=.012)
    assert b.x == pytest.approx(a.x, abs=.15)


def test_nitro_boosts_drains_and_stops(world):
    p = world.player
    drive(world, 4, Controls(throttle=1))
    base = p.v
    p.nitro = 1.0
    drive(world, 2, Controls(throttle=1, nitro=True))
    assert p.nitro_on and p.v > base * 1.08 and p.nitro < .6
    drive(world, 6, Controls(throttle=1, nitro=True))
    assert p.nitro < .15


def test_nitro_regenerates(world):
    world.player.nitro = 0
    drive(world, 10, Controls(throttle=1))
    assert world.player.nitro > .1


def test_vehicles_have_distinct_characters():
    keys = {(v.top_speed, v.accel, v.handling, v.armor, v.nitro) for v in VEHICLES}
    assert len(VEHICLES) == 8 and len(keys) == 8
    assert [v.name for v in VEHICLES] == ["NEON GT", "SHADOW X", "PHANTOM RS", "THUNDER V8", "CYBER R", "INFERNO", "VELOCITY", "APEX ONE"]
    prices = [v.price for v in VEHICLES]
    assert prices[0] == 0 and prices == sorted(prices)


def test_faster_car_goes_further():
    def dist(i):
        w = World(VEHICLES[i], MODES["endless"], seed=1)
        w.spawner.update = lambda *_: None
        drive(w, 15, Controls(throttle=1))
        return w.player.s
    assert dist(7) > dist(0) * 1.15


def test_curve_pushes_outward(world):
    p = world.player
    p.x, p.v = 0, 70
    p.update(.5, Controls(throttle=1), .0016)
    assert p.x < 0 and math.isfinite(p.x)
