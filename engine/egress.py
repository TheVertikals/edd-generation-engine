# engine/egress.py
"""One guarded egress throat. Wrap every Generator whose output leaves the boundary in an
EgressGuard sharing one EgressPolicy: redaction + PII sweep applied to ALL request fields, and a
per-distinct-payload operator preview. Fail-closed — empty/non-list terms, a missing preview, or a
rejection all BLOCK. Agnostic: knows only an alias, a term list, and a preview callback."""
import hashlib
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set

from engine.generator import GenRequest, GenResult, Generator
from engine.pii import residual_pii
from engine.redact import Redactor
from engine.stage import StageBlocked


class EgressError(StageBlocked):
    """Raised to BLOCK egress: unconfigured redaction, a missing preview, or operator rejection.
    Subclasses StageBlocked (F-6) so an operator egress-reject surfaces as run status 'blocked'
    — a first-class human decision — rather than an unexpected 'error' crash."""


@dataclass
class EgressPolicy:
    alias: str
    terms: List[str]
    preview: Optional[Callable[[str], bool]] = None
    allow_cleartext: bool = False
    _redactor: Redactor = field(default=None, init=False, repr=False)
    _approved: Set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self):
        if not self.allow_cleartext:
            if not isinstance(self.terms, list) or not all(isinstance(t, str) for t in self.terms):
                raise EgressError("redact_terms must be a list of strings, got %r" % type(self.terms).__name__)
            if not [t for t in self.terms if t.strip()]:
                raise EgressError("redact_terms is empty — refusing to egress client content unredacted")
        self._redactor = Redactor(self.alias, self.terms if isinstance(self.terms, list) else [])

    def scrub(self, text: str) -> str:
        return residual_pii(self._redactor.redact(text or ""))

    def gate(self, prompt: str, key: Optional[str] = None) -> None:
        # Dedup the operator preview on the client-content `key` (the scrubbed grounding). A
        # None key (empty grounding) hashes the PROMPT so it is never a skeleton key (audit B①).
        if key is None:
            key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if self.allow_cleartext or key in self._approved:
            return
        if self.preview is None:
            raise EgressError("no operator preview configured — refusing to egress client content")
        if not self.preview(prompt):
            raise EgressError("operator rejected the egress preview")
        self._approved.add(key)


class EgressGuard(Generator):
    def __init__(self, inner: Generator, policy: EgressPolicy):
        self.inner = inner
        self.policy = policy

    def generate(self, req: GenRequest) -> GenResult:
        s = self.policy.scrub
        grounding = {}
        for k, v in (req.grounding or {}).items():
            if any(ch.isspace() for ch in k):        # N1: ids are generic — client content is not; and
                raise EgressError(                   #     scrubbing a key would break its audit resolution
                    "grounding id %r contains whitespace — refusing (ids must carry no client content)" % k)
            grounding[k] = s(v)                       # scrub VALUES only; keys must resolve at the final audit
        safe = GenRequest(
            task=req.task,
            instructions=s(req.instructions),
            grounding=grounding,
            schema=req.schema,
            note=s(req.note) if req.note else req.note,
            timeout_s=req.timeout_s, model=req.model)
        # B①: dedup the operator preview on the SCRUBBED CLIENT CONTENT (the grounding), not the
        # full prompt — later-stage instruction differences must not each demand a tap. An EMPTY
        # grounding -> None -> gate() hashes the prompt (never a skeleton key).
        content_key = (hashlib.sha256(
            "\n".join("%s=%s" % (k, grounding[k]) for k in sorted(grounding)).encode("utf-8")).hexdigest()
            if grounding else None)
        self.policy.gate(self.compose_prompt(safe), content_key)
        return self.inner.generate(safe)
