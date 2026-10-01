"""Human baselines are copied as published and attached to the benchmark table."""

import pandas
import pytest

from benchmark_data import config, runs
from benchmark_data.steps.human_baselines import attach_human_baselines, load_human_baselines

HEADER = "benchmark,group,score,note,source\n"


def _write(tmp_path, body):
    (tmp_path / config.HUMAN_BASELINES_FILE).write_text(HEADER + body)
    return tmp_path


def test_values_are_kept_as_published_and_orphans_are_set_aside(tmp_path):
    d = _write(tmp_path, "A,Average Human,1.0,panel,src\nA,Domain Expert,0.5275,mean,src\n"
                         "Ghost,Top Performer,0.9,,src\n")
    table = load_human_baselines(d)
    benchmarks = pandas.DataFrame({"benchmark_id": ["id-a"], "name": ["A"]})
    out, orphans = attach_human_baselines(table, benchmarks)
    assert out["score"].tolist() == [1.0, 0.5275], "no clip, no rounding"
    assert out["benchmark_id"].tolist() == ["id-a", "id-a"]
    assert orphans == {"Ghost"}


def test_two_measurements_of_one_group_are_two_rows(tmp_path):
    d = _write(tmp_path, "A,Domain Expert,0.812,paper,src1\nA,Domain Expert,0.697,openai,src2\n")
    assert len(load_human_baselines(d)) == 2


@pytest.mark.parametrize("body", [
    "A,Expert,0.5,,src\n",                        # unknown group
    "A,Average Human,1.2,,src\n",                 # outside [0, 1]
    "A,Average Human,,,src\n",                    # missing
    "A,Average Human,0.5,,src\nA,Average Human,0.6,,src\n",  # same measurement twice
])
def test_bad_files_are_rejected(tmp_path, body):
    with pytest.raises(ValueError):
        load_human_baselines(_write(tmp_path, body))


def test_shipped_file_matches_the_database():
    table = load_human_baselines()
    benchmarks = runs.latest(config.DATABASE_DIR) / "benchmarks.csv"
    names = set(pandas.read_csv(benchmarks, dtype=str)["name"])
    assert set(table["benchmark"]) <= names, sorted(set(table["benchmark"]) - names)
    assert (table["source"] != "").all()
