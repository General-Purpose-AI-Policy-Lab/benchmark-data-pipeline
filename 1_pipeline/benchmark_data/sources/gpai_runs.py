"""Feed `gpai_runs`: the lab's own measurements, one row per (model, benchmark, run), frozen.

Each run has its folder `0_input/feed/gpai_runs/runs/<run_id>/` (manifest.json, samples.csv,
transcripts.zip), written by `evals/` from the raw API log; scores.csv carries its summary rows.
Model names are machine names (`claude-sonnet-5_none`), resolved by the grammar.
"""

from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.sources.record import Record

SOURCE_LABEL = "GPAI Policy Lab run {run_id} ({n_epochs} epochs x {n_items} questions)"
RUN_URL = ("https://github.com/General-Purpose-AI-Policy-Lab/benchmark-data-pipeline/tree/main/"
           "0_input/feed/gpai_runs/runs/{run_id}")


def translate(feed_dir: Path) -> Iterator[Record]:
    """One row of scores.csv = one score, with its clustered stderr."""
    runs = pandas.read_csv(feed_dir / "gpai_runs/scores.csv", dtype={"run_id": str})
    for row in runs.itertuples():
        yield Record(row.model, row.benchmark, float(row.score), float(row.stderr), "", "", {},
                     SOURCE_LABEL.format(run_id=row.run_id, n_epochs=row.n_epochs,
                                         n_items=row.n_items),
                     RUN_URL.format(run_id=row.run_id))
