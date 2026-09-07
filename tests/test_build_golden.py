"""The full build reproduces the blessed copy byte for byte, twice in a row."""

import filecmp

import pytest

from benchmark_data import config
from benchmark_data.build import build

pytestmark = pytest.mark.skipif(
    not list((config.FEED_DIR / "seal").glob("*.html")),
    reason="SEAL pages absent (fresh clone): run `python -m benchmark_data refresh`",
)


def test_build_matches_expected_and_is_deterministic(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    build(out_dir=first, views_dir=first / "views")
    build(out_dir=second, views_dir=second / "views")
    for f in config.TABLE_FILES:
        assert filecmp.cmp(first / f, config.EXPECTED_DIR / f, shallow=False), f"{f} != expected"
        assert filecmp.cmp(first / f, second / f, shallow=False), f"{f} not deterministic"
    for f in config.VIEW_FILES:
        assert filecmp.cmp(first / "views" / f, config.EXPECTED_VIEWS_DIR / f, shallow=False), f
        assert filecmp.cmp(first / "views" / f, second / "views" / f, shallow=False), f
