"""`3_views/dated_scores_flat.csv`: the scores of dated models, benchmark-forecasting's schema.

Same columns as `all_scores_flat.csv` (floor as `lower_bound`, known `ceiling`); rows whose model
has no `publication_date` are left out and reported.
"""

import logging

import pandas

from benchmark_data import config
from benchmark_data.views.all_scores_flat import join_scores

log = logging.getLogger(__name__)


def build_dated_scores_flat(models: pandas.DataFrame, benchmarks: pandas.DataFrame,
                            scores: pandas.DataFrame) -> pandas.DataFrame:
    """Rows whose model has a `publication_date`.

    Sibling boards are already merged in the database (PRBench, SWE Atlas), so the view carries
    no merge option: the merged series is the only one there is.
    """
    out = join_scores(models, benchmarks, scores)
    undated = out["release_date"].fillna("") == ""
    if undated.any():
        log.info("dated_scores_flat: %d score(s) of undated models left out (%s)",
                 int(undated.sum()), sorted(set(out.loc[undated, "model_version"]))[:6])
    out = out[~undated].copy()
    coarse = out["feed"].map(config.FEED_LABEL)
    out["source"] = out["source_label"].where(out["source_label"] != "", coarse)
    return (out[config.DATED_SCORES_COLS].sort_values(["benchmark", "model_version"])
               .reset_index(drop=True))
