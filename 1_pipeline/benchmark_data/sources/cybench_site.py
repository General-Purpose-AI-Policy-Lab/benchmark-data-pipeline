"""Cybench's own leaderboard (cybench.github.io), a frozen snapshot of 2026-09-07.

The site collects results the authors ran (HAL) and figures published in system and model cards,
some on subsets of the 40 tasks (35, 37 or 39). Epoch carries most of these rows; the snapshot
adds the ones Epoch has not picked up (Muse Spark, Claude Opus 4.7, Claude Mythos Preview). The
benchmark is saturated, so the file is not refreshed automatically: `refresh` only records its
provenance. The task count of each row is written into the source label.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

FILE = "cybench_leaderboard.csv"
BENCHMARK = "Cybench"
SCORE_COLUMN = "End-to-End % Solved"
SOURCE_URL = "https://cybench.github.io/"
SNAPSHOT = "2026-09-07"
TOTAL_TASKS = 40


def translate(feed_dir: Path) -> Iterator[Record]:
    """One row per model; footnote markers on names are stripped at resolution."""
    table = pandas.read_csv(feed_dir / "cybench_site" / FILE)
    score = pandas.to_numeric(table[SCORE_COLUMN], errors="coerce") / 100
    for i, raw in table["Model"].items():
        if pandas.isna(raw) or pandas.isna(score[i]):
            continue
        count = int(table["Count"][i])
        subset = f"{count}/{TOTAL_TASKS} tasks" if count != TOTAL_TASKS else "all 40 tasks"
        yield Record(raw, BENCHMARK, score[i], "", "", "", {},
                     f"Cybench leaderboard (cybench.github.io, snapshot {SNAPSHOT}; {subset})",
                     SOURCE_URL)
