import base64
import json

from engine.fonts import font_faces


def _stub_assets(tmp_path):
    d = tmp_path / "fonts"
    d.mkdir()
    (d / "geist-400.b64").write_text(base64.b64encode(b"FONTDATA").decode(), encoding="utf-8")
    (d / "MANIFEST.json").write_text(json.dumps(
        {"geist": {"family": "Geist", "weights": {"400": "geist-400.b64"}}}), encoding="utf-8")
    return str(d)


def test_font_faces_inlines_present_faces(tmp_path):
    css = font_faces(kit={"display": "geist"}, assets_dir=_stub_assets(tmp_path))
    assert "@font-face" in css and "font-family:'Geist'" in css
    assert "data:font/woff2;base64," in css


def test_missing_face_is_skipped_not_fatal(tmp_path):
    css = font_faces(kit={"display": "nope"}, assets_dir=_stub_assets(tmp_path))
    assert css.strip() == ""


def test_no_manifest_returns_empty(tmp_path):
    assert font_faces(assets_dir=str(tmp_path)) == ""
