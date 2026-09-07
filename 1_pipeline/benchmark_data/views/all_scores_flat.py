"""`3_views/all_scores_flat.csv`: one row per (model_version, benchmark), every score.

Multiaxis_ECI's `benchmarks_merged.csv` schema, plus `source_url`, the feed, and the benchmark's
floor (`lower_bound`) and known ceiling (`ceiling`, empty when none is established). `source` is
the fine label the feed publishes for the row (a leaderboard, a technical report), the feed's
name when it publishes none.
"""

import pandas

from benchmark_data import config


def join_scores(models: pandas.DataFrame, benchmarks: pandas.DataFrame,
                scores: pandas.DataFrame) -> pandas.DataFrame:
    """Scores with their model and benchmark columns; consumer names for the shared columns."""
    bench = benchmarks.rename(columns={"name": "benchmark", "floor": "lower_bound"})
    out = (scores.merge(models, on="model_id", how="left")
                 .merge(bench, on="benchmark_id", how="left"))
    return out.rename(columns={"publication_date": "release_date"})


def build_all_scores_flat(models: pandas.DataFrame, benchmarks: pandas.DataFrame,
                          scores: pandas.DataFrame) -> pandas.DataFrame:
    """Every score, dated or not; `source` is the feed's own label for the row (`source_label`)."""
    out = join_scores(models, benchmarks, scores)
    coarse = out["feed"].map(config.FEED_LABEL)
    out["source"] = out["source_label"].where(out["source_label"] != "", coarse)
    return (out[config.ALL_SCORES_COLS].sort_values(["benchmark", "model_version"])
               .reset_index(drop=True))
