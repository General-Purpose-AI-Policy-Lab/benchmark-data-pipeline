"""Consumer views: flat files in the schemas the modelling repositories read today.

Views are derived from the four tables and never edited by hand. `all_scores_flat.csv` is every
score in Multiaxis_ECI's `benchmarks_merged.csv` schema, `dated_scores_flat.csv` keeps the scores
of dated models only (benchmark-forecasting's input), both with the benchmark floor as
`lower_bound` and its known `ceiling`; `human_baselines.csv` is the shared baseline schema.
"""

import pandas

from benchmark_data import config
from benchmark_data.views.all_scores_flat import build_all_scores_flat
from benchmark_data.views.dated_scores_flat import build_dated_scores_flat


def build_human_view(human: pandas.DataFrame) -> pandas.DataFrame:
    """Human baselines in the consumers' schema (`benchmark` instead of `benchmark_id, name`)."""
    return (human.rename(columns={"name": "benchmark"})[config.VIEW_HUMAN_COLS]
                 .sort_values(["benchmark", "group", "score"]).reset_index(drop=True))


def build_views(models: pandas.DataFrame, benchmarks: pandas.DataFrame, scores: pandas.DataFrame,
                human: pandas.DataFrame) -> dict[str, pandas.DataFrame]:
    """-> {file name: view}, in `config.VIEW_FILES` order."""
    return {"all_scores_flat.csv": build_all_scores_flat(models, benchmarks, scores),
            "dated_scores_flat.csv": build_dated_scores_flat(models, benchmarks, scores),
            "human_baselines.csv": build_human_view(human)}
