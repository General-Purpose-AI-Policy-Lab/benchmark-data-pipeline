"""score_drop_rules.csv: a type of run is dropped on a benchmark whatever its score, unless the
score clears the rule's `keep_at_or_above`."""
from collections import Counter

from benchmark_data.sources import Record
from benchmark_data.steps.ingest import _dropped_by_rule, load_score_drop_rules


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
