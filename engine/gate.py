from dataclasses import dataclass
from typing import List

from engine.stage import GateSpec


@dataclass
class Verdict:
    decision: str  # "approve" | "revise" | "reject"
    note: str = ""


class Gate:
    def request(self, spec: GateSpec) -> Verdict:
        raise NotImplementedError


class AutoApproveGate(Gate):
    def request(self, spec: GateSpec) -> Verdict:
        return Verdict("approve")


class ScriptedGate(Gate):
    """Test double: returns pre-scripted verdicts in order."""

    def __init__(self, verdicts: List[Verdict]):
        self._verdicts = list(verdicts)

    def request(self, spec: GateSpec) -> Verdict:
        assert self._verdicts, "ScriptedGate exhausted"
        return self._verdicts.pop(0)
