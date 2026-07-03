import pytest

from engine.bundle import Bundle


def test_write_then_read_roundtrips(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("notes/a.md", "hello")
    assert b.read("notes/a.md") == "hello"
    assert b.exists("notes/a.md") is True


def test_read_missing_returns_none(tmp_path):
    assert Bundle(str(tmp_path)).read("nope.md") is None


def test_write_is_atomic_no_tmp_left(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("x.md", "y")
    leftovers = [p.name for p in tmp_path.rglob("*.tmp")]
    assert leftovers == []


def test_unicode_roundtrips(tmp_path):
    b = Bundle(str(tmp_path))
    text = "café — déjà vu — 日本語"
    b.write("u.md", text)
    assert b.read("u.md") == text


@pytest.mark.parametrize("bad", ["../evil.md", "a/../../evil.md", "/etc/passwd"])
def test_path_traversal_is_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        Bundle(str(tmp_path)).write(bad, "x")
