"""The full build: ingest -> dedup -> merge_siblings -> enrich -> human baselines -> validate
-> export (tables, then consumer views)."""

import logging
from pathlib import Path

import pandas

from benchmark_data import config, runs
from benchmark_data.steps.dedup import dedup
from benchmark_data.steps.enrich import enrich
from benchmark_data.steps.export import (
    build_manifest,
    excluded_table,
    export,
    export_views,
    model_names_table,
)
from benchmark_data.steps.human_baselines import attach_human_baselines, load_human_baselines
from benchmark_data.steps.ingest import ingest
from benchmark_data.steps.merge_siblings import load_sibling_merges, merge_siblings
from benchmark_data.steps.validate import validate
from benchmark_data.views import build_views

log = logging.getLogger(__name__)


def _log_disagreements(dups: pandas.DataFrame, models: pandas.DataFrame,
                       benchmarks: pandas.DataFrame) -> None:
    if not len(dups):
        return
    b = benchmarks.set_index("benchmark_id")["name"]
    m = models.set_index("model_id")["base_model"]
    table = (dups.head(12)
             .assign(model=lambda d: d["model_id"].map(m),
                     benchmark=lambda d: d["benchmark_id"].map(b))
             [["model", "benchmark", "n", "score_min", "score_max", "spread", "feeds"]])
    log.info("disagreements (first 12):\n%s", table.to_string(index=False))


def _log_below_floor(scores: pandas.DataFrame, benchmarks: pandas.DataFrame) -> None:
    """Scores under their benchmark's floor: kept as published, counted here for the record."""
    floor = benchmarks.set_index("benchmark_id")["floor"].map(pandas.to_numeric)
    name = benchmarks.set_index("benchmark_id")["name"]
    below = scores[scores["score"] < scores["benchmark_id"].map(floor)]
    if len(below):
        by_bench = below["benchmark_id"].map(name).value_counts().head(6).to_dict()
        log.info("%d score(s) below the benchmark floor (kept; chance-level or weaker models), "
                 "most on: %s", len(below), by_bench)
    else:
        log.info("no score below its benchmark floor")


def _log_new_models(new_names: list[dict], previous_models: Path) -> None:
    if previous_models.exists() and previous_models.stat().st_size:
        prev = set(pandas.read_csv(previous_models)["model_id"])
        fresh = [n for n in new_names if n["model_id"] not in prev]
        log.info("new models vs %s: %d", previous_models, len(fresh))
        for n in fresh[:20]:
            log.info("  %-11s %-45s %s", n["feed"], n["raw_name"], n["ident"])
    else:
        log.info("no previous %s: every model is new", previous_models)


def build(feed_dir: Path = config.FEED_DIR, metadata_dir: Path = config.METADATA_DIR,
          out_dir: Path | None = None, views_dir: Path | None = None) -> None:
    """Build the tables of `out_dir` and the views of `views_dir` from the feeds and metadata.

    By default both go to the folders of today's run, `2_database/<YYYYMMDD>/` and
    `3_views/<YYYYMMDD>/` (a rebuild the same day replaces them).
    """
    previous = runs.dates(config.DATABASE_DIR)
    previous_models = (config.DATABASE_DIR / previous[-1] / "models.csv" if previous
                       else config.DATABASE_DIR / "models.csv")
    date = runs.today()
    out_dir = out_dir or config.DATABASE_DIR / date
    views_dir = views_dir or config.VIEWS_DIR / date
    log.info("run %s: tables -> %s, views -> %s", date, out_dir, views_dir)
    result = ingest(feed_dir, metadata_dir)

    scores = pandas.DataFrame(result.scores, columns=config.SCORE_COLS)
    models = pandas.DataFrame(result.models.values())
    benchmarks = pandas.DataFrame(result.benchmarks.values())

    deduped, dups, n_exact = dedup(scores)
    n_disagree = int(dups["n"].sum() - len(dups)) if len(dups) else 0
    log.info("scores before %s -> after %s (%s exact duplicates + %s disagreements)",
             f"{len(scores):,}", f"{len(deduped):,}", f"{n_exact:,}", f"{n_disagree:,}")
    _log_disagreements(dups, models, benchmarks)

    merges = load_sibling_merges(metadata_dir)
    deduped, benchmarks = merge_siblings(deduped, benchmarks, merges)
    parts = {p for ps in merges.values() for p in ps}

    models, benchmarks = enrich(models, benchmarks, result.meta_obs, metadata_dir, parts,
                                result.names)

    human, _ = attach_human_baselines(load_human_baselines(metadata_dir), benchmarks)

    validate(models, benchmarks, deduped, human)
    _log_below_floor(deduped, benchmarks)
    log.info("OK: %s models, %s benchmarks, %s scores, %s human baselines",
             f"{len(models):,}", f"{len(benchmarks):,}", f"{len(deduped):,}", f"{len(human):,}")
    for feed, names in result.unmapped.items():
        log.info("unresolved [%s]: %s", feed, sorted(names) if names else "none")
    _log_new_models(result.new_names, previous_models)

    names = model_names_table(result.raw_names)
    excluded = excluded_table(metadata_dir, result.excluded)
    tables = {"models.csv": models, "benchmarks.csv": benchmarks, "scores.csv": deduped,
              "human_baselines.csv": human, "model_names.csv": names,
              "excluded_benchmarks.csv": excluded}
    export(models, benchmarks, deduped, human, out_dir, names, excluded,
           build_manifest(tables, feed_dir, metadata_dir))
    export_views(build_views(models, benchmarks, deduped, human), views_dir)
