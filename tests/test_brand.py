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


# append to tests/test_brand.py
import io, pytest
from engine import brand

@pytest.mark.parametrize("ip", [
    "10.0.0.5", "127.0.0.1", "100.95.134.80", "169.254.169.254", "0.0.0.0",
    "::1", "fc00::1", "fe80::1",
    "::ffff:100.95.134.80",       # N1: mapped CGNAT (ark) — must block on 3.9 AND 3.12
    "::ffff:10.0.0.5", "::ffff:1.1.1.1",    # R3: ALL mapped forms blocked, incl. mapped-PUBLIC
    "2002:0a00:0001::", "64:ff9b::a00:1",   # 6to4 + NAT64 (embedded private)
    "fec0::1", "fecf:ffff:ffff:ffff::1",    # deprecated IPv6 site-local fec0::/10 (is_global lies True)
])
def test_reject_bad_addresses(ip):
    with pytest.raises(ValueError):
        brand._reject_if_bad(ip)

def test_public_address_ok():
    brand._reject_if_bad("1.1.1.1")           # no raise
    brand._reject_if_bad("2606:4700:4700::1111")   # a real public IPv6 must still pass

def test_resolve_pinned_validates_all_and_pins(monkeypatch):
    monkeypatch.setattr(brand.socket, "getaddrinfo",
        lambda h, *a, **k: [(2, 1, 6, "", ("1.1.1.1", 0)), (2, 1, 6, "", ("10.0.0.9", 0))])
    with pytest.raises(ValueError):           # a mixed public+private host is refused
        brand._resolve_pinned("evil.example")

def test_fetch_pins_and_revalidates_redirect(monkeypatch):
    calls = {"open": []}
    class _Sock:
        def __init__(self, body): self._b = io.BytesIO(body)
        def makefile(self, *a, **k): return self._b
        def sendall(self, *a): pass
        def close(self): pass
        def settimeout(self, *a): pass
    def fake_open(family, ip, port, scheme, host, timeout=15):
        calls["open"].append(ip)
        return _Sock(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello")
    monkeypatch.setattr(brand.socket, "getaddrinfo",
                        lambda h, *a, **k: [(2, 1, 6, "", ("1.1.1.1", 0))])
    body = brand._default_fetch("https://brand.example/", _open=fake_open)
    assert body == "hello" and calls["open"] == ["1.1.1.1"]   # connected to the VALIDATED ip (pin)
