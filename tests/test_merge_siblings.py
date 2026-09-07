"""Sibling boards averaged into one series."""

import pandas
import pytest

from benchmark_data.identity import benchmark_id
from benchmark_data.steps.merge_siblings import load_sibling_merges, merge_siblings

COLS = ["model_id", "benchmark_id", "score", "stderr", "harness", "feed", "source_label",
        "source_url"]


def _tables():
    benchmarks = pandas.DataFrame([{"benchmark_id": benchmark_id(n), "name": n}
                                   for n in ("A", "B", "Other")])
    scores = pandas.DataFrame([
        ("m1", benchmark_id("A"), 0.2, 0.01, "Codex", "seal", "Scale SEAL (a)", "https://a"),
        ("m1", benchmark_id("B"), 0.4, 0.03, "Claude Code", "seal", "Scale SEAL (b)", "https://b"),
        ("m2", benchmark_id("A"), 0.6, "", "", "seal", "Scale SEAL (a)", "https://a"),
        ("m1", benchmark_id("Other"), 0.9, "", "", "epoch", "EpochAI", ""),
    ], columns=COLS)
    return scores, benchmarks


def test_parts_are_replaced_by_the_per_model_mean():
    scores, benchmarks = merge_siblings(*_tables(), {"AB": ["A", "B"]})
    assert set(benchmarks["name"]) == {"AB", "Other"}
    ab = scores[scores["benchmark_id"] == benchmark_id("AB")].set_index("model_id")
    assert ab.loc["m1", "score"] == pytest.approx(0.3)   # mean of the two boards
    assert ab.loc["m2", "score"] == pytest.approx(0.6)   # one board only
    assert ab.loc["m1", "stderr"] == pytest.approx((0.01**2 + 0.03**2) ** 0.5 / 2)
    assert ab.loc["m2", "stderr"] == ""
    assert ab.loc["m1", "harness"] == "Claude Code / Codex"
    assert ab.loc["m1", "source_label"] == "Scale SEAL (a) / Scale SEAL (b)"
    assert ab.loc["m1", "source_url"] == "https://a https://b"
    assert (scores["benchmark_id"] == benchmark_id("Other")).sum() == 1


def test_missing_parts_are_ignored():
    scores, benchmarks = _tables()
    out_scores, out_benchmarks = merge_siblings(scores, benchmarks, {"X": ["Nope"]})
    assert len(out_scores) == len(scores) and len(out_benchmarks) == len(benchmarks)


def test_a_board_cannot_belong_to_two_series(tmp_path):
    (tmp_path / "sibling_merges.csv").write_text("merged_name,part\nX,A\nY,A\n")
    with pytest.raises(ValueError):
        load_sibling_merges(tmp_path)
