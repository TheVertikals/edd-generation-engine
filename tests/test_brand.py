import pytest

from engine.brand import capture_brand
from engine.inputpack import InputPack


def _pack(tmp_path, extra=""):
    (tmp_path / "inputpack.yaml").write_text("beacon_id: 01B\n" + extra, encoding="utf-8")
    return InputPack(str(tmp_path))


def test_pack_colors_are_authoritative(tmp_path):
    b = capture_brand(_pack(tmp_path, 'brand_colors: "#0A2540,#0073CF"\n'))
    assert "#0073cf" in [c["hex"] for c in b["colors"]] and b["colors"][0]["source"] == "pack"


def test_url_extraction_when_no_pack_colors(tmp_path):
    html = '<meta name="theme-color" content="#0073CF"><style>:root{--brand:#0A2540}</style>'
    b = capture_brand(_pack(tmp_path, "brand_url: https://x.example\n"), fetch=lambda u: html)
    assert {"#0073cf", "#0a2540"} <= {c["hex"] for c in b["colors"]}
    assert all(c["source"] == "https://x.example" for c in b["colors"])


def test_fetch_rejects_non_http_scheme(tmp_path):
    with pytest.raises(ValueError):
        capture_brand(_pack(tmp_path, "brand_url: file:///etc/passwd\n"))


def test_no_brand_source_returns_empty(tmp_path):
    b = capture_brand(_pack(tmp_path))
    assert b["colors"] == [] and b["fonts"] == []
