import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ["NEON_DRIVE_DATA"] = tempfile.mkdtemp(prefix="neon_test_")

import pytest  # noqa: E402

from config.modes import BY_ID as MODES  # noqa: E402
from config.vehicles import VEHICLES  # noqa: E402
from entities.world import World  # noqa: E402


@pytest.fixture
def world():
    """Monde vide : aucune apparition, pour tester une seule chose à la fois."""
    w = World(VEHICLES[0], MODES["endless"], seed=1)
    w.spawner.update = lambda *_: None
    return w


@pytest.fixture
def store(tmp_path):
    from database.store import Store
    s = Store(tmp_path / "t.db")
    yield s
    s.close()
