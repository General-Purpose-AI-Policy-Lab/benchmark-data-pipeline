"""Feed `epoch_live`: `epoch.ai/data/benchmarks.csv`, Epoch's internal evaluations, versioned per task."""

import logging
from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.config import CLAUDE_HYBRID_BASES
from benchmark_data.identity import hybrid_mode
from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

# Dictionary: live-feed task -> (benchmark, required `task version` prefix or None).
# Every Epoch internal evaluation goes through here (one transport, no double counting).
# FrontierMath v1 / v2 are SEPARATE benchmarks: the v1 problem set was defective.
LIVE_TASK_SPEC = {
    'Chess Puzzles':                          ('Chess Puzzles', None),
    'EBR-bench':                              ('EBR-bench', None),
    'FrontierMath-2025-02-28-Private':        ('FrontierMath Tiers 1-3 v1', '1.'),
    'FrontierMath-Erdos':                     ('FrontierMath Erdos', None),
    'FrontierMath-Tier-4-2025-07-01-Private': ('FrontierMath Tier 4 v1', '1.'),
    'FrontierMath-Tier-4-v2-Private':         ('FrontierMath Tier 4 v2', '2.'),
    'FrontierMath-Tiers-1-3-v2-Private':      ('FrontierMath Tiers 1-3 v2', '2.'),
    'Furniture Assembly':                     ('Furniture Assembly', None),
    'GPQA diamond':                           ('GPQA Diamond', None),
    'MATH level 5':                           ('MATH Level 5', None),
    'MirrorCode':                             ('MirrorCode', None),
    'Mystery Game Puzzles':                   ('Mystery Game Puzzles', None),
    'OEIS Open':                              ('OEIS Open', None),
    'OEIS Open Lite':                         ('OEIS Open Lite', None),
    'OTIS Mock AIME 2024-2025':               ('OTIS Mock AIME 2024-2025', None),
    'SimpleQA Verified':                      ('SimpleQA Verified', None),
    'SWE-Bench verified':                     ('SWE-Bench Verified', None),
}

# Tasks set aside, with the reason.
LIVE_TASK_SKIP = {
    'FrontierMath-2025-02-28-Public':        '10-problem public split; the information would be manufactured by the clip at the bounds',
    'FrontierMath-Tier-4-2025-07-01-Public': '2-problem public split; only 3 distinct values',
    'SimpleQA Verified (anti-abstention)':   'protocol variant of SimpleQA Verified (abstention disallowed), same items; one series per benchmark',
}

if set(LIVE_TASK_SPEC) & set(LIVE_TASK_SKIP):
    raise ValueError("task in both LIVE_TASK_SPEC and LIVE_TASK_SKIP")


SOURCE_LABEL = "Epoch AI internal evaluation"


def translate(feed_dir: Path) -> Iterator[Record]:
    """One task = one benchmark; guard on the problem-set version.

    Raises:
        ValueError: a pinned task carries a `task version` from another problem set.
    """
    live = pandas.read_csv(feed_dir / "epoch_live/epoch_live_benchmarks.csv", low_memory=False)
    for task, sub in live.groupby("task"):
        if task in LIVE_TASK_SKIP:
            continue
        if task not in LIVE_TASK_SPEC:
            log.warning("epoch_live: ? task %r: in neither LIVE_TASK_SPEC nor LIVE_TASK_SKIP", task)
            continue
        bench, ver_prefix = LIVE_TASK_SPEC[task]
        ver = sub["task version"].dropna().astype(str)
        bad = sorted(set(ver[~ver.str.startswith(ver_prefix)])) if ver_prefix else []
        if bad:
            raise ValueError(f"{task}: unexpected problem-set version(s) {bad}")
        score = pandas.to_numeric(sub["mean_score"], errors="coerce")
        stderr = pandas.to_numeric(sub["stderr"], errors="coerce")
        url = (sub["log viewer"].fillna("").astype(str) if "log viewer" in sub.columns
               else pandas.Series("", index=sub.index))
        for i, raw in sub["model"].items():
            if pandas.isna(raw) or pandas.isna(score[i]):
                continue
            yield Record(raw, bench, score[i], stderr[i], "", "",
                         {"publication_date": sub["Version release date"][i]},
                         SOURCE_LABEL, url[i], hybrid_mode(raw, CLAUDE_HYBRID_BASES))
