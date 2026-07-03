import json

import pytest

from engine.bundle import Bundle
from engine.generator import FakeGenerator, GenResult
from engine.stages.research import GenerationError
from engine.stages.synthesize import SynthesizeStage


def _b(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("pains.json", '{"pains":[{"id":"p1","statement":"slow","confidence":"verified","sources":["intake:1"],"basis":[]}]}')
    b.write("solutions.json", '{"solutions":[{"id":"s1","pain_id":"p1","approach":"wizard","statement":"wizard","confidence":"inferred","sources":[],"basis":["p1"]}]}')
    return b


def test_synthesize_fills_docs_from_text_and_manifest(tmp_path):
    b = _b(tmp_path)
    SynthesizeStage(FakeGenerator(lambda r: GenResult(ok=True, text="## drafted\n"))).run(b)
    assert "drafted" in b.read("2_ENDSTATE_SPEC.md")
    m = json.loads(b.read(".edd-manifest.json"))
    assert m["artifacts"]["8_SCOPED_PROPOSAL.md"]["present"] is True


def test_synthesize_raises_when_a_doc_is_empty(tmp_path):
    b = _b(tmp_path)
    with pytest.raises(GenerationError):
        SynthesizeStage(FakeGenerator(lambda r: GenResult(ok=True, text="   "))).run(b)
