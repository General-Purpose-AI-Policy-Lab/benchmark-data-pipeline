"""Each feed's translate() on a minimal synthetic feed: the Records it yields, and what it skips."""

import json

import pandas
import pytest

from benchmark_data.sources import epoch_live, epoch_zip, kaggle, rand, seal


def _epoch_file():
    """A FILE_SPEC entry with a unit divisor and no harness column, for a synthetic CSV."""
    for name, (bench, col, divisor) in epoch_zip.FILE_SPEC.items():
        if divisor == 1.0 and name not in epoch_zip.FILE_HARNESS_COLUMN:
            return name, bench, col
    raise AssertionError("no simple FILE_SPEC entry")


def test_epoch_zip_reads_score_effort_meta_and_source(tmp_path):
    name, bench, col = _epoch_file()
    d = tmp_path / "epoch"
    d.mkdir()
    pandas.DataFrame({
        "Model version": ["m-1_high", "m-2", None, "m-3"],
        col: [0.5, 0.25, 0.1, None],
        "Name": ["M 1 (high)", "M 2 (x-high)", "", "M 3"],
        "Release date": ["2025-01-01", "2025-02-02", "", ""],
        "Source": ["Paper A", "", "", ""],
        "Source link": ["https://a", "", "", ""],
    }).to_csv(d / name, index=False)
    (d / "aliases.csv").write_text("raw_name\n")
    recs = list(epoch_zip.translate(tmp_path))
    assert [r.raw_name for r in recs] == ["m-1_high", "m-2"], "blank name and blank score dropped"
    a, b = recs
    assert (a.benchmark, a.score, a.effort, a.source_label, a.source_url) == (
        bench, 0.5, "high", "Paper A", "https://a")
    assert a.meta["publication_date"] == "2025-01-01"
    assert b.effort == "xhigh" and b.source_label == epoch_zip.SOURCE_LABEL and b.source_url == ""


def test_epoch_zip_ignores_skipped_files_and_reports_unknown_ones(tmp_path, caplog):
    d = tmp_path / "epoch"
    d.mkdir()
    (d / next(iter(epoch_zip.FILE_SKIP))).write_text("a,b\n1,2\n")
    (d / "mystery_external.csv").write_text("a,b\n1,2\n")
    assert list(epoch_zip.translate(tmp_path)) == []
    assert "mystery_external.csv" in caplog.text


def test_epoch_live_guards_the_problem_set_version(tmp_path):
    task, (bench, prefix) = next((t, v) for t, v in epoch_live.LIVE_TASK_SPEC.items() if v[1])
    d = tmp_path / "epoch_live"
    d.mkdir()
    frame = pandas.DataFrame({
        "task": [task, task], "model": ["m-1", "m-2"], "mean_score": [0.3, 0.4],
        "stderr": [0.01, 0.02], "task version": [prefix + "x", prefix + "x"],
        "Version release date": ["2025-01-01", "2025-01-02"], "log viewer": ["https://log/1", ""],
    })
    frame.to_csv(d / "epoch_live_benchmarks.csv", index=False)
    recs = list(epoch_live.translate(tmp_path))
    assert [(r.raw_name, r.benchmark, r.score, r.source_url) for r in recs] == [
        ("m-1", bench, 0.3, "https://log/1"), ("m-2", bench, 0.4, "")]
    frame.loc[0, "task version"] = "other-set"
    frame.to_csv(d / "epoch_live_benchmarks.csv", index=False)
    with pytest.raises(ValueError):
        list(epoch_live.translate(tmp_path))


def test_kaggle_strips_default_tag_and_converts_the_interval(tmp_path):
    d = tmp_path / "kaggle"
    d.mkdir()
    for board in kaggle.KAGGLE_SPEC:
        (d / kaggle.board_filename(board)).write_text(json.dumps({"rows": []}))
    board, bench = next(iter(kaggle.KAGGLE_SPEC.items()))
    (d / kaggle.board_filename(board)).write_text(json.dumps({"rows": [
        {"modelVersionSlug": "m-1-default", "taskResults": [
            {"result": {"numericResult": {"value": 0.6, "hasConfidenceInterval": True,
                                          "confidenceInterval": 0.196}}}]},
        {"modelVersionSlug": "m-2", "taskResults": [{"result": {"numericResult": {}}}]},
    ]}))
    recs = list(kaggle.translate(tmp_path))
    assert len(recs) == 1
    r = recs[0]
    assert (r.raw_name, r.benchmark, r.score, r.harness) == ("m-1", bench, 0.6, kaggle.HARNESS)
    assert r.stderr == pytest.approx(0.1)
    assert board in r.source_label and r.source_url == kaggle.BOARD_URL.format(board)


def test_rand_melts_the_wide_table_and_skips_human_rows_and_na(tmp_path):
    d = tmp_path / "rand"
    d.mkdir()
    pandas.DataFrame({
        "Model": ["Human Baseline Description", "Human Baseline Score (%)", "GPT X", "Model Y"],
        "Bio: BenchA": ["experts", "80", "50", "N/A"],
        "Chem: BenchB": ["", "", "N/A", "12.5"],
    }).to_csv(d / "rand_benchmark_scores.csv", index=False)
    recs = list(rand.translate(tmp_path))
    assert sorted((r.raw_name, r.benchmark, r.score) for r in recs) == [
        ("GPT X", "BenchA", 0.5), ("Model Y", "BenchB", 0.125)]
    assert recs[0].source_url == rand.SOURCE_URL


def _seal_page(entries):
    payload = json.dumps({"entries": entries})
    return ('<html><script>self.__next_f.push([1,"'
            + payload.replace('"', '\\"') + '"])</script></html>')


def test_seal_entries_reads_the_streaming_chunks_not_the_table():
    entries = [{"model": "Opus X", "score": 42.5, "version": ""}, {"model": "GPT Y", "score": 7}]
    html = _seal_page(entries) + "<table><tr><td>stale</td></tr></table>"
    assert seal.seal_entries(html) == entries
    assert seal.seal_entries("<html>nothing</html>") == []


def test_seal_translate_scales_scores_and_skips_unknown_boards(tmp_path, caplog):
    d = tmp_path / "seal"
    d.mkdir()
    slug, bench = next(iter(seal.SEAL_SPEC.items()))
    (d / f"{slug}.html").write_text(_seal_page([{"model": "Opus X", "score": 42.5},
                                                {"model": "No score", "score": None}]))
    (d / "unknown_board.html").write_text(_seal_page([{"model": "Z", "score": 1}]))
    recs = list(seal.translate(tmp_path))
    assert [(r.raw_name, r.benchmark, r.score) for r in recs] == [("Opus X", bench, 0.425)]
    assert recs[0].source_url == seal.BOARD_URL.format(slug)
    assert "unknown_board" in caplog.text


def test_seal_translate_demands_the_pages(tmp_path):
    (tmp_path / "seal").mkdir()
    with pytest.raises(FileNotFoundError):
        list(seal.translate(tmp_path))


def test_epoch_cyber_reads_the_long_table_and_reports_unknown_benchmarks(tmp_path, caplog):
    from benchmark_data.sources import epoch_cyber
    d = tmp_path / "epoch_cyber"
    d.mkdir()
    bench = next(iter(epoch_cyber.CYBER_SPEC))
    pandas.DataFrame({
        "model_id": ["cyb_A", "cyb_B", "cyb_C"], "benchmark_id": ["cb1", "cb1", "cb9"],
        "performance": [0.25, None, 0.5], "benchmark": [bench, bench, "Mystery Range"],
        "Model": ["Model A", "Model B", "Model C"], "model_group": ["A", "B", "C"],
        "date": ["2025-01-01", "2025-02-01", "2025-03-01"],
    }).to_csv(d / epoch_cyber.FILE, index=False)
    recs = list(epoch_cyber.translate(tmp_path))
    assert [(r.raw_name, r.benchmark, r.score) for r in recs] == [("Model A", bench, 0.25)]
    assert recs[0].meta == {"publication_date": "2025-01-01"}
    assert recs[0].source_url == epoch_cyber.SOURCE_URL
    assert "Mystery Range" in caplog.text


def test_cybench_site_scales_percentages_and_labels_subsets(tmp_path):
    from benchmark_data.sources import cybench_site
    d = tmp_path / "cybench_site"
    d.mkdir()
    pandas.DataFrame({"Model": ["Model A ⁶", "Model B"], "Count": [35, 40],
                      "End-to-End % Solved": [96, None]}).to_csv(d / cybench_site.FILE, index=False)
    recs = list(cybench_site.translate(tmp_path))
    assert [(r.raw_name, r.benchmark, r.score) for r in recs] == [("Model A ⁶", "Cybench", 0.96)]
    assert "35/40 tasks" in recs[0].source_label
