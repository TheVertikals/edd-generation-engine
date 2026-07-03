import json
import subprocess

import pytest

from engine.generator import ClaudeCliGenerator, GenRequest
from engine.redact import Redactor


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_construction_requires_redactor_or_explicit_cleartext():
    with pytest.raises(ValueError):
        ClaudeCliGenerator()  # no redactor, no allow_cleartext -> fail closed


def test_prompt_goes_on_stdin_redacted_and_command_locked_down():
    captured = {}

    def fake_run(cmd, input, timeout):
        captured["cmd"], captured["input"] = cmd, input
        return _Proc(stdout=json.dumps({"result": json.dumps({"pains": []})}))

    gen = ClaudeCliGenerator(redactor=Redactor("ALIAS", ["Northwind"]), run=fake_run)
    res = gen.generate(GenRequest(task="research", instructions="Find pains at Northwind.",
                                  grounding={"s1": "Northwind is slow"}, schema={"x": 1}))
    assert "Northwind" not in captured["input"] and "ALIAS" in captured["input"]
    assert "Northwind" not in " ".join(captured["cmd"])
    joined = " ".join(captured["cmd"])
    assert "--output-format" in joined and "json" in joined
    assert "--allowedTools" in joined
    assert res.ok and res.data == {"pains": []}


def test_schema_requested_but_unparseable_fails_loud():
    gen = ClaudeCliGenerator(allow_cleartext=True,
                             run=lambda cmd, input, timeout: _Proc(stdout=json.dumps({"result": "prose, not json"})))
    res = gen.generate(GenRequest("t", "", {}, schema={"x": 1}))
    assert not res.ok and "schema" in res.error.lower()


def test_nonzero_exit_and_timeout_and_parse_errors():
    g1 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(returncode=1, stderr="boom"))
    assert not g1.generate(GenRequest("t", "", {})).ok

    def to(c, input, timeout):
        raise subprocess.TimeoutExpired(c, timeout)

    g2 = ClaudeCliGenerator(allow_cleartext=True, run=to)
    assert "timeout" in g2.generate(GenRequest("t", "", {})).error.lower()

    g3 = ClaudeCliGenerator(allow_cleartext=True, run=lambda c, input, timeout: _Proc(stdout="not json"))
    assert not g3.generate(GenRequest("t", "", {})).ok
