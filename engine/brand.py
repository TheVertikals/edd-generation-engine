import http.client
import ipaddress
import re
import socket
import ssl
import urllib.parse
from typing import Callable, List, Optional

from engine.inputpack import InputPack

_HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_FONT = re.compile(r"font-family\s*:\s*([^;\}\"']+)", re.IGNORECASE)
_OS_FONTS = {"geist", "geist mono", "hanken grotesk", "ibm plex sans", "ibm plex mono",
             "bricolage grotesque", "inter", "eb garamond", "fraunces", "space grotesk",
             "source sans 3", "work sans", "public sans"}
_ROLES = ("primary", "secondary", "neutral", "accent", "support")


_BAD_V4 = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
    "172.16.0.0/12", "192.0.0.0/24", "192.168.0.0/16", "198.18.0.0/15", "224.0.0.0/4",
    "240.0.0.0/4", "255.255.255.255/32")]
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _embedded_v4(addr):
    if addr.version != 6:
        return None
    if addr.ipv4_mapped:
        return addr.ipv4_mapped
    if addr.sixtofour:
        return addr.sixtofour
    if addr in _NAT64:
        return ipaddress.ip_address(int(addr) & 0xFFFFFFFF)
    return None


def _reject_if_bad(ip_str: str) -> None:
    addr = ipaddress.ip_address(ip_str)
    if addr.version == 6:
        if _embedded_v4(addr) is not None:      # R3: mapped/6to4/NAT64 are never legit in a brand URL
            raise ValueError("brand_url uses an IPv4-embedded IPv6 form (%s) — refused" % ip_str)
        if (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
                or addr.is_multicast or addr.is_unspecified):
            raise ValueError("brand_url resolves to a non-public address (%s) — refused" % ip_str)
    else:
        if any(addr in net for net in _BAD_V4):
            raise ValueError("brand_url resolves to a non-public address (%s) — refused" % ip_str)


def _resolve_pinned(host: str):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("brand_url host does not resolve: %r (%s)" % (host, e))
    if not infos:
        raise ValueError("brand_url host did not resolve: %r" % host)
    for info in infos:
        _reject_if_bad(info[4][0])                 # validate EVERY address (fail-closed)
    return infos[0][0], infos[0][4][0]             # (family, ip) — pin the first


def _open(family, ip, port, scheme, host, timeout=15):
    raw = socket.create_connection((ip, port), timeout=timeout)   # connect to the PINNED ip
    if scheme == "https":
        return ssl.create_default_context().wrap_socket(raw, server_hostname=host)  # SNI+cert for host
    return raw


def _default_fetch(url: str, _depth: int = 0, _open=_open) -> str:
    if _depth > 3:
        raise ValueError("brand_url: too many redirects")
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError("brand_url must be http(s): %r" % url)
    if not p.hostname:
        raise ValueError("brand_url has no host: %r" % url)
    family, ip = _resolve_pinned(p.hostname)       # validate + pin (N1 normalized, N2 no re-resolve)
    port = p.port or (443 if p.scheme == "https" else 80)
    path = (p.path or "/") + (("?" + p.query) if p.query else "")
    sock = _open(family, ip, port, p.scheme, p.hostname)
    try:
        conn = http.client.HTTPConnection(p.hostname, port, timeout=15)
        conn.sock = sock                           # use the pinned, pre-wrapped socket
        conn.putrequest("GET", path, skip_host=True)
        conn.putheader("Host", p.hostname)
        conn.putheader("User-Agent", "edd-engine")
        conn.endheaders()
        resp = conn.getresponse()
        if resp.status in (301, 302, 303, 307, 308):    # follow + re-validate each hop (N3)
            loc = resp.getheader("Location")
            if not loc:
                raise ValueError("brand_url redirect without Location")
            return _default_fetch(urllib.parse.urljoin(url, loc), _depth + 1, _open=_open)
        return resp.read(2_000_000).decode("utf-8", "replace")
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _norm(h: str) -> str:
    h = h.lower()
    if len(h) == 4:  # #abc -> #aabbcc
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def _is_neutralish(h: str) -> bool:
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return max(r, g, b) - min(r, g, b) < 16  # near-grey


def _extract_colors(html: str) -> List[str]:
    seen, ordered = set(), []
    for m in _HEX.findall(html):
        h = _norm(m)
        if h not in seen:
            seen.add(h)
            ordered.append(h)
    chromatic = [h for h in ordered if not _is_neutralish(h)]
    return (chromatic or ordered)[:5]


def _extract_fonts(html: str) -> List[str]:
    out, seen = [], set()
    for fam in _FONT.findall(html):
        name = fam.split(",")[0].strip().strip("\"'")
        key = name.lower()
        if name and key not in seen and not key.startswith(("-apple", "system", "ui-")):
            seen.add(key)
            out.append(name)
    return out[:3]


def capture_brand(pack: InputPack, fetch: Optional[Callable[[str], str]] = None) -> dict:
    m = pack.manifest()
    colors = [_norm(h) for h in _HEX.findall(m.get("brand_colors", ""))]
    fonts = [f.strip() for f in m.get("brand_fonts", "").split(",") if f.strip()]
    source = "pack"
    url = m.get("brand_url")
    if not colors and url:
        html = (fetch or _default_fetch)(url)
        colors = _extract_colors(html)
        fonts = fonts or _extract_fonts(html)
        source = url
    return {
        "colors": [{"hex": h, "role": _ROLES[min(i, len(_ROLES) - 1)], "source": source}
                   for i, h in enumerate(colors)],
        "fonts": [{"family": f, "open_source": f.lower() in _OS_FONTS, "source": source}
                  for f in fonts],
    }
