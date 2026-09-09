"""Validation, export, regression check and parity buckets on small frames."""

import pandas
import pytest

from benchmark_data import config, parity
from benchmark_data.check import compare_tables
from benchmark_data.steps.enrich import add_epoch_organizations, add_model_version
from benchmark_data.steps.export import export, export_views
from benchmark_data.steps.validate import ValidationError, validate
from benchmark_data.views import build_views

MODELS = pandas.DataFrame({"model_id": ["m1"], "base_model": ["x"], "reasoning_level": [""],
                           "reasoning_tokens": [""], "snapshot": [""], "variant": [""],
                           "model_version": ["x"], "organization": ["O"], "country": ["US"],
                           "publication_date": ["2025-01-01"], "training_flop": [""]})
BENCH = pandas.DataFrame({"benchmark_id": ["b1"], "name": ["B"], "category": ["C"], "floor": [0.0],
                          "ceiling": [""], "access": ["public"]})
SCORES = pandas.DataFrame({"model_id": ["m1"], "benchmark_id": ["b1"], "score": [0.5],
                           "stderr": [""], "harness": [""], "feed": ["epoch"],
                           "source_label": ["Paper"], "source_url": [""]})
HUMAN = pandas.DataFrame({"benchmark_id": ["b1"], "name": ["B"], "group": ["Average Human"],
                          "score": [0.9], "note": [""], "source": ["s"]})


@pytest.mark.parametrize("break_it, message", [
    (lambda s: pandas.concat([s, s]), "duplicated score"),
    (lambda s: s.assign(model_id="ghost"), "orphan model_id"),
    (lambda s: s.assign(benchmark_id="ghost"), "orphan benchmark_id"),
    (lambda s: s.assign(score=1.5), "score outside"),
])
def test_validate_names_the_broken_invariant(break_it, message):
    with pytest.raises(ValidationError, match=message):
        validate(MODELS, BENCH, break_it(SCORES), HUMAN)


def test_validate_checks_human_baselines_too():
    with pytest.raises(ValidationError, match="human"):
        validate(MODELS, BENCH, SCORES, HUMAN.assign(benchmark_id="ghost"))
    validate(MODELS, BENCH, SCORES, HUMAN)


def test_export_writes_every_table_and_view_with_the_declared_columns(tmp_path):
    export(MODELS, BENCH, SCORES, HUMAN, tmp_path / "db")
    export_views(build_views(MODELS, BENCH, SCORES, HUMAN), tmp_path / "views")
    for f, cols in (("models.csv", config.MODEL_COLS), ("benchmarks.csv", config.BENCH_COLS),
                    ("scores.csv", config.SCORE_COLS), ("human_baselines.csv", config.HUMAN_COLS)):
        assert list(pandas.read_csv(tmp_path / "db" / f).columns) == cols
    for f, cols in (("all_scores_flat.csv", config.ALL_SCORES_COLS),
                    ("dated_scores_flat.csv", config.ALL_SCORES_COLS),
                    ("human_baselines.csv", config.VIEW_HUMAN_COLS)):
        assert list(pandas.read_csv(tmp_path / "views" / f).columns) == cols
    flat = pandas.read_csv(tmp_path / "views" / "all_scores_flat.csv")
    assert flat["source"].tolist() == ["Paper"], "the fine source label reaches the view"


def test_compare_tables_describes_the_difference(tmp_path):
    now, ref = tmp_path / "now", tmp_path / "ref"
    export(MODELS, BENCH, SCORES, HUMAN, now)
    export(MODELS, BENCH, SCORES.assign(score=0.6), HUMAN, ref)
    diffs = compare_tables(now, ref)
    assert set(diffs) == {"scores.csv"} and "1 new row(s), 1 gone" in diffs["scores.csv"]
    assert compare_tables(now, now) == {}
    (now / "model_names.csv").write_text("model_id,feed,raw_name,n_records\n")
    assert compare_tables(now, ref) == {"scores.csv": diffs["scores.csv"],
                                        "model_names.csv": "present on one side only"}


def test_model_version_prefers_the_observed_spelling():
    models = MODELS.drop(columns="model_version")
    out = add_model_version(models, {("m1", "x-seen"): 3, ("m1", "x-rare"): 1})
    assert out["model_version"].tolist() == ["x-seen"]
    assert add_model_version(models, {})["model_version"].tolist() == ["x"], "reconstructed"


def test_epoch_organizations_fill_blanks_and_report_disagreements():
    models = pandas.concat([MODELS, MODELS.assign(model_id="m2", base_model="y", organization="",
                                                  country="")], ignore_index=True)
    epoch = pandas.DataFrame({"model_id": ["m1", "m2"], "date": ["", ""],
                              "organization": ["Other", "E"], "country": ["US", "FR"],
                              "flop": ["1e24", "2e24"]})
    out, diff = add_epoch_organizations(models, epoch)
    assert out.set_index("model_id").loc["m2", ["organization", "country"]].tolist() == ["E", "FR"]
    assert out.set_index("model_id")["training_flop"].tolist() == ["1e24", "2e24"], "FLOP filled"
    assert out.set_index("model_id").loc["m1", "organization"] == "O", "ours wins"
    assert diff["base_model"].tolist() == ["x"]


def test_parity_buckets_split_lost_pairs_by_cause():
    golden = pandas.DataFrame({
        "model_version": ["a", "b", "c", "d", "e"],
        "benchmark": ["Kept", "Gone", "Part", "Kept", "Kept"],
        "score": ["0.5", "0.5", "0.5", "0.5", "0.5"],
        "release_date": ["2025-01-01"] * 5,
    })
    view = pandas.DataFrame({
        "model_version": ["a", "e", "f"], "benchmark": ["Kept", "Kept", "Kept"],
        "score": ["0.5", "0.9", "0.1"], "release_date": ["2025-01-02", "2025-01-01", ""],
    })
    status = {"Kept": "included", "Gone": "excluded", "Part": "included"}
    res = parity.compare(golden, view, status, merged_parts={"Part"}, tol=1e-3)
    assert res["lost_excluded"]["model_version"].tolist() == ["b"]
    assert res["lost_merged_part"]["model_version"].tolist() == ["c"]
    assert res["lost_renamed_model"]["model_version"].tolist() == ["d"]
    assert res["lost_other"].empty and res["lost_unknown_benchmark"].empty
    assert res["new"]["model_version"].tolist() == ["f"]
    assert res["score_changed"]["model_version"].tolist() == ["e"]
    assert res["date_changed"]["model_version"].tolist() == ["a"]
