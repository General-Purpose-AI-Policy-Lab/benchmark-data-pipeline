"""Regression test: `2_2_database/` against the blessed copy `tests/expected_database/`."""

import logging
from pathlib import Path

import pandas

from benchmark_data import config

log = logging.getLogger(__name__)


def compare_tables(now_dir: Path, ref_dir: Path, files=config.TABLE_FILES) -> dict[str, str]:
    """-> {file: description of the difference}, empty when the tables are identical."""
    diffs = {}
    for f in files:
        if not (now_dir / f).exists() and not (ref_dir / f).exists():
            continue
        if not (now_dir / f).exists() or not (ref_dir / f).exists():
            diffs[f] = "present on one side only"
            continue
        now = pandas.read_csv(now_dir / f, dtype=str).fillna("")
        ref = pandas.read_csv(ref_dir / f, dtype=str).fillna("")
        if now.equals(ref):
            continue
        cols_plus, cols_minus = set(now) - set(ref), set(ref) - set(now)
        common = sorted(set(now) & set(ref))
        added = len(now[common].merge(ref[common], how="left", indicator=True)
                    .query("_merge == 'left_only'"))
        gone = len(ref[common].merge(now[common], how="left", indicator=True)
                   .query("_merge == 'left_only'"))
        diffs[f] = (f"columns +{sorted(cols_plus) or 'none'} -{sorted(cols_minus) or 'none'}, "
                    f"{added} new row(s), {gone} gone")
    return diffs


def check(now_dir: Path = config.DATABASE_DIR, ref_dir: Path = config.EXPECTED_DIR,
          views_dir: Path = config.VIEWS_DIR, ref_views: Path = config.EXPECTED_VIEWS_DIR) -> bool:
    ok = True
    targets = (
        ("database", now_dir, ref_dir, config.TABLE_FILES,
         "cp 2_database/*.csv tests/expected_database/"),
        ("views", views_dir, ref_views, config.VIEW_FILES,
         "cp 3_views/*.csv tests/expected_views/"),
    )
    for label, now, ref, files, fix in targets:
        diffs = compare_tables(now, ref, files)
        for f in files:
            if f in diffs:
                log.error("DIFF %s/%s: %s. Intended? then: %s", label, f, diffs[f], fix)
            else:
                log.info("OK %s/%s: identical to the expected copy", label, f)
        ok = ok and not diffs
    return ok
