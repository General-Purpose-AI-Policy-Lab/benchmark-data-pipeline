"""Human baselines: one row per published measurement, attached to the benchmark table.

The file `0_input/metadata/human_baselines.csv` is copied as is: no clipping (a 1.0 stays 1.0; a
consumer that needs 1 - epsilon clips downstream), no rounding, the figure as published, with
its source. Rows for a benchmark absent from the database (excluded, or never ingested) are
dropped and reported, never written.
"""

import logging
from pathlib import Path

import pandas

from benchmark_data import config

log = logging.getLogger(__name__)


def load_human_baselines(metadata_dir: Path = config.METADATA_DIR) -> pandas.DataFrame:
    """Read and check the file: known groups, scores in [0, 1], no duplicated measurement.

    Raises:
        ValueError: unknown group, score outside [0, 1], or the same (benchmark, group, source)
            twice.
    """
    table = pandas.read_csv(metadata_dir / config.HUMAN_BASELINES_FILE, dtype=str).fillna("")
    unknown = sorted(set(table["group"]) - set(config.HUMAN_GROUPS))
    if unknown:
        raise ValueError(f"human_baselines.csv: unknown group(s) {unknown}")
    score = pandas.to_numeric(table["score"], errors="coerce")
    if score.isna().any() or not score.between(0, 1).all():
        bad = table.loc[score.isna() | ~score.between(0, 1), "benchmark"].tolist()
        raise ValueError(f"human_baselines.csv: score missing or outside [0, 1] for {bad}")
    key = ["benchmark", "group", "source"]
    if table.duplicated(key).any():
        dups = table.loc[table.duplicated(key), key].to_records(index=False).tolist()
        raise ValueError(f"human_baselines.csv: duplicated measurement {dups}")
    table["score"] = score
    return table


def attach_human_baselines(table: pandas.DataFrame, benchmarks: pandas.DataFrame):
    """Join the benchmark ids; rows whose benchmark is not in the database are set aside.

    Returns:
        (baselines with `benchmark_id`, set of orphan benchmark names).
    """
    ids = benchmarks[["benchmark_id", "name"]]
    out = table.merge(ids, left_on="benchmark", right_on="name", how="left")
    orphans = set(out.loc[out["benchmark_id"].isna(), "benchmark"])
    if orphans:
        log.warning("human_baselines.csv: %d row(s) for benchmark(s) not in the database, "
                    "dropped: %s", int(out["benchmark_id"].isna().sum()), sorted(orphans))
    out = out[out["benchmark_id"].notna()]
    return out[config.HUMAN_COLS], orphans
