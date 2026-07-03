import pytest

from engine.bundle import Bundle
from engine.generator import FakeGenerator, GenResult
from engine.purity import PurityError
from engine.stages.mockup import MockupStage


def _b(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("pains.json", '{"pains":[{"id":"p1","statement":"slow","confidence":"verified","sources":["intake:1"],"basis":[]}]}')
    b.write("solutions.json", '{"solutions":[{"id":"sol1","pain_id":"p1","approach":"wizard","statement":"wizard","confidence":"inferred","sources":[],"basis":["p1"]}]}')
    b.write("creative-direction.json", '{"claims":[]}')
    b.write("brand.json", '{"colors":[{"hex":"#0073cf","role":"primary","source":"pack"}],"fonts":[]}')
    return b


def test_mockup_injects_brand_and_passes_when_model_uses_it(tmp_path):
    b = _b(tmp_path)
    html = '<head><style>h2{color:var(--brand-primary)}</style></head><body><h2 data-source="sol1">Wizard</h2></body>'
    MockupStage(FakeGenerator(lambda r: GenResult(ok=True, text=html))).run(b)
    out = b.read("surfaces/prototype.html")
    assert 'data-source="sol1"' in out and "--brand-primary:" in out and "var(--brand-primary)" in out


def test_mockup_blocks_when_model_ignores_brand(tmp_path):
    b = _b(tmp_path)
    with pytest.raises(PurityError):
        MockupStage(FakeGenerator(lambda r: GenResult(ok=True, text='<h2 data-source="sol1">x</h2>')),
                    max_regen=1).run(b)


def test_mockup_blocks_on_orphan_citation(tmp_path):
    b = _b(tmp_path)
    html = '<h2 data-source="GHOST">x</h2><style>var(--brand-primary)</style>'
    with pytest.raises(PurityError):
        MockupStage(FakeGenerator(lambda r: GenResult(ok=True, text=html)), max_regen=1).run(b)
