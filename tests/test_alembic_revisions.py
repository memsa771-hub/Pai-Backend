from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


def test_revision_chain_includes_discovery_tracking():
    cfg = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev = script.get_revision("013_discovery_tracking")
    assert rev.down_revision == "012_goal_centric"
    assert script.get_heads() == ["013_discovery_tracking"]
