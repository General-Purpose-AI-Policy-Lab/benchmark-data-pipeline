"""Score deduplication: the same (model, benchmark) seen more than once.

Harnesses are not part of the model identity, so several harness runs of one model on one
benchmark collapse here to the best score; the `harness` column of the kept row says which.
Kaggle's independent re-runs are one such harness.
"""

import pandas


def dedup(scores: pandas.DataFrame):
    """-> (deduplicated scores, disagreement report, number of exact duplicates).

    Pass 1: exact duplicates on (model_id, benchmark_id, score rounded to 1e-9); the rounding
    matters: 2.502/100 (SEAL) != 0.02502 (ZIP) in the last bit.
    Pass 2: remaining disagreements -> the max score (best elicitation across harnesses, feeds
    and protocols). The winning row's `harness` and `feed` say where it came from.
    """
    key = ["model_id", "benchmark_id"]
    d = scores.assign(_k=scores["score"].round(9))
    n_exact = int(d.duplicated(key + ["_k"]).sum())
    d = d.drop_duplicates(key + ["_k"]).drop(columns="_k")

    report = (d.groupby(key)
               .agg(n=("score", "size"), score_min=("score", "min"), score_max=("score", "max"),
                    feeds=("feed", lambda s: ", ".join(sorted(set(s)))))
               .reset_index()
               .query("n > 1")
               .assign(spread=lambda r: r["score_max"] - r["score_min"])
               .sort_values(["spread", "model_id"], ascending=[False, True]))

    d = d.sort_values("score", na_position="first").drop_duplicates(key, keep="last")
    return d, report, n_exact
