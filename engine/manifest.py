import json
from typing import Dict, List, Optional

from engine.bundle import Bundle


def write_manifest(bundle: Bundle, artifacts: Dict[str, str],
                   prototypes: Optional[List[str]] = None) -> None:
    """Write .edd-manifest.json in the edd-bundle-manifest/1 shape a renderer resolves against:
    semantic-keyed artifacts ({key: {path, present}}) + a prototypes[] list of present hi-fi
    surfaces. Paths are bundle-relative; do NOT path-key artifacts."""
    arts = {k: {"path": p, "present": bundle.exists(p)} for k, p in artifacts.items()}
    protos = [p for p in (prototypes or []) if bundle.exists(p)]
    bundle.write(".edd-manifest.json", json.dumps(
        {"schema": "edd-bundle-manifest/1", "artifacts": arts, "prototypes": protos}, indent=2))
