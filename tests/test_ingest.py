"""Benchmark scope is applied at ingestion, from benchmarks.csv."""

import pytest

from benchmark_data import config
from benchmark_data.steps.ingest import load_benchmark_status


def test_every_included_benchmark_has_category_and_floor():
    import pandas
    table = pandas.read_csv(config.METADATA_DIR / config.BENCHMARKS_FILE, dtype=str).fillna("")
    included = table[table["status"] == config.STATUS_INCLUDED]
    for col in ("category", "floor"):
        missing = included.loc[included[col] == "", "name"].tolist()
        assert not missing, f"included benchmarks with an empty {col}: {missing}"


def test_status_vocabulary():
    statuses = set(load_benchmark_status().values())
    assert statuses <= {"included", "excluded", "review", "no_source"}, statuses


def test_duplicated_name_is_rejected(tmp_path):
    (tmp_path / config.BENCHMARKS_FILE).write_text("name,status\nA,included\nA,excluded\n")
    with pytest.raises(ValueError):
        load_benchmark_status(tmp_path)


def test_access_vocabulary():
    import pandas
    table = pandas.read_csv(config.METADATA_DIR / config.BENCHMARKS_FILE, dtype=str).fillna("")
    used = set(table["access"]) - {""}
    assert used <= config.ACCESS_CLASSES, used - config.ACCESS_CLASSES
    included = table[table["status"] == config.STATUS_INCLUDED]
    assert (included["access"] != "").all(), included.loc[included["access"] == "", "name"].tolist()
