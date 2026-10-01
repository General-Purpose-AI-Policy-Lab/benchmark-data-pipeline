"""release_dates.csv overrides Epoch's dates (key base_model, snapshot, variant); model_metadata.csv
and dated siblings fill the gaps."""

import pandas
import pytest

from benchmark_data import config
from benchmark_data.steps.enrich import (
    add_benchmark_release_dates,
    add_epoch_model_metadata_dates,
    add_manual_dates,
    add_sibling_dates,
    load_epoch_benchmark_dates,
    load_epoch_model_metadata,
)

MODELS = pandas.DataFrame({
    "model_id": ["a", "b", "c", "d", "e"],
    "base_model": ["gpt-x", "gpt-x", "gpt-x", "other", "gpt-x"],
    "reasoning_level": ["", "high", "", "", ""],
    "snapshot": ["", "", "2025-01-01", "", ""],
    "variant": ["", "thinking", "", "", "Fine Tune"],
    "publication_date": ["2025-02-01", "2025-02-01", "2025-01-01", "", ""],
})


def _write(tmp_path, rows):
    header = "base_model,snapshot,variant,publication_date,source,note\n"
    (tmp_path / config.RELEASE_DATES_FILE).write_text(header + "".join(r + "\n" for r in rows))
    return tmp_path


def test_override_applies_to_every_effort_of_the_exact_snapshot(tmp_path):
    d = _write(tmp_path, ["gpt-x,,,2025-01-15,src,", "other,,,2024-12-31,src,",
                          "gpt-x,,Fine Tune,2025-03-01,src,"])
    out, (orphans, _) = add_manual_dates(MODELS, d)
    dates = dict(zip(out["model_id"], out["publication_date"], strict=True))
    assert dates == {"a": "2025-01-15", "b": "2025-01-15", "c": "2025-01-01", "d": "2024-12-31",
                     "e": "2025-03-01"}
    assert orphans == set()


def test_unmatched_row_is_reported_not_silent(tmp_path):
    d = _write(tmp_path, ["ghost,,,2025-01-15,src,", "gpt-x,2099-01-01,,2025-01-15,src,",
                          "gpt-x,,Ghost Tune,2025-01-15,src,"])
    out, (orphans, _) = add_manual_dates(MODELS, d)
    assert orphans == {"ghost", "gpt-x @2099-01-01", "gpt-x [Ghost Tune]"}
    assert out["publication_date"].tolist() == MODELS["publication_date"].tolist()


def test_duplicated_key_and_bad_date_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        dup = ["gpt-x,,,2025-01-15,s,", "gpt-x,,,2025-01-16,s,"]
        add_manual_dates(MODELS, _write(tmp_path, dup))
    with pytest.raises(ValueError):
        add_manual_dates(MODELS, _write(tmp_path, ["gpt-x,,,15/01/2025,s,"]))


def test_shipped_file_has_a_source_on_every_row():
    table = pandas.read_csv(config.METADATA_DIR / config.RELEASE_DATES_FILE, dtype=str).fillna("")
    assert (table["source"] != "").all(), table.loc[table["source"] == "", "base_model"].tolist()


def test_siblings_inherit_but_fine_tunes_and_disagreements_do_not():
    models = pandas.DataFrame({
        "model_id": list("abcdefg"),
        "base_model": ["m", "m", "m", "m", "n", "n", "n"],
        "snapshot": ["", "", "", "", "", "", ""],
        "variant": ["", "thinking", "thinking", "Fine Tune", "", "", "high-run"],
        "publication_date": ["2025-01-01", "", "", "", "2025-02-01", "2025-02-02", ""],
    })
    out, (left, _) = add_sibling_dates(models)
    dates = dict(zip(out["model_id"], out["publication_date"], strict=True))
    assert dates["b"] == dates["c"] == "2025-01-01"
    assert dates["d"] == "", "a named fine-tune never inherits"
    assert dates["g"] == "" and left == set(), "a named variant is not a run variant"
    models.loc[models["model_id"] == "g", "variant"] = ""
    out, (left, _) = add_sibling_dates(models)
    assert dict(zip(out["model_id"], out["publication_date"], strict=True))["g"] == ""
    assert left == {"n"}, "two dated siblings that disagree fill nothing and are reported"


def test_model_metadata_fills_only_undated_models(tmp_path):
    meta = tmp_path / "model_metadata.csv"
    meta.write_text("model_version,model_group,date,display_name,organization,country,"
                    "accessibility,training_compute_flop\n"
                    "gpt-x,GPT X,2024-12-31,GPT X,OpenAI,United States of America,,\n"
                    "gpt-x_high,GPT X,2024-12-30,GPT X,OpenAI,United States of America,,\n"
                    "other,Other,2024-06-01,Other,,,,\n")
    aliases = tmp_path / "aliases.csv"
    aliases.write_text("raw_name,base_model,reasoning_level,reasoning_tokens,snapshot,variant,harness,note\n")
    from benchmark_data.identity import model_id
    ident = {"base_model": "other", "reasoning_level": "", "reasoning_tokens": "", "snapshot": "",
             "variant": ""}
    models = pandas.DataFrame({
        "model_id": [model_id(ident), "x"],
        "base_model": ["other", "gpt-x"],
        "publication_date": ["", "2025-01-01"],
    })
    epoch = load_epoch_model_metadata(meta, aliases)
    assert epoch.set_index("model_id").loc[model_id(ident), "country"] == "", "no country given"
    out, _ = add_epoch_model_metadata_dates(models, epoch)
    assert out["publication_date"].tolist() == ["2024-06-01", "2025-01-01"]


def test_benchmark_dates_researched_win_over_epoch_and_gaps_are_reported(tmp_path):
    (tmp_path / config.BENCHMARK_RELEASE_DATES_FILE).write_text(
        "name,release_date,source,note\nB,2024-03-01,src,\nGhost,2024-01-01,src,\n")
    bench = pandas.DataFrame({"name": ["A", "B", "C"]})
    out, (orphans, undated) = add_benchmark_release_dates(
        bench, tmp_path, epoch={"A": "2023-01-01", "B": "2023-06-01"})
    assert out["release_date"].tolist() == ["2023-01-01", "2024-03-01", ""]
    assert orphans == {"Ghost"} and undated == {"C"}
    (tmp_path / config.BENCHMARK_RELEASE_DATES_FILE).write_text(
        "name,release_date,source,note\nB,03/2024,src,\n")
    with pytest.raises(ValueError, match="non-ISO"):
        add_benchmark_release_dates(bench, tmp_path, epoch={})


def test_epoch_benchmark_dates_match_by_file_live_task_or_exact_name(tmp_path):
    meta = tmp_path / "benchmark_metadata.csv"
    meta.write_text("benchmark,source_file,release_date\n"
                    "Aider polyglot,aider_polyglot_external.csv,2024-12-21\n"
                    "GPQA diamond,gpqa_diamond.csv,2023-11-20\n"
                    "CritPt,,2025-09-30\n"
                    "Blueprint-Bench 2,,2026-05-04\n"
                    "Unknown,,2020-01-01\n")
    assert load_epoch_benchmark_dates(meta) == {
        "Aider Polyglot": "2024-12-21", "GPQA Diamond": "2023-11-20", "CritPt": "2025-09-30",
        "BlueprintBench 2": "2026-05-04"}


def test_every_included_benchmark_has_a_release_date_with_a_source():
    meta = pandas.read_csv(config.METADATA_DIR / config.BENCHMARKS_FILE, dtype=str).fillna("")
    researched = pandas.read_csv(config.METADATA_DIR / config.BENCHMARK_RELEASE_DATES_FILE,
                                 dtype=str).fillna("")
    assert (researched["source"] != "").all()
    dated = set(researched["name"]) | set(load_epoch_benchmark_dates())
    included = set(meta.loc[meta["status"] == config.STATUS_INCLUDED, "name"])
    merged_parts = set(pandas.read_csv(config.METADATA_DIR / config.SIBLING_MERGES_FILE)["part"])
    assert included - merged_parts - dated == set()
