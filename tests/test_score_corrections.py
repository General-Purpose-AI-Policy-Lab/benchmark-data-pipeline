"""score_corrections.csv: a feed value is replaced (or dropped) only while the feed still carries
the value the correction was written against."""

from benchmark_data.sources import Record
from benchmark_data.sources.epoch_cyber import EPOCH_RESCALED
from benchmark_data.steps.ingest import _corrected, load_score_corrections


def _write(tmp_path, rows):
    (tmp_path / "score_corrections.csv").write_text(
        "feed,benchmark,raw_name,translated_score,corrected_score,source_url,note\n" + rows)
    return load_score_corrections(tmp_path)


def test_replaced_dropped_or_left_when_the_feed_moved(tmp_path):
    corr = _write(tmp_path, "f,B,m1,0.5,0.2,https://x,wrong metric\n"
                            "f,B,m2,0.9,,https://y,other setup\n")
    applied = set()
    fixed = _corrected(Record("m1", "B", 0.5), "f", corr, applied)
    assert fixed.score == 0.2 and fixed.source_url == "https://x"
    assert _corrected(Record("m2", "B", 0.9), "f", corr, applied) is None
    moved = Record("m1", "B", 0.55)                     # the feed changed the value: not applied
    assert _corrected(moved, "f", corr, set()) is moved
    other = Record("m1", "B", 0.5)
    assert _corrected(other, "g", corr, set()) is other  # another feed
    assert applied == {("f", "B", "m1"), ("f", "B", "m2")}


def test_shipped_corrections_load_and_cybergym_is_unscaled():
    corr = load_score_corrections()
    assert ("epoch_cyber", "CyberGym", "Claude Sonnet 4.5") in corr
    assert EPOCH_RESCALED == {"CyberGym": 0.95}
