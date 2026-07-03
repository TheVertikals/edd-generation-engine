from engine.generator import FakeGenerator, GenRequest, GenResult, Generator, GROUNDING_PREAMBLE


def test_compose_prompt_includes_preamble_grounding_and_note():
    req = GenRequest(task="research", instructions="Find pains.",
                     grounding={"s1": "VP said onboarding is slow."}, note="be specific")
    prompt = Generator().compose_prompt(req)
    assert GROUNDING_PREAMBLE.split("\n")[0] in prompt
    assert "s1" in prompt and "onboarding is slow" in prompt
    assert "Find pains." in prompt and "be specific" in prompt


def test_fake_returns_mapped_data():
    res = FakeGenerator({"research": {"pains": []}}).generate(GenRequest("research", "", {}))
    assert res.ok and res.data == {"pains": []}


def test_fake_varies_on_note():
    fake = FakeGenerator(lambda req: GenResult(ok=True, data={"noted": bool(req.note)}))
    assert fake.generate(GenRequest("t", "", {})).data == {"noted": False}
    assert fake.generate(GenRequest("t", "", {}, note="fix")).data == {"noted": True}
