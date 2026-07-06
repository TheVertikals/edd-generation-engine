import io

import pytest
from pytest_bdd import given, scenarios, then, when

from engine import brand
from engine.brand import capture_brand
from engine.inputpack import InputPack

scenarios("../features/08c-brand.feature")


@pytest.fixture
def ctx():
    return {}


def _pack(tmp_path, extra=""):
    (tmp_path / "inputpack.yaml").write_text("beacon_id: 01C\n" + extra, encoding="utf-8")
    return InputPack(str(tmp_path))


class _Sock:
    def __init__(self, body):
        self._b = io.BytesIO(body)

    def makefile(self, *a, **k):
        return self._b

    def sendall(self, *a):
        pass

    def close(self):
        pass

    def settimeout(self, *a):
        pass


# ----- Scenario 1 -----
@given("an input pack that declares brand_colors")
def _declared(ctx, tmp_path):
    ctx["pack"] = _pack(tmp_path, 'brand_colors: "#0A2540,#0073CF"\n')
    ctx["fetched"] = []


@when("brand capture runs")
def _capture(ctx):
    ctx["brand"] = capture_brand(ctx["pack"], fetch=lambda u: (ctx["fetched"].append(u) or ""))


@then("the declared colors are used with source pack and no URL is fetched")
def _authoritative(ctx):
    cols = ctx["brand"]["colors"]
    assert "#0073cf" in [c["hex"] for c in cols] and cols[0]["source"] == "pack"
    assert ctx["fetched"] == []


# ----- Scenario 2 -----
@given("a pack with a brand_url and no declared colors")
def _urlpack(ctx, tmp_path):
    ctx["tmp"] = tmp_path


@when("brand capture fetches it")
def _noopc(ctx):
    pass


@then("a non-http scheme such as file is refused")
def _scheme(ctx):
    with pytest.raises(ValueError):
        capture_brand(_pack(ctx["tmp"], "brand_url: file:///etc/passwd\n"))


@then("the fetch connects to the validated pinned IP")
def _pins(ctx, monkeypatch):
    calls = {"open": []}

    def fake_open(family, ip, port, scheme, host, timeout=15):
        calls["open"].append(ip)
        return _Sock(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello")

    monkeypatch.setattr(brand.socket, "getaddrinfo",
                        lambda h, *a, **k: [(2, 1, 6, "", ("1.1.1.1", 0))])
    body = brand._default_fetch("https://brand.example/", _open=fake_open)
    assert body == "hello" and calls["open"] == ["1.1.1.1"]


# ----- Scenario 3 -----
@given("a brand_url that resolves to a private, loopback, CGNAT, or IPv4-embedded IPv6 address")
def _bad(ctx):
    ctx["bad"] = ["10.0.0.5", "127.0.0.1", "100.95.134.80", "::ffff:10.0.0.5", "fec0::1"]


@when("the address is validated")
def _noopc3(ctx):
    pass


@then("it is refused, and a host resolving to a mix of public and private addresses is refused whole")
def _refused(ctx, monkeypatch):
    for ip in ctx["bad"]:
        with pytest.raises(ValueError):
            brand._reject_if_bad(ip)
    monkeypatch.setattr(brand.socket, "getaddrinfo",
                        lambda h, *a, **k: [(2, 1, 6, "", ("1.1.1.1", 0)),
                                            (2, 1, 6, "", ("10.0.0.9", 0))])
    with pytest.raises(ValueError):
        brand._resolve_pinned("evil.example")


# ----- Scenario 4 -----
@given("a brand_url whose fetch follows a redirect")
def _redir(ctx):
    ctx["resolved"] = []


@when("the fetch follows the Location header")
def _noopc4(ctx):
    pass


@then("each hop is re-resolved and re-pinned, and too many hops is refused")
def _hops(ctx, monkeypatch):
    monkeypatch.setattr(
        brand.socket, "getaddrinfo",
        lambda h, *a, **k: (ctx["resolved"].append(h) or [(2, 1, 6, "", ("1.1.1.1", 0))]))

    def redir_open(family, ip, port, scheme, host, timeout=15):
        return _Sock(b"HTTP/1.1 302 Found\r\nLocation: https://next.example/\r\n"
                     b"Content-Length: 0\r\n\r\n")

    with pytest.raises(ValueError):  # unbounded redirects -> refused after the hop budget
        brand._default_fetch("https://brand.example/", _open=redir_open)
    assert len(ctx["resolved"]) >= 2  # re-resolved (re-validated) at each hop
