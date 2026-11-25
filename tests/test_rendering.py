"""Rendu hors écran : maillages, shaders, scènes complètes, fuites. Ignoré sans OpenGL 3.3."""
import gc

import numpy as np
import pygame
import pytest

from computer_vision.gestures import Calibration, GestureState
from config.environments import PLAYABLE
from config.modes import MODES
from config.vehicles import VEHICLES
from engine.mesh import STRIDE
from engine.models import props, traffic
from engine.models.cars import CarModel, wheel
from entities.traffic import KINDS


@pytest.mark.parametrize("spec", VEHICLES, ids=lambda s: s.id)
def test_car_meshes(spec):
    m = CarModel(spec.shape)
    assert m.mesh.shape[1] == STRIDE and 2500 < m.triangles < 9000 and np.isfinite(m.mesh).all()
    assert np.allclose(np.linalg.norm(m.mesh[:, 3:6], axis=1), 1, atol=.02)
    assert abs(m.mesh[:, 0].max() + m.mesh[:, 0].min()) < .05          # symétrie
    assert len(m.wheels) == 4 and m.mesh[:, 1].min() > 0


def test_car_meshes_are_distinct():
    assert len({CarModel(v.shape).mesh.tobytes()[:20000] for v in VEHICLES}) == 8


@pytest.mark.parametrize("name", list(props.BUILDERS))
def test_props(name):
    d = props.BUILDERS[name]()
    assert len(d) >= 12 and np.isfinite(d).all()


@pytest.mark.parametrize("name", list(traffic.MODELS))
def test_traffic_models(name):
    m = traffic.MODELS[name]()
    L, W, _ = KINDS[name][:3]
    assert abs(m.length - L) < .05 and abs(m.width - W) < .05 and len(m.wheels) >= 4


def test_wheels():
    assert len({wheel(i).tobytes() for i in range(4)}) == 4


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    try:
        import moderngl
        moderngl.create_standalone_context().release()
    except Exception as exc:
        pytest.skip(f"OpenGL indisponible : {exc}")
    from core.app import App
    a = App(headless=True, size=(640, 360), audio=False, start="menu", db_path=tmp_path_factory.mktemp("db") / "r.db")
    yield a
    a.shutdown()


def frames(app, n, dt=1 / 60):
    """Avance n images ; seule la dernière est réellement dessinée, pour aller vite."""
    for _ in range(n - 1):
        app.time += dt
        app.scenes.update(dt)
    app.frame(dt, [])


def image(app):
    return np.asarray(app.screenshot(), float)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def click(app, w):
    k = app.canvas.k
    pos = (int((w.x + w.w / 2) * k), int((w.y + w.h / 2) * k))
    return [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)), pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)]


def game(app, mode="endless", env="auto", seed=2, start=True):
    app.settings["environment"] = env
    app.scenes.set("game", mode_id=mode, seed=seed)
    app.settings["environment"] = "auto"
    g = app.scenes.scene
    if start:
        g.countdown = 0
    return g


@pytest.mark.parametrize("env", PLAYABLE, ids=lambda e: e.id)
def test_each_environment_renders(app, env):
    game(app, env=env.id, start=False)
    frames(app, 90)
    im = image(app)
    assert im.std() > 12 and 8 < im.mean() < 235
    assert app.ctx.error == "GL_NO_ERROR"


def test_environments_look_different(app):
    means = []
    for e in PLAYABLE:
        game(app, env=e.id)
        frames(app, 60)
        means.append(image(app).mean(axis=(0, 1)))
    assert min(np.abs(a - b).sum() for i, a in enumerate(means) for b in means[i + 1:]) > 6


def test_night_mode_is_darker(app):
    lum = []
    for m in ("endless", "night"):
        game(app, m, "mountain_road")
        frames(app, 60)
        lum.append(image(app)[100:200].mean())
    assert lum[1] < lum[0] * .5


@pytest.mark.parametrize("q", ("low", "medium", "high"))
def test_quality_profiles(app, q):
    app.settings["quality"] = q
    app.apply_video()
    game(app)
    frames(app, 30)
    assert image(app).std() > 12 and ("reflect" in app.renderer.targets) == (q != "low")
    app.settings["quality"] = "medium"
    app.apply_video()


def test_menu_buttons_reach_every_screen(app):
    app.settings["mode"] = "endless"
    for i, name in enumerate(["game", "garage", "modes", "leaderboard", "stats", "settings"]):
        app.scenes.set("menu")
        frames(app, 80)
        app.frame(1 / 60, click(app, app.scenes.scene.group.widgets[i]))
        frames(app, 70)
        assert app.scenes.name == name
        if name != "game":
            app.frame(1 / 60, [key(pygame.K_ESCAPE)])
            frames(app, 70)
            assert app.scenes.name == "menu"


def test_quit_asks_then_quits(app):
    app.scenes.set("menu")
    frames(app, 60)
    s = app.scenes.scene
    app.frame(1 / 60, click(app, s.group.widgets[6]))
    frames(app, 10)
    assert s.asking and app.running
    app.frame(1 / 60, click(app, s.quit_group.widgets[0]))
    assert not s.asking and app.running
    app.frame(1 / 60, [key(pygame.K_ESCAPE)])
    app.frame(1 / 60, click(app, s.quit_group.widgets[1]))
    assert not app.running
    app.running = True


def test_keyboard_navigation(app):
    app.scenes.set("menu")
    frames(app, 60)
    for _ in range(2):
        app.frame(1 / 60, [key(pygame.K_DOWN)])
    assert app.scenes.scene.group.focus is app.scenes.scene.group.widgets[1]
    app.frame(1 / 60, [key(pygame.K_RETURN)])
    frames(app, 70)
    assert app.scenes.name == "garage"


def test_mode_cards_launch_each_mode(app):
    for i, m in enumerate(MODES):
        if m.gesture:
            continue
        app.scenes.set("modes")
        frames(app, 70)
        s = app.scenes.scene
        app.frame(1 / 60, click(app, s.cards[i]))
        app.frame(1 / 60, click(app, s.go_btn))
        frames(app, 70)
        assert app.scenes.name == "game" and app.scenes.scene.mode.id == m.id
    app.settings["mode"] = "endless"


def test_garage_buy_select_customise(app):
    st = app.store
    st.set("coins", 1000)
    app.scenes.set("garage")
    frames(app, 60)
    s = app.scenes.scene
    app.frame(1 / 60, click(app, s.thumbs[1]))
    frames(app, 40)
    assert s.spec.id == "shadow_x" and not s.swatches
    app.frame(1 / 60, click(app, s.action))
    frames(app, 20)
    assert "shadow_x" in st.unlocked() and 200 <= st.coins < 1000 and app.settings["vehicle"] == "shadow_x"
    for tab in range(5):
        s.set_tab(tab)
        frames(app, 30)
        before = dict(s.custom)
        app.frame(1 / 60, click(app, s.swatches[2]))
        assert s.custom != before
    assert st.custom("shadow_x") == s.custom
    app.frame(1 / 60, click(app, s.thumbs[7]))
    frames(app, 30)
    app.frame(1 / 60, click(app, s.action))
    assert "apex_one" not in st.unlocked()
    app.settings["vehicle"] = "neon_gt"


def test_settings_widgets(app):
    app.scenes.set("settings", tab=1)
    frames(app, 40)
    s = app.scenes.scene
    app.frame(1 / 60, click(app, s.tab_btns[2]))
    frames(app, 30)
    row = s.rows[6]                                     # touche Nitro
    k = app.canvas.k
    pos = (int((row.x + row.w - 250) * k), int((row.y + row.h / 2) * k))
    app.frame(1 / 60, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1), pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)])
    assert s.binding is not None
    app.frame(1 / 60, [key(pygame.K_n)])
    assert app.settings["keys"]["nitro"][0] == "n" and pygame.K_n in app.keyboard.codes["nitro"]
    app.settings.apply_preset("AZERTY")
    app.keyboard.reload()
    s.set_tab(0)
    frames(app, 20)
    app.frame(1 / 60, click(app, s.rows[2]))
    frames(app, 5)
    assert app.renderer.quality.name == app.settings["quality"] == "high"
    app.settings["quality"] = "medium"
    app.apply_video()


def test_pause_resume_and_game_over_flow(app):
    g = game(app, seed=3)
    frames(app, 40)
    app.frame(1 / 60, [key(pygame.K_ESCAPE)])
    s0 = g.world.player.s
    frames(app, 30)
    assert g.paused and g.world.player.s == s0
    app.frame(1 / 60, [key(pygame.K_ESCAPE)])
    frames(app, 130)
    assert not g.paused and g.world.player.s > s0
    g.world.player.hp, g.world.player.invuln = 1, 0
    g.world._hurt(99, 0, g.world.player.s, "barrier", 1.0)
    games = app.store.totals()["games"]
    frames(app, 300)
    assert app.scenes.name == "gameover" and app.store.totals()["games"] == games + 1
    frames(app, 200)
    app.frame(1 / 60, click(app, app.scenes.scene.group.widgets[2]))
    frames(app, 70)
    assert app.scenes.name == "menu"


class FakeTracker:
    status, error, fps = "running", "", 30.0
    interp = type("I", (), {"cal": Calibration()})()
    state = GestureState(present=True, lost_for=0.0, steer=.5, throttle=1.0)

    def preview(self, seq):
        return None


def test_gesture_loss_pauses_game(app):
    ctl = app.gesture
    ctl.start, ctl.stop, ctl.tracker = (lambda: None), (lambda wait=False: None), FakeTracker()
    try:
        g = game(app, "gesture", seed=3)
        g.world.player.x = 0
        frames(app, 30)
        assert g.world.player.vx > 1 and not g.paused
        ctl.tracker.state = GestureState(present=False, lost_for=2.0)
        frames(app, 80)
        assert g.paused and "MAINS" in g.pause_reason
        ctl.tracker.state = GestureState(present=True, lost_for=0.0)
        frames(app, 10)
        assert not g.paused                                # reprise automatique
        ctl.tracker.state = GestureState(present=False, lost_for=2.0)
        frames(app, 320)
        assert g.paused
        g.to_keyboard()
        frames(app, 130)
        assert not g.paused and not g.use_gesture
    finally:
        del ctl.start, ctl.stop
        ctl.tracker = None


@pytest.mark.parametrize("size", ((1024, 768), (1280, 800), (1720, 720), (640, 360)))
def test_layouts_fit_every_aspect(app, size):
    app._resized(size)
    app.gesture.start = lambda: None
    try:
        for name in ("menu", "modes", "garage", "leaderboard", "stats", "settings", "calibration"):
            app.scenes.set(name)
            for _ in range(70):
                app.scenes.update(1 / 60)
            for w in app.scenes.scene.group.active():
                assert -10 <= w.x and w.x + w.w <= app.canvas.W + 10 and w.y + w.h <= app.canvas.H + 10, (name, size, getattr(w, "label", w))
    finally:
        del app.gesture.start
        app._resized((640, 360))


def test_no_resource_leak(app):
    game(app, seed=3)
    frames(app, 60)
    n0 = len(app.canvas.images)
    for i in range(6):
        game(app, seed=i)
        frames(app, 40)
    app.scenes.set("menu")
    frames(app, 5)
    gc.collect()
    from entities.world import World
    assert len(app.canvas.images) == n0 and len(app.renderer.meshes) <= 70
    assert sum(isinstance(o, World) for o in gc.get_objects()) <= 3      # les parties terminées sont libérées


def test_mouse_jitter_does_not_steal_keyboard_focus(app):
    app.scenes.set("menu")
    frames(app, 60)
    g = app.scenes.scene.group
    for _ in range(3):
        app.frame(1 / 60, [key(pygame.K_DOWN)])
    focus = g.focus
    jitter = [pygame.event.Event(pygame.MOUSEMOTION, pos=(600 + i % 2, 20), rel=(1, 0), buttons=(0, 0, 0)) for i in range(60)]
    app.frame(1 / 60, jitter)
    assert g.focus is focus                             # zone vide : la sélection reste
    w = g.widgets[6]
    app.frame(1 / 60, [pygame.event.Event(pygame.MOUSEMOTION, pos=(int((w.x + 80) * app.canvas.k), int((w.y + 20) * app.canvas.k)), rel=(200, 90), buttons=(0, 0, 0))])
    assert g.focus is w                                 # vrai mouvement : la souris reprend la main