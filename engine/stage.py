from dataclasses import dataclass
from typing import Optional

from engine.bundle import Bundle


@dataclass
class GateSpec:
    """The human decision to fire after a stage. `preview` points at a bundle-relative
    artifact (e.g. a mockup) for visual gates; the skeleton carries it opaquely."""
    question: str
    preview: Optional[str] = None


class StageBlocked(Exception):
    """A stage raises this to signal a *policy block* (e.g. a failed grounding audit), as
    distinct from an unexpected crash. The runner reports it as status 'blocked'."""


class Stage:
    """A bounded unit of work. Reads and writes ONLY via the bundle; never imports or
    calls another stage. Subclasses set `name` and implement `run`; override `gate` to
    require a human decision after the stage (return None for no gate). `run` receives the
    operator's revise `note` on a re-run (None on the first run)."""
    name = "stage"

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        raise NotImplementedError

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return None
