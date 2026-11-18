"""score_drop_rules.csv: a type of run is dropped on a benchmark whatever its score, unless the
score clears the rule's `keep_at_or_above` or score_drop_kept.csv lists the run as read complete."""
from collections import Counter

from benchmark_data.sources import Record
from benchmark_data.steps.ingest import (
    _dropped_by_rule,
    load_score_drop_kept,
    load_score_drop_rules,
)


def _write(tmp_path, rows):
    (tmp_path / "score_drop_rules.csv").write_text(
        "rule,feeds,benchmark,raw_name_regex,keep_at_or_above,note\n" + rows)
    return load_score_drop_rules(tmp_path)


def test_rule_drops_the_run_type_and_keeps_high_scores(tmp_path):
    rules = _write(tmp_path, "cap,f|g,B,_(xhigh|max)$,0.95,cap\nall,f,C,^m,,every m run\n")
    hits = Counter()
    assert _dropped_by_rule(Record("m_max", "B", 0.8), "f", rules, hits)
    assert _dropped_by_rule(Record("m_xhigh", "B", 0.8), "g", rules, hits)
    assert not _dropped_by_rule(Record("m_max", "B", 0.97), "f", rules, hits)      # high enough
    assert not _dropped_by_rule(Record("m_high", "B", 0.5), "f", rules, hits)      # other effort
    assert not _dropped_by_rule(Record("m_max", "B", 0.5), "h", rules, hits)       # other feed
    assert not _dropped_by_rule(Record("m_max", "D", 0.5), "f", rules, hits)       # other benchmark
    # The effort a feed states outside the name counts too.
    assert _dropped_by_rule(Record("m", "B", 0.5, effort="max"), "f", rules, hits)
    assert _dropped_by_rule(Record("m1", "C", 0.99), "f", rules, hits)             # no keep bar
    assert hits == Counter({"cap": 3, "all": 1})


def test_shipped_rules_load():
    rules = load_score_drop_rules()
    assert {r.rule for r in rules} >= {"max-effort", "claude-high"}


def test_a_run_read_complete_keeps_against_a_rule(tmp_path):
    rules = _write(tmp_path, "cap,f|g,B,_max$,0.95,cap\n")
    (tmp_path / "score_drop_kept.csv").write_text(
        "feeds,benchmark,raw_name,score,source_url,note\nf,B,m_max,0.9,u,read\n")
    kept, hits, kept_hits = load_score_drop_kept(tmp_path), Counter(), set()
    assert not _dropped_by_rule(Record("m_max", "B", 0.9), "f", rules, hits, kept, kept_hits)
    assert kept_hits == {("B", "m_max", 0.9)}
    # Only the run that was read: another score, another feed or another name is still dropped.
    assert _dropped_by_rule(Record("m_max", "B", 0.8), "f", rules, hits, kept, kept_hits)
    assert _dropped_by_rule(Record("m_max", "B", 0.9), "g", rules, hits, kept, kept_hits)
    assert _dropped_by_rule(Record("n_max", "B", 0.9), "f", rules, hits, kept, kept_hits)
    assert hits == Counter({"cap": 3}) and len(kept_hits) == 1
    # A row no rule covers is never used, so the build can report it.
    assert not _dropped_by_rule(Record("m_high", "B", 0.9), "f", rules, hits, {("B", "m_high"): [
        (frozenset({"f"}), 0.9)]}, kept_hits)
    assert len(kept_hits) == 1


def test_shipped_kept_rows_are_each_covered_by_a_shipped_rule():
    rules, kept = load_score_drop_rules(), load_score_drop_kept()
    assert kept
    for (benchmark, name), rows in kept.items():
        for feeds, score in rows:
            for feed in feeds:
                rec = Record(name, benchmark, score)
                assert _dropped_by_rule(rec, feed, rules, Counter()), (benchmark, name)
                assert not _dropped_by_rule(rec, feed, rules, Counter(), kept, set())
