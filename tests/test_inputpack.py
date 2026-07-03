from engine.inputpack import InputPack


def _stub(tmp_path):
    (tmp_path / "inputpack.yaml").write_text(
        "beacon_id: 01ABC\npack_version: 1\n", encoding="utf-8"
    )
    (tmp_path / "transcript.txt").write_text("hello", encoding="utf-8")
    return InputPack(str(tmp_path))


def test_manifest_parses_simple_yaml(tmp_path):
    m = _stub(tmp_path).manifest()
    assert m["beacon_id"] == "01ABC"
    assert m["pack_version"] == "1"


def test_read_returns_file_or_none(tmp_path):
    p = _stub(tmp_path)
    assert p.read("transcript.txt") == "hello"
    assert p.read("missing.txt") is None
