"""Consumer views are derived from the tables: same scores, consumer column names, dated rows."""

import pandas
import pytest

from benchmark_data import config
from benchmark_data.identity import IDENT_COLS, machine_name, split_name
from benchmark_data.views import build_views

MODELS = pandas.DataFrame({
    "model_id": ["m1", "m2"],
    "model_version": ["gpt-x_high", "ghost-1"],
    "organization": ["OpenAI", ""],
    "publication_date": ["2025-01-01", ""],
})
BENCHMARKS = pandas.DataFrame({
    "benchmark_id": ["b1"], "name": ["Bench"], "category": ["Mathematics"], "floor": [0.25],
    "ceiling": [0.85], "access": ["public"],
})
SCORES = pandas.DataFrame({
    "model_id": ["m1", "m2"], "benchmark_id": ["b1", "b1"], "score": [0.5, 0.4],
    "stderr": ["", 0.01], "harness": ["", ""], "feed": ["epoch", "seal"],
    "source_label": ["Paper", ""], "source_url": ["https://p", ""],
})
HUMAN = pandas.DataFrame({
    "benchmark_id": ["b1"], "name": ["Bench"], "group": ["Average Human"], "score": [0.9],
    "note": [""], "source": ["src"],
})


def test_all_scores_keeps_every_score_and_dated_scores_only_dated_ones():
    views = build_views(MODELS, BENCHMARKS, SCORES, HUMAN)
    flat, dated, human = (views["all_scores_flat.csv"], views["dated_scores_flat.csv"],
                          views["human_baselines.csv"])
    assert list(flat.columns) == config.ALL_SCORES_COLS
    assert list(dated.columns) == config.DATED_SCORES_COLS
    assert list(human.columns) == config.VIEW_HUMAN_COLS
    assert sorted(flat["source"]) == ["Paper", "Scale SEAL"], "fine label, else the feed's"
    assert flat["lower_bound"].tolist() == [0.25, 0.25] and flat["ceiling"].tolist() == [0.85, 0.85]
    assert dated["model_version"].tolist() == ["gpt-x_high"], "undated model left out"
    assert dated["lower_bound"].tolist() == [0.25] and dated["source"].tolist() == ["Paper"]
    assert human["benchmark"].tolist() == ["Bench"]


@pytest.mark.parametrize("name", [
    "gpt-4o-2024-08-06", "claude-opus-4-20250514_unknown", "claude-3-7-sonnet-20250219_16K",
    "o1-2024-12-17_medium", "kimi-k2-thinking", "gemini-2.5-flash_thinking", "grok-2",
])
def test_machine_name_inverts_split_name(name):
    assert machine_name(split_name(name)) == name


def test_reconstructed_names_split_back_to_their_identity():
    """For run variants with a full-date snapshot, machine_name is an exact inverse of split_name.

    Named fine-tunes (`Bio Llama`) and month-only snapshots (`2025-04`) are out of the grammar
    on purpose: their reconstructed name only has to be stable, not parseable.
    """
    models = pandas.read_csv(config.DATABASE_DIR / "models.csv", dtype=str).fillna("")
    in_grammar = (models["variant"].isin(config.RUN_VARIANTS)
                  & models["snapshot"].str.fullmatch(r"|\d{4}-\d{2}-\d{2}"))
    bad = [(r["model_version"], dict(r[IDENT_COLS])) for _, r in models[in_grammar].iterrows()
           if r["model_version"] == machine_name(dict(r[IDENT_COLS]))
           and split_name(r["model_version"]) != dict(r[IDENT_COLS])]
    assert not bad, bad[:5]
