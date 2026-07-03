import json
from pathlib import Path
from typing import Optional

_DEFAULT_KIT = {"display": "geist", "mono": "geist-mono", "expressive": "bricolage"}


def _assets_dir(override: Optional[str]) -> Path:
    return Path(override) if override else Path(__file__).resolve().parent / "assets" / "fonts"


def font_faces(kit: Optional[dict] = None, assets_dir: Optional[str] = None) -> str:
    """Return @font-face CSS with inlined data: URIs for the resolved kit; skip any face whose
    asset is absent (system fallback). Empty when the kit hasn't been vendored."""
    root = _assets_dir(assets_dir)
    try:
        manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return ""
    kit = kit or _DEFAULT_KIT
    blocks = []
    for key in kit.values():
        entry = manifest.get(key)
        if not entry:
            continue
        for weight, fname in entry.get("weights", {}).items():
            try:
                b64 = (root / fname).read_text(encoding="utf-8").strip()
            except (FileNotFoundError, OSError):
                continue
            blocks.append(
                "@font-face{{font-family:'{fam}';font-weight:{w};font-display:swap;"
                "src:url(data:font/woff2;base64,{b64}) format('woff2');}}".format(
                    fam=entry["family"], w=weight, b64=b64))
    return "\n".join(blocks)
