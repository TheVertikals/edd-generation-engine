from typing import List

from engine.bundle import Bundle
from engine.checkpoint import Checkpoint
from engine.gate import Gate
from engine.stage import Stage


class Runner:
    """Walks an ordered list of Stages over one Bundle, checkpointing after each and
    firing the Gate between them. Resumable: stages already in the checkpoint are skipped.
    Stages are fallible/best-effort: a raising stage stops the run with status 'error'
    rather than crashing the process."""

    def __init__(self, bundle: Bundle, gate: Gate, max_revisions: int = 3):
        self.bundle = bundle
        self.gate = gate
        self.max_revisions = max_revisions
        self.checkpoint = Checkpoint(bundle.root)

    def run(self, stages: List[Stage]) -> dict:
        done = self.checkpoint.completed()
        for stage in stages:
            if stage.name in done:
                continue
            revisions = 0
            while True:
                try:
                    stage.run(self.bundle)
                except Exception as exc:  # stages are fallible — surface, don't crash
                    return self._result("error", failed_at=stage.name, error=str(exc))
                spec = stage.gate(self.bundle)
                if spec is None:
                    break  # no gate -> stage is done
                verdict = self.gate.request(spec)
                if verdict.decision == "approve":
                    break
                if verdict.decision == "reject":
                    return self._result("rejected", rejected_at=stage.name)
                # revise: re-run the stage, bounded
                revisions += 1
                if revisions > self.max_revisions:
                    return self._result("rejected", rejected_at=stage.name)
            self.checkpoint.mark(stage.name)
        return self._result("complete")

    def _result(self, status, rejected_at=None, failed_at=None, error=None) -> dict:
        return {
            "status": status,
            "completed": self.checkpoint.completed(),
            "rejected_at": rejected_at,
            "failed_at": failed_at,
            "error": error,
        }
