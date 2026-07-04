from engine.frontmatter import parse_yaml, parse_frontmatter

# A domain-NEUTRAL fixture that exercises the parser's full surface: nested maps, block lists of
# maps at both indents, a map nested inside a list item, flow lists, null, ints, inline comments,
# and quotes. The parser is agnostic; any real proprietary contract is exercised only in a
# downstream tier's own (private) tests, never here.
SAMPLE = """\
name: "Acme — sample"
type: record
metadata:
  id: "20260703T120000-rec1"
  schema_version: 2
  ref_id: "01KVEXAMPLEREFID000000"   # join key -> a related record id
  handle: "northstar"                # a short handle
  sources: ["cap-20260701-a", "note-b"]
  links: []
  projects: [acme-tools]
  mask_terms: ["<Placeholder Co>", "<Placeholder Name>"]   # masked before egress
  posture: "recorded"
  contacts:
    - handle: "lead-1"
      role: "engineering lead"
      basis: ["cap-20260701-a"]
      status: "active"
  records:
    - ref_id: "01KVEXAMPLEREFID000000"
      input_ref: "inputs/rec-2026-07-03/"
      exits:
        primary: null
        secondary: "outputs/rec-2026-07-03/summary.md"
      created_at: "2026-07-03T18:00:00Z"
tags: [record, sample-fixture]
"""

def test_scalars_lists_and_ints():
    d = parse_yaml(SAMPLE); m = d["metadata"]
    assert d["type"] == "record" and d["tags"] == ["record", "sample-fixture"]
    assert m["ref_id"] == "01KVEXAMPLEREFID000000" and m["handle"] == "northstar"
    assert m["schema_version"] == 2
    assert m["sources"] == ["cap-20260701-a", "note-b"]
    assert m["links"] == [] and m["projects"] == ["acme-tools"]
    assert m["mask_terms"] == ["<Placeholder Co>", "<Placeholder Name>"]

def test_block_list_of_maps_and_nested_exits_with_null():
    m = parse_yaml(SAMPLE)["metadata"]
    assert m["contacts"][0]["handle"] == "lead-1"
    assert m["contacts"][0]["basis"] == ["cap-20260701-a"]
    rec = m["records"][0]
    assert rec["exits"]["primary"] is None            # null -> None, not the string "null"
    assert rec["exits"]["secondary"].endswith("summary.md")

def test_no_top_level_pollution():
    d = parse_yaml(SAMPLE)
    for leaked in ("role", "status", "input_ref", "primary", "basis"):
        assert leaked not in d

def test_same_indent_block_list_keeps_following_keys():   # F5
    d = parse_yaml("ref_id: 01ABC\nsources:\n- cap-1\n- cap-2\npack_version: 1\n")
    assert d["sources"] == ["cap-1", "cap-2"]
    assert d["ref_id"] == "01ABC" and d["pack_version"] == 1   # not dropped

def test_frontmatter_bom_and_absent():
    assert parse_frontmatter("﻿---\nmetadata:\n  handle: n\n---\nbody")["metadata"]["handle"] == "n"
    assert parse_frontmatter("no frontmatter") == {}

def test_bare_scalar_and_null():
    assert parse_yaml("ref_id: 01ABC  # note\npack_version: 1\n") == {"ref_id": "01ABC", "pack_version": 1}
    assert parse_yaml("x: null\ny: ~\n") == {"x": None, "y": None}
