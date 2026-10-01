"""Parity against the consumers' frozen outputs: every golden benchmark name must map, and the
differences must fall into the documented buckets."""

import pytest

from benchmark_data import config, parity, runs

pytestmark = pytest.mark.skipif(not runs.dates(config.VIEWS_DIR),
                                reason="3_views/ absent: run the build first")


@pytest.mark.parametrize("consumer", list(parity.GOLDENS))
def test_every_golden_benchmark_name_maps(consumer):
    res = parity.run(consumer)
    unknown = sorted(set(res["lost_unknown_benchmark"]["benchmark"]))
    assert not unknown, f"add previous_names for {unknown}"


@pytest.mark.parametrize("consumer", list(parity.GOLDENS))
def test_report_has_every_bucket(consumer):
    res = parity.run(consumer)
    text = parity.report(consumer, res, 0, 0)
    for bucket in ("lost_excluded", "lost_merged_part", "lost_renamed_model", "lost_other",
                   "new", "score_changed", "date_changed"):
        assert f"| {bucket} |" in text
