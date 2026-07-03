import json
import subprocess

import pytest

from engine.generator import ClaudeCliGenerator, GenRequest
from engine.redact import Redactor


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _envelope(result="", structured_output=None, is_error=False, **extra):
    """Mirror the real `claude -p --output-format json` envelope (CLI 2.1.199)."""
    env = {"type": "result", "subtype": "error" if is_error else "success",
           "is_error": is_error, "result": result, "session_id": "s", "num_turns": 1}
    if structured_output is not None:
        env["structured_output"] = structured_output
    env.update(extra)
    return json.dumps(env)


def test_construction_requires_redactor_or_explicit_cleartext():
    with pytest.raises(ValueError):
        ClaudeCliGenerator()  # no redactor, no allow_cleartext -> fail closed


def test_prompt_goes_on_stdin_redacted_and_command_locked_down():
    captured = {}

    def fake_run(cmd, input, timeout):
        captured["cmd"], captured["input"] = cmd, input
        return _Proc(stdout=_envelope(result=json.dumps({"pains": []}),
                                      structured_output={"pains": []}))

    gen = ClaudeCliGenerator(redactor=Redactor("ALIAS", ["Northwind"]), run=fake_run)
    res = gen.generate(GenRequest(task="research", instructions="Find pains at Northwind.",
                                  grounding={"s1": "Northwind is slow"}, schema={"x": 1}))
    cmd = captured["cmd"]
    # prompt travels on stdin, redacted; never in argv
    assert "Northwind" not in captured["input"] and "ALIAS" in captured["input"]
    assert "Northwind" not in " ".join(cmd)
    assert "Find pains" not in " ".join(cmd)
    # headless + json envelope
    assert "-p" in cmd
    assert cmd[cmd.index("--output-format") + 1] == "json"
    # tool lockdown: --tools "" disables ALL built-in tools; --strict-mcp-config
    # (with no --mcp-config) disables MCP; --disallowedTools is the extra deny layer
    assert cmd[cmd.index("--tools") + 1] == ""
    assert "--strict-mcp-config" in cmd
    assert "Bash" in cmd[cmd.index("--disallowedTools") + 1]
    # schema flag carries the schema inline
    assert json.loads(cmd[cmd.index("--json-schema") + 1]) == {"x": 1}
    assert res.ok and res.data == {"pains": []}


def test_model_flag_wired_through_when_set_and_absent_when_not():
    seen = []

    def fake_run(cmd, input, timeout):
        seen.append(cmd)
        return _Proc(stdout=_envelope(result="hi"))

    gen = ClaudeCliGenerator(allow_cleartext=True, run=fake_run)
    gen.generate(GenRequest("t", "", {}, model="claude-fable-5"))
    gen.generate(GenRequest("t", "", {}))
    assert seen[0][seen[0].index("--model") + 1] == "claude-fable-5"
    assert "--model" not in seen[1]


def test_structured_output_key_preferred_with_result_string_fallback():
    # real schema runs return BOTH: structured_output (parsed) + result (string JSON)
    g1 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(
        stdout=_envelope(result=json.dumps({"a": 1}), structured_output={"a": 1})))
    r1 = g1.generate(GenRequest("t", "", {}, schema={"type": "object"}))
    assert r1.ok and r1.data == {"a": 1} and r1.text == json.dumps({"a": 1})

    # no structured_output key: fall back to parsing result as JSON
    g2 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(
        stdout=_envelope(result=json.dumps({"b": 2}))))
    r2 = g2.generate(GenRequest("t", "", {}, schema={"type": "object"}))
    assert r2.ok and r2.data == {"b": 2}


def test_schema_requested_but_unparseable_fails_loud():
    gen = ClaudeCliGenerator(allow_cleartext=True,
                             run=lambda cmd, input, timeout: _Proc(stdout=_envelope(result="prose, not json")))
    res = gen.generate(GenRequest("t", "", {}, schema={"x": 1}))
    assert not res.ok and "schema" in res.error.lower()


def test_envelope_is_error_fails_loud_even_on_zero_exit():
    gen = ClaudeCliGenerator(allow_cleartext=True,
                             run=lambda cmd, input, timeout: _Proc(
                                 stdout=_envelope(result="credit balance too low", is_error=True)))
    res = gen.generate(GenRequest("t", "", {}))
    assert not res.ok and "credit balance too low" in res.error


def test_nonzero_exit_and_timeout_and_parse_errors():
    g1 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(returncode=1, stderr="boom"))
    assert not g1.generate(GenRequest("t", "", {})).ok

    def to(c, input, timeout):
        raise subprocess.TimeoutExpired(c, timeout)

    g2 = ClaudeCliGenerator(allow_cleartext=True, run=to)
    assert "timeout" in g2.generate(GenRequest("t", "", {})).error.lower()

    g3 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(stdout="not json"))
    assert not g3.generate(GenRequest("t", "", {})).ok

    g4 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(stdout='["not", "a", "dict"]'))
    assert not g4.generate(GenRequest("t", "", {})).ok
