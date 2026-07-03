import json
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union

GROUNDING_PREAMBLE = (
    "You are generating content that will be audited for grounding.\n"
    "Rules you must follow exactly:\n"
    "1. Ground every claim in the GROUNDING FACTS provided below. NEVER manufacture facts.\n"
    "2. Every factual claim must cite the source id(s) it comes from, in its `sources` list.\n"
    "3. You may offer educated design opinions, but each opinion must be marked with\n"
    "   confidence `inferred` and carry a `basis` list of the grounded fact ids it reasons from.\n"
    "4. Assign every item a confidence tier: verified | corroborated | inferred | speculative.\n"
    "5. If you cannot ground a claim in the facts, mark it `speculative` or omit it.\n"
    "   Do not present speculation as fact."
)


@dataclass
class GenRequest:
    task: str
    instructions: str
    grounding: Dict[str, str]
    schema: Optional[dict] = None
    note: Optional[str] = None
    timeout_s: int = 300
    model: Optional[str] = None


@dataclass
class GenResult:
    ok: bool
    text: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None


class Generator:
    def generate(self, req: GenRequest) -> GenResult:
        raise NotImplementedError

    def compose_prompt(self, req: GenRequest) -> str:
        facts = "\n".join("[%s] %s" % (sid, txt) for sid, txt in sorted(req.grounding.items()))
        parts = [GROUNDING_PREAMBLE, "\nGROUNDING FACTS:\n" + (facts or "(none provided)"),
                 "\nTASK:\n" + req.instructions]
        if req.note:
            parts.append("\nREVISION NOTE (address this):\n" + req.note)
        return "\n".join(parts)


class FakeGenerator(Generator):
    """Hermetic test double. `responses` is a callable(req)->GenResult, or a dict task->data."""

    def __init__(self, responses: Union[Callable[[GenRequest], GenResult], Dict[str, dict]]):
        self._responses = responses

    def generate(self, req: GenRequest) -> GenResult:
        if callable(self._responses):
            return self._responses(req)
        if req.task in self._responses:
            return GenResult(ok=True, data=self._responses[req.task])
        return GenResult(ok=False, error="no fake response for task %r" % req.task)


def _default_run(cmd: List[str], input: str, timeout: int):
    return subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)


class ClaudeCliGenerator(Generator):
    """Real generator: shells to the headless `claude` CLI, locked down (no tools/MCP/extra
    dirs) so untrusted transcript text cannot drive tool use. The prompt goes on STDIN
    (avoids ARG_MAX and `ps` leakage) and is REDACTED first. Fail-closed: refuses to run
    without a redactor unless `allow_cleartext=True`. `run` is injectable for hermetic tests.

    CLI flag contract (CONFIRMED against claude CLI 2.1.199):
      * `-p` / `--print`: headless mode; with no prompt argv arg the prompt is read from STDIN.
      * `--output-format json`: stdout is a single JSON envelope, e.g.
        {"type": "result", "subtype": "success", "is_error": false,
         "result": "<assistant text>", "structured_output": {...}, ...}.
        `structured_output` is present (as a parsed object) only when --json-schema was
        given; `result` then also holds the same JSON as a string.
      * `--json-schema <schema>`: structured output validated against the inline JSON Schema.
      * Tool lockdown: `--tools ""` disables ALL built-in tools (documented: 'Use "" to
        disable all tools'); `--strict-mcp-config` with no --mcp-config disables all MCP
        servers; `--disallowedTools "..."` kept as a redundant deny layer.
        (--allowedTools only pre-approves permissions; it does not restrict availability.)
      * `--model <model>`: alias (e.g. "fable") or full name (e.g. "claude-fable-5")."""

    def __init__(self, redactor=None, allow_cleartext: bool = False, run=None, claude_bin: str = "claude"):
        if redactor is None and not allow_cleartext:
            raise ValueError("ClaudeCliGenerator requires a redactor (or explicit allow_cleartext=True)")
        self.redactor = redactor
        self._run = run or _default_run
        self.claude_bin = claude_bin

    def generate(self, req: GenRequest) -> GenResult:
        prompt = self.compose_prompt(req)
        if self.redactor is not None:
            prompt = self.redactor.redact(prompt)
        cmd = [self.claude_bin, "-p", "--output-format", "json",
               "--tools", "", "--strict-mcp-config",
               "--disallowedTools", "Bash Edit Write Read WebFetch WebSearch"]
        if req.model:
            cmd += ["--model", req.model]
        if req.schema is not None:
            cmd += ["--json-schema", json.dumps(req.schema)]
        try:
            proc = self._run(cmd, input=prompt, timeout=req.timeout_s)
        except (subprocess.TimeoutExpired, TimeoutError) as exc:
            return GenResult(ok=False, error="timeout: %s" % exc)
        except Exception as exc:
            return GenResult(ok=False, error="run failed: %s" % exc)
        if proc.returncode != 0:
            return GenResult(ok=False, error=(proc.stderr or "nonzero exit").strip())
        return self._parse(proc.stdout, schema_requested=req.schema is not None)

    def _parse(self, stdout: str, schema_requested: bool) -> GenResult:
        try:
            envelope = json.loads(stdout)
        except ValueError:
            return GenResult(ok=False, error="parse error: CLI output was not JSON")
        if not isinstance(envelope, dict):
            return GenResult(ok=False, error="parse error: CLI envelope was not a JSON object")
        if envelope.get("is_error"):
            detail = envelope.get("result") or envelope.get("subtype") or "unknown"
            return GenResult(ok=False, error="CLI reported error: %s" % detail)
        text = envelope.get("result")
        text = text if isinstance(text, str) else ""
        data = envelope.get("structured_output")
        if not isinstance(data, dict):
            data = None
        if data is None and text:
            try:
                maybe = json.loads(text)
            except ValueError:
                maybe = None
            if isinstance(maybe, dict):
                data = maybe
        if schema_requested and not isinstance(data, dict):
            return GenResult(ok=False, error="schema requested but model output was not a JSON object")
        return GenResult(ok=True, text=text, data=data)
