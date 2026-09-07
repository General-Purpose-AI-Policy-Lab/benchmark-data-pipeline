"""Sibling boards averaged into one series (decision B6, 2026-09-04).

Scale publishes some benchmarks as several leaderboards built on the same task pool, rubric
and models (PRBench Finance / Legal, the three SWE Atlas boards). Kept apart they count the
same signal several times. Each group becomes one benchmark: the per-model mean of the boards
available for that model, after deduplication (so one score per model per board).
"""

import logging
from pathlib import Path

import numpy
import pandas

from benchmark_data import config
from benchmark_data.identity import benchmark_id

log = logging.getLogger(__name__)


def load_sibling_merges(metadata_dir: Path = config.METADATA_DIR) -> dict[str, list[str]]:
    """sibling_merges.csv (merged_name, part) -> {merged_name: [parts]}, in file order."""
    path = metadata_dir / config.SIBLING_MERGES_FILE
    if not path.exists():
        return {}
    table = pandas.read_csv(path, dtype=str).fillna("")
    if table["part"].duplicated().any():
        raise ValueError(f"{path.name}: a board can only belong to one merged series")
    return {m: g["part"].tolist() for m, g in table.groupby("merged_name", sort=False)}


def _combine_stderr(s: pandas.Series) -> float | str:
    """Standard error of a mean of independent measurements: sqrt(sum se^2) / n, '' if none."""
    se = pandas.to_numeric(s, errors="coerce").dropna()
    return float(numpy.sqrt((se ** 2).sum()) / len(s)) if len(se) == len(s) and len(se) else ""


def merge_siblings(scores: pandas.DataFrame, benchmarks: pandas.DataFrame,
                   merges: dict[str, list[str]]):
    """Replace each group of part benchmarks by one merged series.

    Args:
        scores: deduplicated scores (one row per model_id, benchmark_id).
        benchmarks: benchmark table with `benchmark_id`, `name`.
        merges: {merged_name: [part names]}.

    Returns:
        (scores, benchmarks) with the parts removed and the merged series added. Parts absent
        from the data are ignored; a group with no part present adds nothing.
    """
    name_of = dict(zip(benchmarks["benchmark_id"], benchmarks["name"], strict=True))
    id_of = {v: k for k, v in name_of.items()}
    scores, benchmarks = scores.copy(), benchmarks.copy()
    for merged, parts in merges.items():
        part_ids = [id_of[p] for p in parts if p in id_of]
        if not part_ids:
            continue
        sub = scores[scores["benchmark_id"].isin(part_ids)]
        agg = (sub.groupby("model_id", sort=True)
                  .agg(score=("score", "mean"), stderr=("stderr", _combine_stderr),
                       harness=("harness", lambda h: " / ".join(sorted({x for x in h if x}))),
                       feed=("feed", "first"),
                       source_label=("source_label",
                                     lambda s: " / ".join(sorted({x for x in s if x}))),
                       source_url=("source_url", lambda s: " ".join(sorted({x for x in s if x}))),
                       n_boards=("benchmark_id", "nunique"))
                  .reset_index())
        mid = benchmark_id(merged)
        agg["benchmark_id"] = mid
        counts = agg["n_boards"].value_counts().sort_index(ascending=False).to_dict()
        log.info("%s: %d rows on %d boards -> %d merged models (boards per model: %s)",
                 merged, len(sub), len(part_ids), len(agg), counts)
        scores = pandas.concat([scores[~scores["benchmark_id"].isin(part_ids)],
                                agg[config.SCORE_COLS]], ignore_index=True)
        benchmarks = pandas.concat([benchmarks[~benchmarks["benchmark_id"].isin(part_ids)],
                                    pandas.DataFrame([{"benchmark_id": mid, "name": merged}])],
                                   ignore_index=True)
    return scores, benchmarks
