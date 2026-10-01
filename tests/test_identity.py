"""Machine-name grammar and alias resolution."""

import pytest

from benchmark_data.identity import (
    ALIAS_COLS,
    IDENT_COLS,
    load_aliases,
    model_id,
    resolve_model,
    split_name,
    strip_name,
)


def _alias(**kw):
    return {**{c: "" for c in [*IDENT_COLS, "harness"]}, **kw}


@pytest.mark.parametrize("name, expected", [
    ("claude-opus-4-8_high", dict(base_model="claude-opus-4-8", reasoning_level="high")),
    ("zai-org/glm-4.7", dict(base_model="glm-4.7")),
    ("claude-opus-4-6_120K", dict(base_model="claude-opus-4-6", reasoning_tokens="120000")),
    # Epoch's "effort unknown" and the bare name are one identity (2026-09-09).
    ("claude-opus-4-5-20251101_unknown",
     dict(base_model="claude-opus-4-5", snapshot="2025-11-01")),
    ("gpt-5-2025-08-07_medium",
     dict(base_model="gpt-5", snapshot="2025-08-07", reasoning_level="medium")),
    ("kimi-k2-thinking", dict(base_model="kimi-k2-thinking")),
    ("kimi-k2_thinking", dict(base_model="kimi-k2", variant="thinking")),
    ("Qwen3-235B-A22B-Thinking-2507", dict(base_model="Qwen3-235B-A22B-Thinking-2507")),
    ("some-model_weird", dict(base_model="some-model_weird")),
])
def test_split_name(name, expected):
    ident = split_name(name)
    blank = dict.fromkeys(ident, "")
    assert ident == {**blank, **expected}


def test_strip_name_removes_footnote_markers():
    assert strip_name("gpt-5.4 (xHigh)*") == "gpt-5.4 (xHigh)"
    assert strip_name("Qwen3-Omni† ") == "Qwen3-Omni"
    assert strip_name("Opus 5 (Claude Code) xHigh\n") == "Opus 5 (Claude Code) xHigh"


def test_unknown_and_known_never_merge():
    assert model_id(split_name("opus-5")) != model_id(split_name("opus-5_high"))


def test_resolve_prefers_alias_then_split():
    aliases = {"Opus 4.8": _alias(base_model="claude-opus-4-8")}
    assert resolve_model("Opus 4.8", aliases, splittable=False)[0] == "ok"
    assert resolve_model("Opus 4.9", aliases, splittable=False) == ("unmapped", None, "")
    _, ident, harness = resolve_model("claude-opus-4-9_high", aliases, splittable=True)
    assert ident["reasoning_level"] == "high" and harness == ""


def test_alias_harness_is_returned_but_not_part_of_identity():
    entry = _alias(base_model="claude-opus-4-8", reasoning_level="xhigh", harness="Claude Code")
    aliases = {"Opus 4.8 (Claude Code) xhigh": entry}
    status, ident, harness = resolve_model("Opus 4.8 (Claude Code) xhigh", aliases, False)
    assert status == "ok" and harness == "Claude Code" and "harness" not in ident
    assert model_id(ident) == model_id(split_name("claude-opus-4-8_xhigh"))


def test_alias_with_blank_base_model_is_a_drop():
    aliases = {"Unsafety Llama": _alias()}
    assert resolve_model("Unsafety Llama", aliases, splittable=False) == ("drop", None, "")


def test_load_aliases_rejects_duplicates_and_bad_header(tmp_path):
    good = tmp_path / "a.csv"
    good.write_text(",".join(ALIAS_COLS) + "\nx,y,,,,,,\nx,z,,,,,,\n")
    with pytest.raises(ValueError, match="duplicated"):
        load_aliases(good)
    bad = tmp_path / "b.csv"
    bad.write_text("raw_name,base_model\n")
    with pytest.raises(ValueError, match="columns"):
        load_aliases(bad)


def test_known_effort_or_budget_makes_thinking_implicit():
    from benchmark_data.identity import normalize
    base = {"base_model": "m", "reasoning_level": "", "reasoning_tokens": "", "snapshot": "",
            "variant": "thinking"}
    assert normalize(base)["variant"] == "thinking", "no effort known: the variant stays"
    assert normalize({**base, "reasoning_tokens": "16000"})["variant"] == ""
    assert normalize({**base, "reasoning_level": "high"})["variant"] == ""


def test_strip_name_removes_superscript_footnotes():
    assert strip_name("Claude Opus 4.7 ⁸") == "Claude Opus 4.7"
    assert strip_name("OpenAI o3-mini ¹†") == "OpenAI o3-mini"


def test_hybrid_mode_reads_the_epoch_convention():
    from benchmark_data.identity import hybrid_mode
    bases = {"claude-opus-4-6", "claude-opus-4"}
    assert hybrid_mode("claude-opus-4-6_unknown", bases) == "thinking"
    assert hybrid_mode("claude-opus-4-6", bases) == "none"
    assert hybrid_mode("claude-opus-4-20250514", bases) == "none"
    card = "Thinking level unknown. From the system card"
    assert hybrid_mode("claude-opus-4-20250514", bases, card) == ""
    assert hybrid_mode("claude-opus-4-6_max", bases) == ""          # the name says it already
    assert hybrid_mode("gpt-5.5_unknown", bases) == ""              # not a hybrid base


def test_machine_name_keeps_named_variants_apart():
    from benchmark_data.identity import machine_name
    base = {"base_model": "gpt-5", "reasoning_level": "", "reasoning_tokens": "",
            "snapshot": "2025-08-07", "variant": ""}
    assert machine_name(base) == "gpt-5-2025-08-07"
    assert machine_name({**base, "variant": "chat"}) == "gpt-5-2025-08-07_chat"
    cyber = {**base, "base_model": "gpt-5.5", "snapshot": "", "variant": "Cyber"}
    assert machine_name(cyber) == "gpt-5.5_cyber"
