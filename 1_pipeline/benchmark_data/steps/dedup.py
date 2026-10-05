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


def drop_bare_copies(scores: pandas.DataFrame, models: pandas.DataFrame):
    """-> (scores without the copies, the dropped rows).

    Two scores equal to 1e-6 of one release (same base model and snapshot) on one benchmark, one
    of them naming no effort or an effort only the feed's hybrid-model convention gave (Epoch's
    `_unknown` read as thinking on a Claude hybrid, `effort_by_convention`), are one measurement
    counted twice: a feed carries the run unlabelled or by convention, another (or the same one)
    with the label its source states, as Epoch's cyber table beside its Cybench file, or Scale's
    RLI board beside Epoch's copy of it. One row is kept (user, 2026-10-05), by order of evidence:
    an effort the source states, then no effort, then an effort by convention; also when the two
    are separate runs whose scores agree, one release, one benchmark, one value being one data
    point. Rows of equal standing (two stated efforts that agree) are both kept, and scores of
    exactly 0 or 1 are left alone: equal floors and ceilings are no evidence of one run.
    """
    ident = models.set_index("model_id")[["base_model", "snapshot", "reasoning_level",
                                          "reasoning_tokens", "variant"]].fillna("")
    d = scores.join(ident, on="model_id")
    conv = d["effort_by_convention"].fillna(False).astype(bool) \
        if "effort_by_convention" in d else pandas.Series(False, index=d.index)
    bare = (d["reasoning_level"] == "") & (d["reasoning_tokens"] == "") & (d["variant"] == "")
    effort = ((d["reasoning_level"] != "") | (d["reasoning_tokens"] != "")) & \
        d["variant"].isin(["", "thinking"]) | (d["variant"] == "thinking")
    rank = pandas.Series(-1, index=d.index)
    rank[effort] = 2
    rank[bare] = 1
    rank[effort & conv] = 0
    key = ["base_model", "snapshot", "benchmark_id"]
    pool = d[(rank >= 0) & (d["score"] > 0) & (d["score"] < 1)].assign(rank=rank).reset_index()
    pairs = pool.merge(pool, on=key, suffixes=("", "_o"))
    pairs = pairs[(pairs["model_id"] != pairs["model_id_o"])
                  & ((pairs["score"] - pairs["score_o"]).abs() <= 1e-6)
                  & (pairs["rank"] < pairs["rank_o"])]
    hit = pairs["index"].unique()
    return scores.drop(index=hit), scores.loc[hit]
