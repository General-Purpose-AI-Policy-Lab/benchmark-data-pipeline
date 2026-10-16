"""The lab's own runs (feed `gpai_runs`): every score row is recomputed from its run's samples."""

import hashlib
import json

import pandas
import pytest

from benchmark_data import config

FEED = config.FEED_DIR / "gpai_runs"
SCORES = pandas.read_csv(FEED / "scores.csv", dtype={"run_id": str})
RUN_IDS = sorted(SCORES["run_id"].unique())


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_scores_are_the_samples_summary(run_id):
    """score = mean credit over questions and epochs; stderr = sd of per-question means / sqrt(n).

    The credit of an answer is its correctness; a call without an answer (refused, or cut at
    max_tokens) is not scored and carries the expected credit the run's imputation gave it."""
    samples = pandas.read_csv(FEED / "runs" / run_id / "samples.csv")
    missing = samples["stop_reason"].isin(["refusal", "max_tokens"])  # no answer to score
    assert (samples.loc[~missing, "credit"] == samples.loc[~missing, "correct"]).all()
    assert (~samples.loc[missing, "correct"]).all()
    assert samples.loc[missing, "credit"].between(0, 1).all()
    for row in SCORES[SCORES["run_id"] == run_id].itertuples():
        s = samples[samples["subset"] == row.benchmark]
        assert s["stop_reason"].isin(["refusal", "max_tokens"]).mean() <= 0.30
        per_item = s.groupby("record_id")["credit"].mean()
        assert len(per_item) == row.n_items
        assert s["epoch"].nunique() == row.n_epochs
        assert s.groupby("record_id").size().eq(row.n_epochs).all()  # a full grid
        assert row.score == pytest.approx(per_item.mean(), abs=1e-6)
        assert row.stderr == pytest.approx(per_item.std(ddof=1) / len(per_item) ** 0.5, abs=1e-6)


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_manifest_matches_the_run_files(run_id):
    run = FEED / "runs" / run_id
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["run_id"] == run_id
    assert manifest["output_files"] == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(run.iterdir()) if p.name != "manifest.json"}
    for bench, res in manifest["results"].items():
        rows = SCORES[(SCORES["run_id"] == run_id) & (SCORES["benchmark"] == bench)]
        if bench in manifest["excluded_from_scores"]:  # refused too often: kept out on purpose
            assert rows.empty
            continue
        [row] = rows.itertuples()
        assert (row.score, row.stderr) == (res["score"], res["stderr"])


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_samples_carry_no_item_text(run_id):
    """GPQA-style benchmarks ask that items never appear in plain text: ids and outcomes only."""
    cols = set(pandas.read_csv(FEED / "runs" / run_id / "samples.csv", nrows=0).columns)
    assert not cols & {"question", "choices", "completion", "prompt"}
