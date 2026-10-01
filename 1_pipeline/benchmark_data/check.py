"""Regression test: the latest `2_database/<date>/` and `3_views/<date>/` against their blessed
copies under `tests/`."""

import logging
from pathlib import Path

import pandas

from benchmark_data import config, runs

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


def _shown(path: Path) -> Path:
    """`path` relative to the repository when it lies inside it (for the re-bless command)."""
    return path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path


def check(now_dir: Path | None = None, ref_dir: Path = config.EXPECTED_DIR,
          views_dir: Path | None = None, ref_views: Path = config.EXPECTED_VIEWS_DIR) -> bool:
    """Compare a build (by default the latest run) with the blessed copies."""
    now_dir = now_dir or runs.latest(config.DATABASE_DIR)
    views_dir = views_dir or runs.latest(config.VIEWS_DIR)
    log.info("checking %s and %s", now_dir, views_dir)
    ok = True
    targets = (
        ("database", now_dir, ref_dir, config.TABLE_FILES,
         f"cp {_shown(now_dir)}/*.csv tests/expected_database/"),
        ("views", views_dir, ref_views, config.VIEW_FILES,
         f"cp {_shown(views_dir)}/*.csv tests/expected_views/"),
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
