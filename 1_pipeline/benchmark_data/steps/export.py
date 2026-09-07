"""Write the tables (sorted, deterministic), the consumer views and the build manifest."""

import datetime
import hashlib
import json
import logging
import subprocess
from pathlib import Path

import pandas

import benchmark_data
from benchmark_data import config
from benchmark_data.identity import IDENT_COLS

log = logging.getLogger(__name__)

_SORT = {"models.csv": IDENT_COLS, "benchmarks.csv": ["name"],
         "scores.csv": ["benchmark_id", "model_id", "feed"],
         "human_baselines.csv": ["name", "group", "score", "source"],
         "model_names.csv": ["model_id", "feed", "raw_name"],
         "excluded_benchmarks.csv": ["name"]}


def model_names_table(raw_names) -> pandas.DataFrame:
    """(model_id, feed, raw name) -> count, every spelling a feed used for a model."""
    rows = [(m, f, n, c) for (m, f, n), c in raw_names.items()]
    return pandas.DataFrame(rows, columns=config.MODEL_NAMES_COLS)


def excluded_table(metadata_dir: Path, dropped) -> pandas.DataFrame:
    """Benchmarks kept out of the database, with the criterion, the records dropped and the note.

    Everything whose `status` is not `included` in benchmarks.csv: excluded, under review, or
    without a source today.
    """
    meta = pandas.read_csv(metadata_dir / config.BENCHMARKS_FILE, dtype=str).fillna("")
    out = meta[meta["status"] != config.STATUS_INCLUDED].copy()
    out["records_dropped"] = out["name"].map(dropped).fillna(0).astype(int)
    return out[config.EXCLUDED_COLS]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             cwd=config.ROOT, check=True, timeout=5)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def build_manifest(tables: dict[str, pandas.DataFrame], feed_dir: Path = config.FEED_DIR,
                   metadata_dir: Path = config.METADATA_DIR) -> dict:
    """What this build was made of: schema version, feeds (provenance), inputs' hashes, counts.

    The manifest carries a timestamp, so it sits outside the golden comparison.
    """
    provenance_file = feed_dir / "provenance.json"
    provenance = json.loads(provenance_file.read_text()) if provenance_file.exists() else {}
    inputs = sorted([*metadata_dir.glob("*.csv"), *feed_dir.glob("*/aliases.csv")])
    return {
        "schema_version": benchmark_data.SCHEMA_VERSION,
        "built_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "feeds": provenance,
        "inputs_sha256": {str(p.relative_to(config.ROOT)): _sha256(p) for p in inputs},
        "rows": {name: int(len(df)) for name, df in tables.items()},
    }


def export_views(views: dict[str, pandas.DataFrame], out_dir: Path = config.VIEWS_DIR) -> None:
    """Write the consumer views (already sorted by their builders)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in config.VIEW_FILES:
        views[name].fillna("").to_csv(out_dir / name, index=False, encoding="utf-8")
        log.info("3_views/%s: %s rows x %d columns", name, f"{len(views[name]):,}",
                 len(views[name].columns))


def export(models: pandas.DataFrame, benchmarks: pandas.DataFrame, scores: pandas.DataFrame,
           human: pandas.DataFrame, out_dir: Path = config.DATABASE_DIR,
           names: pandas.DataFrame | None = None, excluded: pandas.DataFrame | None = None,
           manifest: dict | None = None) -> None:
    """Write the tables given (the optional ones when provided) and the manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = [("models.csv", models, config.MODEL_COLS),
              ("benchmarks.csv", benchmarks, config.BENCH_COLS),
              ("scores.csv", scores, config.SCORE_COLS),
              ("human_baselines.csv", human, config.HUMAN_COLS)]
    if names is not None:
        tables.append(("model_names.csv", names, config.MODEL_NAMES_COLS))
    if excluded is not None:
        tables.append(("excluded_benchmarks.csv", excluded, config.EXCLUDED_COLS))
    for name, df, cols in tables:
        out = df[cols].sort_values(_SORT[name]).fillna("")
        out.to_csv(out_dir / name, index=False, encoding="utf-8")
        log.info("%s: %s rows x %d columns", name, f"{len(out):,}", len(out.columns))
    if manifest is not None:
        (out_dir / config.MANIFEST_FILE).write_text(json.dumps(manifest, indent=2,
                                                               ensure_ascii=False) + "\n")
