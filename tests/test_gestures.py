"""Contrôle gestuel : reconnaissance, filtrage, volant, calibration, thread."""
import math
import time
from pathlib import Path

import numpy as np
import pytest

from computer_vision.gestures import FIST, OPEN, TWO, Calibration, Calibrator, GestureInterpreter, Hand, classify, finger_scores
from computer_vision.tracker import GestureTracker, ProcessTracker, available

MCP = {0: (-.030, -.085), 1: (-.008, -.090), 2: (.013, -.085), 3: (.032, -.075)}
LEN = {0: (.042, .025, .020), 1: (.046, .028, .021), 2: (.042, .026, .021), 3: (.033, .020, .018)}
SHAPES = {OPEN: (1, 1, 1, 1), FIST: (0, 0, 0, 0), TWO: (1, 1, 0, 0)}


def world_hand(up, rot=(0, 0, 0)):
    p = np.zeros((21, 3))
    p[1], p[2], p[3], p[4] = (-.025, -.02, .008), (-.045, -.045, .012), (-.06, -.06, .012), (-.08, -.08, .012)
    for f in range(4):
        b = 5 + 4 * f
        p[b] = (*MCP[f], 0)
        pt = p[b].copy()
        for j, (ln, deg) in enumerate(zip(LEN[f], (4, 8, 10) if up[f] else (75, 170, 235)), 1):
            a = math.radians(deg)
            pt = pt + ln * np.array([0, -math.cos(a), math.sin(a)])
            p[b + j] = pt
    for ax, deg in enumerate(rot):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        r = [np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
             np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])][ax]
        p = p @ r.T
    return p


def hand(kind=OPEN, x=.5, y=.55, rot=(0, 0, 0)):
    w = world_hand(SHAPES[kind], rot)
    img = w * 2.2
    c = img[[0, 5, 9, 17], :2].mean(axis=0)
    img[:, 0] += x - c[0]
    img[:, 1] += y - c[1]
    return Hand(img, w, .95)


def feed(g, hands, n=8, t0=0.0, dt=1 / 30):
    for i in range(n):
        st = g.update(hands, t0 + i * dt)
    return st


@pytest.mark.parametrize("kind", SHAPES)
@pytest.mark.parametrize("rot", [(0, 0, 0), (0, 0, 35), (0, 0, -35), (25, 0, 0), (0, 40, 0), (0, 180, 0)])
def test_classification_survives_rotation(kind, rot):
    assert classify(finger_scores(world_hand(SHAPES[kind], rot))) == kind


def test_controls_from_gestures():
    g = GestureInterpreter()
    st = feed(g, [hand(OPEN)])
    assert st.throttle == 1 and st.brake == 0 and not st.nitro
    st = feed(g, [hand(FIST)], t0=1)
    assert st.throttle == 0 and st.brake == 1
    st = feed(g, [hand(TWO)], t0=2)
    assert st.nitro and st.brake == 0


def test_steering_left_right_and_dead_zone():
    g = GestureInterpreter()
    assert feed(g, [hand(x=.52)]).steer == 0
    assert feed(g, [hand(x=.28)], 20, 1).steer < -.5
    assert feed(GestureInterpreter(), [hand(x=.72)], 20, 3).steer > .5


def test_sensitivity_changes_response():
    lo, hi = GestureInterpreter(sensitivity=0.0), GestureInterpreter(sensitivity=1.0)
    a, b = feed(lo, [hand(x=.60)], 20).steer, feed(hi, [hand(x=.60)], 20).steer
    assert 0 < a < b


def test_tremor_is_filtered():
    rng = np.random.default_rng(0)
    g = GestureInterpreter()
    out = [g.update([hand(x=.62 + rng.normal(0, .012))], i / 30).steer for i in range(90)]
    raw = [g._shape((.62 + rng.normal(0, .012) - .5) / .24) for _ in range(90)]
    assert np.std(out[30:]) < np.std(raw) * .75


def test_single_wrong_frame_is_ignored():
    g = GestureInterpreter()
    feed(g, [hand(OPEN)], 10)
    st = g.update([hand(FIST)], .4)
    assert st.brake == 0 and st.throttle == 1


def test_jump_is_rejected():
    g = GestureInterpreter()
    feed(g, [hand(x=.5)], 10)
    assert abs(g.update([hand(x=.95)], .36).steer) < .05


def test_short_loss_tolerated_long_loss_reported():
    g = GestureInterpreter()
    feed(g, [hand(OPEN)], 10)
    assert g.update([], .45).present
    st = g.update([], 1.6)
    assert not st.present and st.lost_for > .9 and st.throttle == 0


def test_steering_wheel_with_two_hands():
    g = GestureInterpreter()
    st = feed(g, [hand(x=.35, y=.5), hand(x=.65, y=.5)], 12)
    assert st.wheel and abs(st.steer) < .05
    st = feed(g, [hand(x=.36, y=.40), hand(x=.64, y=.60)], 20, 1)
    assert st.steer > .4                         # main droite plus basse : on tourne à droite
    st = feed(g, [hand(x=.36, y=.60), hand(x=.64, y=.40)], 25, 3)
    assert st.steer < -.4


def test_one_hand_mode_ignores_second_hand():
    g = GestureInterpreter(hands="one")
    assert not feed(g, [hand(x=.35), hand(x=.65)], 12).wheel


def test_calibration_flow_and_use():
    g, cal, t = GestureInterpreter(), Calibrator(), 0.0
    for target, x in (("center", .42), ("left", .22), ("right", .70)):
        n = 0
        while not cal.done and cal.current == target and n < 400:
            cal.update(1 / 30, g.update([hand(x=x)], t))
            t += 1 / 30
            n += 1
    assert cal.done
    c = cal.result()
    assert c.center == pytest.approx(.42, abs=.02) and c.left == pytest.approx(.22, abs=.03) and c.right == pytest.approx(.70, abs=.03)
    assert feed(GestureInterpreter(c), [hand(x=.42)], 15).steer == 0
    assert feed(GestureInterpreter(c), [hand(x=.70)], 25).steer > .7


def test_calibration_rejects_wrong_side():
    g, cal = GestureInterpreter(), Calibrator()
    for i in range(60):
        cal.update(1 / 30, g.update([hand(x=.5)], i / 30))
    assert cal.current == "left"
    for i in range(60, 160):
        cal.update(1 / 30, g.update([hand(x=.7)], i / 30))
    assert cal.current == "left"


def test_bad_calibration_falls_back():
    assert Calibration.from_dict({"center": .5, "left": .49, "right": .51}) == Calibration()
    assert Calibration.from_dict(None) == Calibration()


class FakeCam:
    def __init__(self, ok=True, dead=False):
        self.ok, self.dead, self.released = ok, dead, False

    def isOpened(self):
        return self.ok

    def read(self):
        time.sleep(.005)
        return (False, None) if self.dead else (True, np.zeros((480, 640, 3), np.uint8))

    def release(self):
        self.released = True


class FakeDetector:
    def detect(self, rgb, t):
        time.sleep(.03)
        return [hand(FIST, x=.7)]

    def close(self):
        pass


def wait(cond, sec=8):
    t = time.time()
    while time.time() - t < sec:
        if cond():
            return True
        time.sleep(.02)
    return False


def test_thread_does_not_block_game_loop():
    pytest.importorskip("cv2")
    cam = FakeCam()
    tr = GestureTracker(opener=lambda i: cam, detector_factory=FakeDetector)
    tr.start()
    assert wait(lambda: tr.status == "running" and tr.state.brake == 1)
    times = []
    for _ in range(200):
        a = time.perf_counter()
        tr.state
        tr.preview(-1)
        times.append(time.perf_counter() - a)
        time.sleep(.001)
    assert np.percentile(times, 95) < .008               # l'inférence simulée dure 30 ms
    assert len(tr.preview(-1)[1]) == 320 * 240 * 4
    tr.stop()
    assert cam.released and tr.status == "off"


def test_no_camera_is_reported():
    pytest.importorskip("cv2")
    tr = GestureTracker(opener=lambda i: FakeCam(ok=False), detector_factory=FakeDetector)
    tr.start()
    assert wait(lambda: tr.status == "error") and "webcam" in tr.error.lower()
    tr.stop()


def test_unplugged_camera_is_reported():
    pytest.importorskip("cv2")
    tr = GestureTracker(opener=lambda i: FakeCam(dead=True), detector_factory=FakeDetector)
    tr.start()
    assert wait(lambda: tr.status == "error", 10)
    tr.stop()


def test_no_image_is_ever_saved_or_sent():
    src = "".join(p.read_text(encoding="utf-8") for p in (Path(__file__).parent.parent / "computer_vision").glob("*.py"))
    assert not [w for w in ("imwrite", "VideoWriter", "requests", "socket", "urllib", "http", ".save(") if w in src]


def test_real_mediapipe_model_loads():
    ok, why = available()
    if not ok:
        pytest.skip(why)
    from computer_vision.tracker import HandDetector
    d = HandDetector()
    assert d.detect(np.zeros((480, 640, 3), np.uint8), 0.0) == []
    assert d.detect(np.full((480, 640, 3), 127, np.uint8), .05) == []
    d.close()


def fake_worker(conn, shm_name, camera, config):
    from computer_vision.tracker import _worker
    _worker(conn, shm_name, camera, config, opener=lambda i: FakeCam(), factory=FakeDetector)


def crash_worker(conn, shm_name, camera, config):
    raise SystemExit(3)


def test_process_tracker_end_to_end():
    pytest.importorskip("cv2")
    tr = ProcessTracker(target=fake_worker)
    tr.start()
    assert wait(lambda: tr.state.brake == 1 and tr.status == "running", 25)
    times = []
    for _ in range(100):
        a = time.perf_counter()
        tr.state
        tr.preview(-1)
        times.append(time.perf_counter() - a)
        time.sleep(.005)
    assert np.percentile(times, 95) < .005
    assert len(tr.preview(-1)[1]) == 320 * 240 * 4
    tr.configure(calibration=Calibration(.6, .3, .9))
    assert wait(lambda: 0 <= tr.state.steer < .3, 5)
    tr.stop()
    assert tr.status == "off" and not tr.state.present


def test_process_crash_is_reported():
    tr = ProcessTracker(target=crash_worker)
    tr.start()
    assert wait(lambda: (tr.poll() or tr.status) == "error", 25)
    tr.stop()