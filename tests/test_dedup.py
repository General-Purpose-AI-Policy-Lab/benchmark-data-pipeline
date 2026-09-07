"""Deduplication policy: exact duplicates, then max; harness rides with the winner."""

import pandas
import pytest

from benchmark_data.steps.dedup import dedup

COLS = ["model_id", "benchmark_id", "score", "stderr", "harness", "feed"]


def _scores(rows):
    return pandas.DataFrame(rows, columns=COLS)


def test_exact_duplicates_are_merged_and_counted():
    d, report, n_exact = dedup(_scores([("m", "b", 0.5, "", "", "epoch"),
                                        ("m", "b", 0.5, "", "", "seal")]))
    assert n_exact == 1 and len(d) == 1 and report.empty


def test_disagreement_defaults_to_max():
    d, report, _ = dedup(_scores([("m", "b", 0.4, "", "", "epoch"),
                                  ("m", "b", 0.6, "", "", "seal")]))
    assert d["score"].tolist() == [0.6]
    assert report.iloc[0]["spread"] == pytest.approx(0.2)
    assert report.iloc[0]["feeds"] == "epoch, seal"


def test_best_harness_wins_and_is_kept():
    d, _, _ = dedup(_scores([("m", "b", 0.4, "", "Codex", "epoch"),
                             ("m", "b", 0.7, "", "Claude Code", "epoch")]))
    assert d["harness"].tolist() == ["Claude Code"]


def test_feeds_are_just_harnesses_max_wins():
    rows = [("m", "b", 0.9, "", "", "epoch"),
            ("m", "b", 0.7, "", "Kaggle Open Benchmarks", "kaggle")]
    d, _, _ = dedup(_scores(rows))
    assert d["feed"].tolist() == ["epoch"]
    d, _, _ = dedup(_scores([rows[0][:2] + (0.5,) + rows[0][3:], rows[1]]))
    assert d["feed"].tolist() == ["kaggle"]
