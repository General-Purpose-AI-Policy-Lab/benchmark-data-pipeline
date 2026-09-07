"""Pass 1: for each feed, load, translate, resolve the model name, stack the score.

Benchmark scope is decided here, as early as possible: a record on a benchmark whose `status`
in benchmarks.csv is not `included` is counted and dropped, so no model seen only there ever
needs a release date or an alias.
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas

from benchmark_data import config
from benchmark_data.identity import (
    IDENT_COLS,
    benchmark_id,
    load_aliases,
    model_id,
    resolve_model,
    strip_name,
)
from benchmark_data.sources import TRANSLATE, Record

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """What pass 1 produces, before deduplication.

    Attributes:
        models: model_id -> {model_id, *IDENT_COLS}.
        benchmarks: benchmark_id -> {benchmark_id, name}.
        scores: one row per measurement (SCORE_COLS), duplicates included.
        meta_obs: (model_id, publication_date, training_flop) gleaned from the feeds.
        unmapped: feed -> unresolved names (reported, never guessed).
        dropped: feed -> names explicitly dropped (alias with an empty base_model).
        excluded: benchmark -> number of records dropped because its status is not `included`.
        new_names: one entry per model created (feed, raw_name, model_id, ident).
        names: (model_id, machine name) -> count, for names the grammar parsed without an alias.
        raw_names: (model_id, feed, raw name) -> count, every spelling seen (`model_names.csv`).
        completed: variants whose effort was completed from a displayed name.
    """

    models: dict[str, dict] = field(default_factory=dict)
    benchmarks: dict[str, dict] = field(default_factory=dict)
    scores: list[dict] = field(default_factory=list)
    meta_obs: list[dict] = field(default_factory=list)
    unmapped: dict[str, set] = field(default_factory=dict)
    dropped: dict[str, set] = field(default_factory=dict)
    excluded: Counter = field(default_factory=Counter)
    new_names: list[dict] = field(default_factory=list)
    completed: Counter = field(default_factory=Counter)
    names: Counter = field(default_factory=Counter)
    raw_names: Counter = field(default_factory=Counter)


def load_benchmark_status(metadata_dir: Path = config.METADATA_DIR) -> dict[str, str]:
    """benchmarks.csv -> {name: status}."""
    table = pandas.read_csv(metadata_dir / config.BENCHMARKS_FILE, dtype=str).fillna("")
    if table["name"].duplicated().any():
        raise ValueError(f"duplicated name in {config.BENCHMARKS_FILE}")
    return dict(zip(table["name"], table["status"], strict=True))


def _take(result: IngestResult, feed: str, rec: Record, aliases: dict) -> str | None:
    """Resolve the name, create model / benchmark as needed, stack the score. -> model_id or None.

    `effort` (read from Epoch's displayed `Name`) only completes an identity with no known
    effort; variant='thinking' is left alone, its machine name already stated its configuration.
    """
    status, ident, alias_harness = resolve_model(rec.raw_name, aliases, config.SPLITTABLE[feed])
    if status != "ok":
        bucket = result.unmapped if status == "unmapped" else result.dropped
        bucket[feed].add(strip_name(rec.raw_name))
        return None
    if (rec.effort and not ident["reasoning_level"] and not ident["reasoning_tokens"]
            and ident["variant"] != "thinking"):
        result.completed[ident["variant"] or "bare"] += 1
        ident = {**ident, "reasoning_level": rec.effort,
                 "variant": "" if ident["variant"] == "unknown-effort" else ident["variant"]}
    mid = model_id(ident)
    name = strip_name(rec.raw_name)
    result.raw_names[(mid, feed, name)] += 1
    if config.SPLITTABLE[feed] and name not in aliases and not rec.effort:
        result.names[(mid, name.split("/", 1)[1] if name.count("/") == 1 else name)] += 1
    if mid not in result.models:
        result.models[mid] = {"model_id": mid, **ident}
        result.new_names.append({"feed": feed, "raw_name": strip_name(rec.raw_name),
                                 "model_id": mid, "ident": tuple(ident[c] for c in IDENT_COLS)})
    bid = benchmark_id(rec.benchmark)
    result.benchmarks.setdefault(bid, {"benchmark_id": bid, "name": rec.benchmark})
    stderr = "" if rec.stderr == "" or pandas.isna(rec.stderr) else float(rec.stderr)
    result.scores.append({"model_id": mid, "benchmark_id": bid, "score": float(rec.score),
                          "stderr": stderr, "harness": rec.harness or alias_harness, "feed": feed,
                          "source_label": rec.source_label, "source_url": rec.source_url})
    return mid


def _check_unit_range(result: IngestResult, feed: str) -> None:
    """A score is a proportion; anything else is a spec error.

    Raises:
        ValueError: a score of the feed falls outside [0, 1].
    """
    got = [r["score"] for r in result.scores if r["feed"] == feed]
    bad = [s for s in got if not 0 <= s <= 1]
    if bad:
        raise ValueError(f"{feed}: {len(bad)} score(s) outside [0,1], e.g. {bad[:3]}")
    log.info("%s: %s scores, all in [0, 1]", feed, f"{len(got):,}")


def ingest(feed_dir: Path = config.FEED_DIR,
           metadata_dir: Path = config.METADATA_DIR) -> IngestResult:
    """Single loop over the feeds, in `config.SOURCE_ORDER`.

    Raises:
        ValueError: a source has no translate function, or a benchmark named by a source has no
            row in benchmarks.csv (every benchmark must be listed, with a status).
    """
    if set(TRANSLATE) != set(config.SOURCE_ORDER):
        raise ValueError("every feed needs a translate function and a position in SOURCE_ORDER")
    status = load_benchmark_status(metadata_dir)
    aliases = {s: load_aliases(feed_dir / s / "aliases.csv") for s in config.SOURCE_ORDER}
    result = IngestResult(unmapped={s: set() for s in config.SOURCE_ORDER},
                          dropped={s: set() for s in config.SOURCE_ORDER})
    unknown_benchmarks: set[str] = set()
    for feed in config.SOURCE_ORDER:
        log.info("%s:", feed)
        for rec in TRANSLATE[feed](feed_dir):
            if rec.benchmark not in status:
                unknown_benchmarks.add(rec.benchmark)
                continue
            if status[rec.benchmark] != config.STATUS_INCLUDED:
                result.excluded[rec.benchmark] += 1
                continue
            mid = _take(result, feed, rec, aliases[feed])
            if mid and rec.meta:
                result.meta_obs.append({"model_id": mid, **rec.meta})
        _check_unit_range(result, feed)
    if unknown_benchmarks:
        raise ValueError(f"benchmarks with no row in {config.BENCHMARKS_FILE}: "
                         f"{sorted(unknown_benchmarks)}")
    if result.excluded:
        log.info("excluded benchmarks (records dropped): %s", dict(result.excluded))
    if result.completed:
        log.info("efforts completed from `Name`: %s", dict(result.completed))
    drops = {f: sorted(d) for f, d in result.dropped.items() if d}
    log.info("explicit DROPs: %s", drops or "none")
    return result
