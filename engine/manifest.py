import json
from typing import List

from engine.bundle import Bundle


def write_manifest(bundle: Bundle, paths: List[str]) -> None:
    """Write .edd-manifest.json (schema edd-bundle-manifest/1), recording each artifact's presence."""
    arts = {p: {"path": p, "present": bundle.exists(p)} for p in paths}
    bundle.write(".edd-manifest.json",
                 json.dumps({"schema": "edd-bundle-manifest/1", "artifacts": arts}, indent=2))
