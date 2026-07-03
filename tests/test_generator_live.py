import os

import pytest

from engine.generator import ClaudeCliGenerator, GenRequest

pytestmark = pytest.mark.skipif(
    os.environ.get("EDD_ENGINE_LIVE") != "1",
    reason="live test: set EDD_ENGINE_LIVE=1 and have the claude CLI installed",
)


def test_live_claude_returns_structured_output():
    gen = ClaudeCliGenerator(allow_cleartext=True)
    res = gen.generate(GenRequest(
        task="smoke", instructions='Return JSON {"ok": true} and nothing else.',
        grounding={"s1": "the sky is blue"}, schema={"type": "object"}, timeout_s=120))
    assert res.ok, res.error
    assert isinstance(res.data, dict)
