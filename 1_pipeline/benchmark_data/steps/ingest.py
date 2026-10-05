"""Pass 1: for each feed, load, translate, resolve the model name, stack the score.

Benchmark scope is decided here, as early as possible: a record on a benchmark whose `status`
in benchmarks.csv is not `included` is counted and dropped, so no model seen only there ever
needs a release date or an alias.
"""

import logging
import re
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
    normalize,
    resolve_model,
    split_name,
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


def _take(result: IngestResult, feed: str, rec: Record, aliases: dict,
          fixes: dict | None = None, fixed: set | None = None) -> str | None:
    """Resolve the name, create model / benchmark as needed, stack the score. -> model_id or None.

    `effort` (read from Epoch's displayed `Name`) only completes an identity with no known
    effort; variant='thinking' is left alone, its machine name already stated its configuration.
    `fixes` (score_variant_fixes.csv) then moves one score to the effort its source states, or
    drops it as a copy of a labelled score; applied keys are added to `fixed`.
    """
    status, ident, alias_harness = resolve_model(rec.raw_name, aliases, config.SPLITTABLE[feed])
    if status != "ok":
        bucket = result.unmapped if status == "unmapped" else result.dropped
        bucket[feed].add(strip_name(rec.raw_name))
        return None
    if (rec.effort and not ident["reasoning_level"] and not ident["reasoning_tokens"]
            and ident["variant"] != "thinking"):
        result.completed[ident["variant"] or "bare"] += 1
        ident = {**ident, "reasoning_level": rec.effort}
    by_convention = False
    if rec.mode and not (ident["reasoning_level"] or ident["reasoning_tokens"] or ident["variant"]):
        # the source's convention for a hybrid model (`config.CLAUDE_HYBRID_BASES`)
        ident = ({**ident, "variant": "thinking"} if rec.mode == "thinking"
                 else {**ident, "reasoning_level": "none"})
        by_convention = True
    suffix, spelled_as = "", ""
    if fixes:
        fix = _variant_fix(fixes, feed, rec, model_id(ident))
        if fix is not None:
            fixed.add(fix.key)
            if fix.fix == "drop":
                return None
        if fix is not None and fix.fix == "remodel":
            ident, spelled_as = normalize(split_name(fix.new_model)), fix.new_model
            by_convention = False
        elif fix is not None:
            ident, suffix = _with_effort(ident, fix.suffix), fix.suffix
            by_convention = False
    mid = model_id(ident)
    name = strip_name(rec.raw_name)
    result.raw_names[(mid, feed, name)] += 1
    if config.SPLITTABLE[feed] and name not in aliases and not rec.effort and not rec.mode:
        spelled = name.split("/", 1)[1] if name.count("/") == 1 else name
        # A relabelled run votes for its bare spelling plus the effort it was moved to, so it
        # does not lend the bare model's name to another identity.
        if suffix:
            spelled = re.sub(r"_unknown$", "", spelled) + suffix
        result.names[(mid, spelled_as or spelled)] += 1
    if mid not in result.models:
        result.models[mid] = {"model_id": mid, **ident}
        result.new_names.append({"feed": feed, "raw_name": strip_name(rec.raw_name),
                                 "model_id": mid, "ident": tuple(ident[c] for c in IDENT_COLS)})
    bid = benchmark_id(rec.benchmark)
    result.benchmarks.setdefault(bid, {"benchmark_id": bid, "name": rec.benchmark})
    stderr = "" if rec.stderr == "" or pandas.isna(rec.stderr) else float(rec.stderr)
    result.scores.append({"model_id": mid, "benchmark_id": bid, "score": float(rec.score),
                          "stderr": stderr, "harness": rec.harness or alias_harness, "feed": feed,
                          "source_label": rec.source_label, "source_url": rec.source_url,
                          "effort_by_convention": by_convention})
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


def _report_unused_aliases(result: IngestResult, aliases: dict[str, dict]) -> None:
    """Alias rows whose identity produced no model: the raw name only occurs on excluded
    benchmarks, or the row is stale (a spelling the feed no longer uses). Reported, not fatal."""
    for feed, table in aliases.items():
        unused = []
        for raw in table:
            status, ident, _ = resolve_model(raw, table, False)
            if status == "ok" and model_id(ident) not in result.models:
                unused.append(raw)
        if unused:
            log.info("%s: %d alias row(s) whose identity produced no model (excluded benchmarks "
                     "only, or stale): %s%s", feed, len(unused), sorted(unused)[:10],
                     " ..." if len(unused) > 10 else "")


def load_score_corrections(metadata_dir: Path = config.METADATA_DIR) -> dict:
    """(feed, benchmark, raw_name) -> row of score_corrections.csv: a feed value known to be wrong
    (the wrong metric, a misread figure), replaced by the published one with its source; an empty
    `corrected_score` drops the row (no comparable value is published).
    `translated_score` is the value as the feed's translator yields it (after any rescale it
    undoes), so a correction stops applying, and is reported, as soon as the feed changes it."""
    path = metadata_dir / config.SCORE_CORRECTIONS_FILE
    if not path.exists():
        return {}
    table = pandas.read_csv(path, dtype={"feed": str, "benchmark": str, "raw_name": str})
    return {(r.feed, r.benchmark, r.raw_name): r for r in table.itertuples()}


def _corrected(rec: Record, feed: str, corrections: dict, applied: set) -> Record | None:
    """`rec` with its corrected score (None when the correction drops it), when the feed still
    carries the value the correction was written against; a correction whose feed value has moved
    is left unapplied (and reported)."""
    key = (feed, rec.benchmark, str(rec.raw_name))
    row = corrections.get(key)
    if row is None or abs(float(rec.score) - float(row.translated_score)) > 1e-6:
        return rec
    applied.add(key)
    if pandas.isna(row.corrected_score):
        return None
    return rec._replace(score=float(row.corrected_score), source_url=row.source_url)


def load_score_variant_fixes(metadata_dir: Path = config.METADATA_DIR) -> dict:
    """(feed, benchmark, model_id) -> rows of score_variant_fixes.csv: one score whose run named no
    effort although its source states it (`fix` = relabel, `suffix` the effort in machine-name
    grammar: `_none`, `_high`, `_thinking`, `_16K`), or that copies a labelled score of the same
    model already in the data (`fix` = drop), or that belongs to another model than its name says
    (`fix` = remodel, `new_model` the machine name of the model it moves to: an API alias such as
    `deepseek-chat` serves a different release over time). `model_id` is the score's identity
    before the fix
    (`model_version` is there for the reader), and `score` the value it carries, so a fix stops
    applying, and is reported, as soon as the feed changes that value. An empty `score` matches
    every value: a benchmark whose published score is a mean of several feed records (SWE Atlas,
    the mean of its sub-boards) has no record carrying it."""
    path = metadata_dir / config.SCORE_VARIANT_FIXES_FILE
    if not path.exists():
        return {}
    table = pandas.read_csv(path, dtype={"feed": str, "benchmark": str, "model_id": str,
                                         "suffix": str, "new_model": str})
    if "new_model" not in table:
        table["new_model"] = ""
    table = table.fillna({"suffix": "", "new_model": ""})
    bad = table[~table["fix"].isin(["relabel", "drop", "remodel"])
                | ((table["fix"] == "relabel") & ~table["suffix"].map(_effort_suffix_ok))
                | ((table["fix"] == "remodel") & (table["new_model"] == ""))]
    if len(bad):
        raise ValueError(f"{config.SCORE_VARIANT_FIXES_FILE}: bad fix or suffix in rows "
                         f"{bad.index.tolist()}")
    out: dict = {}
    for r in table.itertuples():
        key = (r.feed, r.benchmark, r.model_id,
               None if pandas.isna(r.score) else float(r.score))
        out.setdefault(key[:3], []).append(_Fix(key, r.fix, r.suffix, r.new_model))
    return out


@dataclass(frozen=True)
class _Fix:
    key: tuple
    fix: str
    suffix: str
    new_model: str = ""


def _effort_suffix_ok(suffix: str) -> bool:
    """A suffix the machine-name grammar reads as an effort, a budget or thinking."""
    ident = split_name("x" + suffix) if suffix.startswith("_") else {}
    return any(ident.get(c) for c in ("reasoning_level", "reasoning_tokens", "variant"))


def _with_effort(ident: dict, suffix: str) -> dict:
    """`ident` with the effort fields `suffix` states (the rest of the identity kept)."""
    eff = split_name("x" + suffix)
    return normalize({**ident, **{c: eff[c] for c in ("reasoning_level", "reasoning_tokens",
                                                      "variant")}})


def _variant_fix(fixes: dict, feed: str, rec: Record, mid: str):
    """The fix written against this score, if the feed still carries its value."""
    for fix in fixes.get((feed, rec.benchmark, mid), ()):
        if fix.key[3] is None or abs(float(rec.score) - fix.key[3]) <= 1e-6:
            return fix
    return None


def load_score_drop_rules(metadata_dir: Path = config.METADATA_DIR) -> list:
    """Rows of score_drop_rules.csv: a TYPE of run whose scores on a benchmark are dropped
    wholesale, without reading each score (a run setup known to fail, such as an output cap that
    cuts the reasoning of long-thinking runs before they answer). A rule names its feeds
    (`|`-separated), the benchmark, a regex searched in the run's name (with its `effort`, when the
    feed states it outside the name, appended as `_<effort>`), and `keep_at_or_above`: a score that
    high cannot have lost much to the failure and is kept (empty keeps nothing)."""
    path = metadata_dir / config.SCORE_DROP_RULES_FILE
    if not path.exists():
        return []
    table = pandas.read_csv(path, dtype={"feeds": str, "benchmark": str, "raw_name_regex": str})
    return [r._replace(raw_name_regex=re.compile(r.raw_name_regex)) for r in table.itertuples()]


def _dropped_by_rule(rec: Record, feed: str, rules: list, hits: Counter) -> bool:
    """Whether a drop rule covers `rec` (counted in `hits` under the rule's name)."""
    name = str(rec.raw_name) + (f"_{rec.effort}" if rec.effort else "")
    for r in rules:
        if (feed in r.feeds.split("|") and rec.benchmark == r.benchmark
                and r.raw_name_regex.search(name)
                and (pandas.isna(r.keep_at_or_above) or float(rec.score) < r.keep_at_or_above)):
            hits[r.rule] += 1
            return True
    return False


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
    corrections, applied = load_score_corrections(metadata_dir), set()
    drop_rules, rule_hits = load_score_drop_rules(metadata_dir), Counter()
    fixes, fixed = load_score_variant_fixes(metadata_dir), set()
    for feed in config.SOURCE_ORDER:
        log.info("%s:", feed)
        for rec in TRANSLATE[feed](feed_dir):
            rec = _corrected(rec, feed, corrections, applied)
            if rec is None or _dropped_by_rule(rec, feed, drop_rules, rule_hits):
                continue
            if rec.benchmark not in status:
                unknown_benchmarks.add(rec.benchmark)
                continue
            if status[rec.benchmark] != config.STATUS_INCLUDED:
                result.excluded[rec.benchmark] += 1
                continue
            mid = _take(result, feed, rec, aliases[feed], fixes, fixed)
            if mid and rec.meta:
                result.meta_obs.append({"model_id": mid, **rec.meta})
        _check_unit_range(result, feed)
    if unknown_benchmarks:
        raise ValueError(f"benchmarks with no row in {config.BENCHMARKS_FILE}: "
                         f"{sorted(unknown_benchmarks)}")
    _report_unused_aliases(result, aliases)
    stale = sorted(set(corrections) - applied)
    if stale:
        log.warning("%s: %d correction(s) not applied, the feed value has moved or the row is "
                    "gone (review them): %s", config.SCORE_CORRECTIONS_FILE, len(stale), stale)
    log.info("score corrections applied: %d", len(applied))
    stale_fixes = sorted({f.key for rows in fixes.values() for f in rows} - fixed, key=str)
    if stale_fixes:
        log.warning("%s: %d fix(es) not applied, the feed value has moved or the row is gone "
                    "(review them): %s", config.SCORE_VARIANT_FIXES_FILE, len(stale_fixes),
                    stale_fixes[:10])
    log.info("%s: %d score(s) fixed", config.SCORE_VARIANT_FIXES_FILE, len(fixed))
    log.info("%s: %d score(s) dropped by rule: %s", config.SCORE_DROP_RULES_FILE,
             sum(rule_hits.values()), dict(rule_hits) or "none")
    if result.excluded:
        log.info("excluded benchmarks (records dropped): %s", dict(result.excluded))
    if result.completed:
        log.info("efforts completed from `Name`: %s", dict(result.completed))
    drops = {f: sorted(d) for f, d in result.dropped.items() if d}
    log.info("explicit DROPs: %s", drops or "none")
    return result
