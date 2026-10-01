"""Dated build folders: the latest run is found by its name, other folders are ignored."""

import pytest

from benchmark_data import runs


def test_latest_is_the_most_recent_dated_folder(tmp_path):
    for name in ("20260908", "20261001", "20260930", "notes", "2026-10-02"):
        (tmp_path / name).mkdir()
    (tmp_path / "20261005").write_text("a file, not a run")
    assert runs.dates(tmp_path) == ["20260908", "20260930", "20261001"]
    assert runs.latest(tmp_path) == tmp_path / "20261001"


def test_no_run_is_an_explicit_error(tmp_path):
    assert runs.dates(tmp_path / "absent") == []
    with pytest.raises(FileNotFoundError, match="benchmark_data build"):
        runs.latest(tmp_path)


def test_today_names_a_folder():
    assert len(runs.today()) == 8 and runs.today().isdigit()
