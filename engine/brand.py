import re
from typing import Callable, List, Optional

from engine.inputpack import InputPack

_HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_FONT = re.compile(r"font-family\s*:\s*([^;\}\"']+)", re.IGNORECASE)
_OS_FONTS = {"geist", "geist mono", "hanken grotesk", "ibm plex sans", "ibm plex mono",
             "bricolage grotesque", "inter", "eb garamond", "fraunces", "space grotesk",
             "source sans 3", "work sans", "public sans"}
_ROLES = ("primary", "secondary", "neutral", "accent", "support")


def _default_fetch(url: str) -> str:
    import urllib.parse
    import urllib.request
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError("brand_url must be http(s): %r" % url)
    # public brand page only; no auth headers, so no client-confidential egress.
    # NOTE: scheme + body-cap only; private-IP / DNS-rebinding SSRF hardening is deferred.
    req = urllib.request.Request(url, headers={"User-Agent": "edd-engine"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read(2_000_000).decode("utf-8", "replace")


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
