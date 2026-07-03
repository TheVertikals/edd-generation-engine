import pathlib
import re

from engine import prompts


def test_brief_has_the_required_behaviors():
    b = prompts.DESIGN_BRIEF.lower()
    for phrase in ("reconcile", "no default", "data-source", "prefers-reduced-motion"):
        assert phrase in b


def test_prompts_module_source_is_agnostic():
    # grep the SOURCE, not just the string — an identifier like VANTAGE_BRIEF would trip the gate
    src = pathlib.Path(prompts.__file__).read_text(encoding="utf-8")
    assert not re.search(r"vantage|cortex", src, re.IGNORECASE)


def test_instructions_specify_citation_discipline():
    assert "brand:" in prompts.CREATIVE_DIRECTION_INSTR and "sources" in prompts.CREATIVE_DIRECTION_INSTR
    assert "basis" in prompts.SOLUTION_INSTR and prompts.PURITY_SWEEP_INSTR
