"""Sauvegarde SQLite, réglages, progression, succès."""
from config.modes import BY_ID as MODES
from config.settings import ACTIONS, PRESETS, Settings
from config.vehicles import VEHICLES
from core.progression import ACHIEVEMENTS, check_achievements, finish_run, level_from_xp, rank, xp_for
from database.store import Store
from entities.world import World


def played(distance=6000, score=30000, coins=120):
    w = World(VEHICLES[0], MODES["endless"], seed=1)
    w.stats.distance, w.stats.score, w.stats.coins, w.stats.time = distance, score, coins, 90
    return w


def test_persistence_across_sessions(tmp_path):
    path = tmp_path / "a.db"
    s = Store(path)
    s.add("coins", 5000)
    assert s.buy("shadow_x", 800)
    s.set_custom("shadow_x", {"paint": "#FF5A1F", "rim": 2})
    st = Settings(s)
    st["quality"], st["music"], st["vehicle"] = "high", .2, "shadow_x"
    st.bind("nitro", 0, "left shift")
    st.save()
    finish_run(s, played())
    s.close()
    s = Store(path)
    st = Settings(s)
    assert s.unlocked() == {"neon_gt", "shadow_x"} and s.custom("shadow_x")["rim"] == 2
    assert (st["quality"], st["music"], st["vehicle"]) == ("high", .2, "shadow_x")
    assert st["keys"]["nitro"][0] == "left shift"
    assert s.best("endless") == 30000 and s.totals()["games"] == 1 and s.totals()["distance"] == 6000
    s.close()


def test_buy_is_atomic(store):
    store.add("coins", 500)
    assert not store.buy("shadow_x", 800) and store.coins == 500 and "shadow_x" not in store.unlocked()
    store.add("coins", 300)
    assert store.buy("shadow_x", 800) and store.coins == 0
    assert not store.buy("shadow_x", 800)


def test_custom_does_not_unlock(store):
    store.set_custom("apex_one", {"rim": 1})
    assert "apex_one" not in store.unlocked()


def test_corrupted_database_is_set_aside(tmp_path):
    path = tmp_path / "b.db"
    path.write_bytes(b"ceci n'est pas une base" * 200)
    s = Store(path)
    assert s.recovered and s.coins == 0
    assert list(tmp_path.glob("b.corrompue-*.db"))
    s.add("coins", 3)
    s.close()


def test_invalid_settings_are_ignored(store):
    store.save_settings({"quality": "ultra", "music": "fort", "resolution": [1], "keys": {"left": []}, "inconnu": 3})
    with store.db:
        store.db.execute("INSERT OR REPLACE INTO settings VALUES('sfx','{cassé')")
    s = Settings(store)
    assert s["quality"] == "medium" and s["music"] == .65 and s["resolution"] == [1600, 900] and s["sfx"] == .85
    assert set(s["keys"]) == set(ACTIONS)


def test_presets_and_conflicts(store):
    s = Settings(store)
    assert s["keys"]["left"] == ["left", "q"] and s["keys"]["up"] == ["up", "z"]
    s.apply_preset("QWERTY")
    assert s["keys"]["left"] == ["left", "a"] and PRESETS["QWERTY"]["up"] == ["up", "w"]
    s.bind("nitro", 0, "d")
    assert "d" not in s["keys"]["right"] and s["preset"] == "PERSO"
    assert s.unbound() == []


def test_run_rewards_and_record(store):
    r = finish_run(store, played())
    assert r.record and r.best == 0 and r.xp > 0 and r.coins == 120
    assert {a.id for a in r.achievements} >= {"first_run", "km5", "score25", "coins100"}
    assert store.coins == 120 + r.bonus_coins + r.level_bonus
    r2 = finish_run(store, played(score=100))
    assert not r2.record and r2.best == 30000
    assert not {a.id for a in r2.achievements} & {a.id for a in r.achievements}


def test_levels():
    assert level_from_xp(0)[0] == 1 and level_from_xp(xp_for(1))[0] == 2
    lv = [level_from_xp(x)[0] for x in range(0, 60000, 500)]
    assert lv == sorted(lv) and rank(1) == "ROOKIE" and rank(99) == "APEX LEGEND"


def test_achievements_unique_and_once(store):
    assert len({a.id for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS) >= 20
    store.add_run("endless", "neon_city", "neon_gt", 1, 1, 1, 1, 0, 0, 0, 1)
    assert [a.id for a in check_achievements(store)] == ["first_run"]
    assert check_achievements(store) == []


def test_leaderboard_order(store):
    for s in (5, 90, 40):
        store.add_run("night", "neon_city", "neon_gt", s, 1, 1, 1, 0, 0, 0, 1)
    assert [r.score for r in store.top("night")] == [90, 40, 5] and store.top("survival") == []


def test_schema(store):
    names = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"profile", "settings", "vehicles", "runs", "achievements"} <= names
