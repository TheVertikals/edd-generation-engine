from engine.checkpoint import Checkpoint


def test_mark_and_completed(tmp_path):
    c = Checkpoint(str(tmp_path))
    assert c.completed() == []
    c.mark("intake")
    c.mark("research")
    assert c.completed() == ["intake", "research"]


def test_mark_is_idempotent(tmp_path):
    c = Checkpoint(str(tmp_path))
    c.mark("intake")
    c.mark("intake")
    assert c.completed() == ["intake"]


def test_reset_clears(tmp_path):
    c = Checkpoint(str(tmp_path))
    c.mark("intake")
    c.reset()
    assert c.completed() == []


def test_completed_survives_reload(tmp_path):
    Checkpoint(str(tmp_path)).mark("intake")
    assert Checkpoint(str(tmp_path)).completed() == ["intake"]
