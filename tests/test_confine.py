# tests/test_confine.py
import os, pytest
from engine.confine import assert_within

def test_inside_ok(tmp_path):
    (tmp_path / "sub").mkdir()
    assert assert_within(str(tmp_path), str(tmp_path / "sub" / "x")).endswith("x")

def test_prefix_trap_and_escape(tmp_path):
    (tmp_path / "foo").mkdir(); (tmp_path / "foobar").mkdir()
    with pytest.raises(ValueError):
        assert_within(str(tmp_path / "foo"), str(tmp_path / "foobar" / "x"))

def test_symlink_escape(tmp_path):
    root = tmp_path / "root"; root.mkdir(); (tmp_path / "secret").mkdir()
    (root / "link").symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError):
        assert_within(str(root), str(root / "link"))

def test_rejects_relative_inputs(tmp_path):
    with pytest.raises(ValueError):
        assert_within("relative/root", str(tmp_path))
    with pytest.raises(ValueError):
        assert_within(str(tmp_path), "relative/path")

def test_case_insensitive_fs_no_false_positive(tmp_path):
    # on a case-insensitive FS a case-different-but-same path must NOT raise
    d = tmp_path / "Case"; d.mkdir()
    if os.path.exists(str(tmp_path / "CASE")):        # FS is case-insensitive
        assert assert_within(str(tmp_path / "Case"), str(tmp_path / "case" / "f")).endswith("f")
