from pathlib import Path
from typing import Optional


class InputPack:
    """A per-engagement directory of generic, normalized input files plus a manifest.

    The pack is a boundary contract: its producer matures over phases (a stub fixture,
    then a minimal transcript/notes adapter, then a sovereign capture-and-memory
    substrate) but the Engine only ever sees plain files and cannot tell the producers
    apart. That is what keeps the Engine agnostic.

    Skeleton scope: the manifest parser reads scalar `key: value` lines only. Structured
    fields (e.g. provenance source lists) are out of scope here and land in a later plan.
    """

    def __init__(self, root: str):
        self.root = root

    def manifest(self) -> dict:
        raw = self.read("inputpack.yaml") or ""
        out = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
        return out

    def read(self, rel: str) -> Optional[str]:
        try:
            return (Path(self.root) / rel).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
