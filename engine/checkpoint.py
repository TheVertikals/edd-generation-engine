import json
import os
from pathlib import Path
from typing import List


class Checkpoint:
    """Resumable state: the ordered list of completed stage names, persisted at
    <root>/.engine/state.json."""

    def __init__(self, root: str):
        self._path = Path(root) / ".engine" / "state.json"

    def completed(self) -> List[str]:
        try:
            return json.loads(self._path.read_text(encoding="utf-8")).get("completed", [])
        except (FileNotFoundError, ValueError, OSError):
            return []

    def mark(self, name: str) -> None:
        done = self.completed()
        if name not in done:
            done.append(name)
        self._write({"completed": done})

    def reset(self) -> None:
        self._write({"completed": []})

    def _write(self, obj: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.parent / (self._path.name + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)
