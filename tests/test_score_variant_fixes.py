"""score_variant_fixes.csv: one score moved to the effort its source states, or dropped as a copy
of a labelled score, keyed on its identity and value."""
import pytest

from benchmark_data.identity import model_id, split_name
from benchmark_data.sources import Record
from benchmark_data.steps.ingest import (
    IngestResult,
    _take,
    _with_effort,
    load_score_variant_fixes,
)

HEADER = ("feed,benchmark,model_id,model_version,score,fix,suffix,duplicate_of,source_url,note,"
          "new_model\n")


def _write(tmp_path, rows):
    (tmp_path / "score_variant_fixes.csv").write_text(HEADER + rows)
    return load_score_variant_fixes(tmp_path)


def _result():
    return IngestResult(unmapped={"epoch": set()}, dropped={"epoch": set()})


def test_relabel_and_drop(tmp_path):
    bare = model_id(split_name("m-2025-01-01"))
    fixes = _write(tmp_path, f"epoch,B,{bare},m-2025-01-01,0.5,relabel,_none,,u,n,\n"
                             f"epoch,C,{bare},m-2025-01-01,0.7,drop,,m-2025-01-01_high,u,n,\n"
                             f"epoch,D,{bare},m-2025-01-01,,relabel,_16K,,u,n,\n")
    fixed, result = set(), _result()
    none = model_id(split_name("m-2025-01-01_none"))
    rec = Record("m-2025-01-01_unknown", "B", 0.5)
    assert _take(result, "epoch", rec, {}, fixes, fixed) == none
    # The relabelled run votes for its own spelling, not the bare model's.
    assert result.names[(none, "m-2025-01-01_none")] == 1
    assert _take(result, "epoch", Record("m-2025-01-01", "C", 0.7), {}, fixes, fixed) is None
    # Another value is another run: the fix does not touch it.
    assert _take(result, "epoch", Record("m-2025-01-01", "B", 0.6), {}, fixes, fixed) == bare
    # An empty score matches every value (a benchmark published as a mean of records).
    tok = model_id(split_name("m-2025-01-01_16K"))
    assert _take(result, "epoch", Record("m-2025-01-01", "D", 0.3), {}, fixes, fixed) == tok
    assert len(fixed) == 3


def test_with_effort_keeps_the_rest_of_the_identity():
    ident = split_name("Qwen3-32B")
    assert _with_effort(ident, "_thinking") == split_name("Qwen3-32B_thinking")
    assert _with_effort(split_name("gpt-5.2-2025-12-11"), "_none") == \
        split_name("gpt-5.2-2025-12-11_none")


def test_bad_rows_refused(tmp_path):
    with pytest.raises(ValueError):
        _write(tmp_path, "epoch,B,x,m,0.5,relabel,_bogus,,u,n,\n")
    with pytest.raises(ValueError):
        _write(tmp_path, "epoch,B,x,m,0.5,move,_none,,u,n,\n")


def test_shipped_fixes_load():
    fixes = load_score_variant_fixes()
    assert sum(len(v) for v in fixes.values()) >= 200


def test_remodel_moves_the_score_to_another_model(tmp_path):
    chat = model_id(split_name("deepseek-chat"))
    fixes = _write(tmp_path, f"epoch,LMCA,{chat},deepseek-chat,0.15,remodel,,,u,n,DeepSeek-V3\n")
    fixed, result = set(), _result()
    v3 = model_id(split_name("DeepSeek-V3"))
    assert _take(result, "epoch", Record("deepseek-chat", "LMCA", 0.15), {}, fixes, fixed) == v3
    assert result.names[(v3, "DeepSeek-V3")] == 1


def test_remodel_needs_a_model(tmp_path):
    with pytest.raises(ValueError):
        _write(tmp_path, "epoch,B,x,m,0.5,remodel,,,u,n,\n")


def test_bare_copies_dropped_unless_at_a_bound():
    import pandas as pd

    from benchmark_data.steps.dedup import drop_bare_copies
    models = pd.DataFrame([
        {"model_id": "b", "base_model": "m", "snapshot": "", "reasoning_level": "",
         "reasoning_tokens": "", "variant": ""},
        {"model_id": "h", "base_model": "m", "snapshot": "", "reasoning_level": "high",
         "reasoning_tokens": "", "variant": ""},
        {"model_id": "p", "base_model": "m", "snapshot": "", "reasoning_level": "high",
         "reasoning_tokens": "", "variant": "pro"},
    ])
    scores = pd.DataFrame([
        {"model_id": "b", "benchmark_id": "X", "score": 0.4},   # copy of h -> dropped
        {"model_id": "h", "benchmark_id": "X", "score": 0.4},
        {"model_id": "b", "benchmark_id": "Y", "score": 0.0},   # equal floors: kept
        {"model_id": "h", "benchmark_id": "Y", "score": 0.0},
        {"model_id": "b", "benchmark_id": "Z", "score": 0.3},   # equals the pro mode: kept
        {"model_id": "p", "benchmark_id": "Z", "score": 0.3},
    ])
    kept, dropped = drop_bare_copies(scores, models)
    assert list(zip(dropped.model_id, dropped.benchmark_id, strict=True)) == [("b", "X")]
    assert len(kept) == 5


def test_an_effort_by_convention_yields_to_the_bare_original():
    """Epoch's `_unknown` copy of a Scale row, read as thinking by the Claude hybrid convention,
    goes; the source's own bare row stays."""
    import pandas as pd

    from benchmark_data.steps.dedup import drop_bare_copies
    models = pd.DataFrame([
        {"model_id": "b", "base_model": "c", "snapshot": "", "reasoning_level": "",
         "reasoning_tokens": "", "variant": ""},
        {"model_id": "t", "base_model": "c", "snapshot": "", "reasoning_level": "",
         "reasoning_tokens": "", "variant": "thinking"},
        {"model_id": "k", "base_model": "c", "snapshot": "", "reasoning_level": "",
         "reasoning_tokens": "12000", "variant": ""},
    ])
    scores = pd.DataFrame([
        {"model_id": "b", "benchmark_id": "R", "score": 0.16, "effort_by_convention": False},
        {"model_id": "t", "benchmark_id": "R", "score": 0.16, "effort_by_convention": True},
        # a convention copy of a stated budget goes too, the stated one stays
        {"model_id": "t", "benchmark_id": "S", "score": 0.45, "effort_by_convention": True},
        {"model_id": "k", "benchmark_id": "S", "score": 0.45, "effort_by_convention": False},
    ])
    _, dropped = drop_bare_copies(scores, models)
    assert sorted(zip(dropped.model_id, dropped.benchmark_id, strict=True)) == [("t", "R"),
                                                                                ("t", "S")]
