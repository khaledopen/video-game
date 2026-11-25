"""Sauvegarde SQLite : profil, réglages, garage, parties et succès."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from config.paths import data_dir

log = logging.getLogger(__name__)
VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS profile(key TEXT PRIMARY KEY, value REAL NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vehicles(id TEXT PRIMARY KEY, unlocked INTEGER NOT NULL DEFAULT 0, custom TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT, played_at REAL NOT NULL, mode TEXT NOT NULL, environment TEXT NOT NULL,
    vehicle TEXT NOT NULL, score INTEGER NOT NULL, distance REAL NOT NULL, duration REAL NOT NULL,
    top_speed REAL NOT NULL, coins INTEGER NOT NULL, dodged INTEGER NOT NULL, near_misses INTEGER NOT NULL, level INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS runs_score ON runs(mode, score DESC);
CREATE TABLE IF NOT EXISTS achievements(id TEXT PRIMARY KEY, unlocked_at REAL NOT NULL);
"""


@dataclass(frozen=True)
class RunRow:
    id: int
    played_at: float
    mode: str
    environment: str
    vehicle: str
    score: int
    distance: float
    duration: float
    top_speed: float
    coins: int
    dodged: int
    near_misses: int
    level: int


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else data_dir() / "neon_drive.db"
        self.recovered = False
        try:
            self._open()
        except sqlite3.DatabaseError as exc:
            # base illisible : on la met de côté plutôt que de l'effacer
            log.error("Sauvegarde illisible (%s) : mise de côté.", exc)
            try:
                self.db.close()
            except Exception:
                pass
            backup = self.path.with_name(f"{self.path.stem}.corrompue-{int(time.time())}.db")
            self.path.replace(backup)
            self.recovered = True
            self._open()

    def _open(self):
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("integrity_check")
        self.db.execute(f"PRAGMA user_version={VERSION}")
        self.db.commit()

    def close(self):
        try:
            self.db.commit()
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error as exc:
            log.warning("Fermeture de la sauvegarde : %s", exc)
        self.db.close()

    # -- profil ---------------------------------------------------------------------
    def get(self, key: str, default: float = 0.0) -> float:
        r = self.db.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def set(self, key: str, value: float):
        with self.db:
            self.db.execute("INSERT INTO profile VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, float(value)))

    def add(self, key: str, delta: float) -> float:
        with self.db:
            self.db.execute("INSERT INTO profile VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=value+excluded.value", (key, float(delta)))
        return self.get(key)

    @property
    def coins(self) -> int:
        return int(self.get("coins"))

    # -- réglages -----------------------------------------------------------------------
    def load_settings(self) -> dict:
        out = {}
        for k, v in self.db.execute("SELECT key, value FROM settings"):
            try:
                out[k] = json.loads(v)
            except ValueError:
                log.warning("Réglage illisible ignoré : %s", k)
        return out

    def save_settings(self, values: dict):
        with self.db:
            self.db.executemany("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                [(k, json.dumps(v)) for k, v in values.items()])

    # -- garage -----------------------------------------------------------------------------
    def unlocked(self) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT id FROM vehicles WHERE unlocked=1")} | {"neon_gt"}

    def buy(self, vid: str, price: int) -> bool:
        """Achat atomique : débite et débloque, ou ne fait rien."""
        if vid in self.unlocked():
            return False
        with self.db:
            cur = self.db.execute("UPDATE profile SET value=value-? WHERE key='coins' AND value>=?", (price, price))
            if cur.rowcount != 1 and price > 0:
                return False
            self.db.execute("INSERT INTO vehicles(id, unlocked) VALUES(?,1) ON CONFLICT(id) DO UPDATE SET unlocked=1", (vid,))
        return True

    def custom(self, vid: str) -> dict:
        r = self.db.execute("SELECT custom FROM vehicles WHERE id=?", (vid,)).fetchone()
        try:
            return json.loads(r[0]) if r else {}
        except ValueError:
            return {}

    def set_custom(self, vid: str, custom: dict):
        with self.db:
            self.db.execute("INSERT INTO vehicles(id, unlocked, custom) VALUES(?,0,?) ON CONFLICT(id) DO UPDATE SET custom=excluded.custom",
                            (vid, json.dumps(custom)))

    # -- parties -------------------------------------------------------------------------------
    def add_run(self, mode, environment, vehicle, score, distance, duration, top_speed, coins, dodged, near_misses, level) -> int:
        with self.db:
            cur = self.db.execute(
                "INSERT INTO runs(played_at, mode, environment, vehicle, score, distance, duration, top_speed, coins, dodged, near_misses, level)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), mode, environment, vehicle, int(score), distance, duration, top_speed, int(coins), int(dodged), int(near_misses), int(level)))
        return cur.lastrowid

    def best(self, mode: str | None = None) -> int:
        q, a = ("SELECT MAX(score) FROM runs WHERE mode=?", (mode,)) if mode else ("SELECT MAX(score) FROM runs", ())
        return int(self.db.execute(q, a).fetchone()[0] or 0)

    def top(self, mode: str | None = None, limit: int = 10) -> list[RunRow]:
        q = "SELECT * FROM runs" + (" WHERE mode=?" if mode else "") + " ORDER BY score DESC, id LIMIT ?"
        return [RunRow(*r) for r in self.db.execute(q, (mode, limit) if mode else (limit,))]

    def recent(self, limit: int = 20) -> list[RunRow]:
        return [RunRow(*r) for r in self.db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))]

    def totals(self) -> dict:
        r = self.db.execute("SELECT COUNT(*), TOTAL(distance), TOTAL(duration), MAX(top_speed), TOTAL(coins), TOTAL(dodged), TOTAL(near_misses),"
                            " MAX(score), MAX(distance), MAX(duration) FROM runs").fetchone()
        keys = ("games", "distance", "time", "top_speed", "coins", "dodged", "near_misses", "best", "best_distance", "best_time")
        return {k: (v or 0) for k, v in zip(keys, r)}

    def per_mode(self) -> dict[str, tuple]:
        return {r[0]: r[1:] for r in self.db.execute("SELECT mode, COUNT(*), MAX(score), TOTAL(distance) FROM runs GROUP BY mode")}

    # -- succès -------------------------------------------------------------------------------------
    def achievements(self) -> dict[str, float]:
        return dict(self.db.execute("SELECT id, unlocked_at FROM achievements"))

    def unlock_achievement(self, aid: str) -> bool:
        with self.db:
            return self.db.execute("INSERT OR IGNORE INTO achievements VALUES(?,?)", (aid, time.time())).rowcount == 1
