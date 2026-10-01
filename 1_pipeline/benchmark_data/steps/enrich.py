"""Pass 2: metadata is joined onto models and benchmarks.

Each join returns its two leftovers (metadata rows with no target, targets with no metadata)
for the build report.
"""

import logging
from pathlib import Path

import pandas

from benchmark_data import config
from benchmark_data.identity import IDENT_COLS, load_aliases, machine_name, model_id, resolve_model
from benchmark_data.sources.epoch_live import LIVE_TASK_SPEC
from benchmark_data.sources.epoch_zip import FILE_SPEC

log = logging.getLogger(__name__)

Leftovers = tuple[set, set]


# Lines of each leftover list shown in the build log. Orphan metadata is expected for models
# that only appeared on excluded benchmarks and for spellings later merged by an alias.
LEFTOVER_LINES = 20


def report_leftovers(label: str, meta_orphans: set, targets_without: set) -> None:
    """The two leftovers of a metadata join, logged the same way everywhere."""
    log.info("%s: %d metadata row(s) with no target, %d target(s) with no metadata",
             label, len(meta_orphans), len(targets_without))
    for x in sorted(meta_orphans)[:LEFTOVER_LINES]:
        log.info("    orphan metadata : %s", x)
    if len(meta_orphans) > LEFTOVER_LINES:
        log.info("    ... %d more (see the note below the join for the usual causes)",
                 len(meta_orphans) - LEFTOVER_LINES)
    for x in sorted(targets_without)[:LEFTOVER_LINES]:
        log.info("    no metadata     : %s", x)


def add_benchmark_metadata(benchmarks: pandas.DataFrame,
                           metadata_dir: Path = config.METADATA_DIR,
                           merged_parts: set[str] = frozenset()):
    """benchmarks.csv -> category, floor, ceiling, access (key: name); `included` rows only.

    `merged_parts` are the boards averaged into another series by merge_siblings: they are
    included so they get ingested, but legitimately absent from the final table.
    """
    meta = pandas.read_csv(metadata_dir / config.BENCHMARKS_FILE, dtype=str).fillna("")
    included = meta[meta["status"] == config.STATUS_INCLUDED]
    cols = ["name", "category", "floor", "ceiling", "access"]
    b = benchmarks.merge(included[cols], on="name", how="left", indicator=True)
    leftovers = (set(included["name"]) - set(benchmarks["name"]) - set(merged_parts),
                 set(b.loc[b["_merge"] == "left_only", "name"]))
    empty = {c: set(b.loc[b[c].fillna("") == "", "name"]) for c in ("category", "floor", "access")}
    for c, names in empty.items():
        if names:
            log.warning("benchmarks.csv: %d included benchmark(s) with an empty %s: %s",
                        len(names), c, sorted(names)[:8])
    return b.drop(columns="_merge").fillna({c: "" for c in cols}), leftovers


# Epoch's spelling in benchmark_metadata.csv -> ours, for rows matched by name only.
EPOCH_BENCHMARK_NAMES = {"Blueprint-Bench 2": "BlueprintBench 2"}


def load_epoch_benchmark_dates(path: Path = config.EPOCH_BENCHMARK_METADATA) -> dict[str, str]:
    """Epoch's `release_date` per benchmark, keyed on our names.

    A row is matched through its `source_file` (the ZIP translator's `FILE_SPEC`); a row without
    one (Epoch's benchmarks outside the ECI) or an internal evaluation, through its `benchmark`
    column: the live feed's `LIVE_TASK_SPEC`, a `FILE_SPEC` name spelled the same, or
    `EPOCH_BENCHMARK_NAMES`. Rows with no date or no match are left out.
    """
    if not path.exists():
        log.warning("%s absent: no Epoch benchmark dates", path)
        return {}
    table = pandas.read_csv(path, dtype=str).fillna("")
    zip_names = {spec[0] for spec in FILE_SPEC.values()}
    out = {}
    for _, r in table[table["release_date"] != ""].iterrows():
        if r["source_file"] in FILE_SPEC:
            name = FILE_SPEC[r["source_file"]][0]
        elif r["benchmark"] in LIVE_TASK_SPEC:
            name = LIVE_TASK_SPEC[r["benchmark"]][0]
        elif r["benchmark"] in zip_names:
            name = r["benchmark"]
        elif r["benchmark"] in EPOCH_BENCHMARK_NAMES:
            name = EPOCH_BENCHMARK_NAMES[r["benchmark"]]
        else:
            continue
        out[name] = r["release_date"]
    return out


def add_benchmark_release_dates(benchmarks: pandas.DataFrame,
                                metadata_dir: Path = config.METADATA_DIR,
                                epoch: dict[str, str] | None = None):
    """release_date: the benchmark's first public release, not its first score.

    Epoch's `benchmark_metadata.csv` first; `benchmark_release_dates.csv` (key: name, one source
    URL per row) wins over it, for the benchmarks Epoch does not date and those where Epoch dates
    another version or event (`docs/decisions.md`).

    Raises:
        ValueError: duplicated name, or a date that is not ISO `YYYY-MM-DD`.
    """
    epoch = load_epoch_benchmark_dates() if epoch is None else epoch
    manual = pandas.read_csv(metadata_dir / config.BENCHMARK_RELEASE_DATES_FILE,
                             dtype=str).fillna("")
    if manual["name"].duplicated().any():
        raise ValueError(f"duplicated name in {config.BENCHMARK_RELEASE_DATES_FILE}: "
                         f"{sorted(manual.loc[manual['name'].duplicated(), 'name'])}")
    bad = manual.loc[~manual["release_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}"), "name"]
    if len(bad):
        raise ValueError(f"{config.BENCHMARK_RELEASE_DATES_FILE}: non-ISO date for {sorted(bad)}")
    researched = dict(zip(manual["name"], manual["release_date"], strict=True))
    b = benchmarks.copy()
    from_epoch = b["name"].map(epoch)
    from_file = b["name"].map(researched)
    b["release_date"] = from_file.fillna(from_epoch).fillna("")
    log.info("benchmark release dates: %d from Epoch, %d from %s (%d of them replace Epoch's), "
             "%d undated", int((from_epoch.notna() & from_file.isna()).sum()),
             int(from_file.notna().sum()), config.BENCHMARK_RELEASE_DATES_FILE,
             int((from_file.notna() & from_epoch.notna() & (from_file != from_epoch)).sum()),
             int((b["release_date"] == "").sum()))
    return b, (set(researched) - set(b["name"]), set(b.loc[b["release_date"] == "", "name"]))


def add_organizations(models: pandas.DataFrame, metadata_dir: Path = config.METADATA_DIR):
    """organizations.csv -> organization, country (key: base_model)."""
    orgs = pandas.read_csv(metadata_dir / config.ORGANIZATIONS_FILE).fillna("")
    if orgs["base_model"].duplicated().any():
        raise ValueError("duplicated base_model in organizations.csv: the join would fan out")
    m = models.merge(orgs, on="base_model", how="left", indicator=True)
    leftovers = (set(orgs["base_model"]) - set(models["base_model"]),
                 set(m.loc[m["_merge"] == "left_only", "base_model"]))
    return m.drop(columns="_merge").fillna({"organization": "", "country": ""}), leftovers


def add_epoch_dates_and_flop(models: pandas.DataFrame, meta_obs: list[dict]):
    """publication_date, training_flop: modal value of the Epoch observations per model.

    A model appears in dozens of files and Epoch does not always agree with itself. The modal
    value is taken; ties go to the smallest (hence the earliest date).
    """
    obs = pandas.DataFrame(meta_obs)

    def modal(col):
        v = obs[["model_id", col]].dropna()
        v = v[v[col].astype(str).str.strip() != ""]
        return (v.value_counts().reset_index(name="n")
                 .sort_values(["n", col], ascending=[False, True])
                 .drop_duplicates("model_id").set_index("model_id")[col])

    models = models.copy()
    for col in ("publication_date", "training_flop"):
        models[col] = models["model_id"].map(modal(col))
    named = models.set_index("model_id")["base_model"]
    leftovers = (set(obs["model_id"]) - set(models["model_id"]),
                 set(named[models.loc[models["publication_date"].isna(), "model_id"]]))
    log.info("    of which without FLOP: %d model(s)", int(models["training_flop"].isna().sum()))
    return models.fillna({"publication_date": "", "training_flop": ""}), leftovers


def load_epoch_model_metadata(path: Path = config.EPOCH_MODEL_METADATA,
                              aliases_path: Path = config.FEED_DIR / "epoch" / "aliases.csv"
                              ) -> pandas.DataFrame:
    """Epoch's model table resolved to model ids: one row per model_id with date, organization,
    country (ISO alpha-2) and training FLOP.

    Rows are resolved with the same grammar and aliases as the score files. Several rows for one
    model: the earliest date, the first non-empty organization and country. Countries are mapped
    through `config.EPOCH_COUNTRY_ISO`, organizations through `config.EPOCH_ORGANIZATION_CANON`.

    Raises:
        ValueError: a country name missing from `config.EPOCH_COUNTRY_ISO`.
    """
    if not path.exists():
        log.warning("%s absent: no Epoch model metadata", path)
        return pandas.DataFrame(columns=["model_id", "date", "organization", "country", "flop"])
    table = pandas.read_csv(path, dtype=str).fillna("")
    table = table[table["model_version"] != ""]
    aliases = load_aliases(aliases_path)
    resolved = [resolve_model(raw, aliases, splittable=True) for raw in table["model_version"]]
    ok = [status == "ok" for status, _, _ in resolved]
    ids = [model_id(ident) for status, ident, _ in resolved if status == "ok"]
    table = table[ok].assign(model_id=ids)
    names = {c for cell in table["country"] for c in cell.split(",") if c}
    unknown = sorted(names - set(config.EPOCH_COUNTRY_ISO))
    if unknown:
        raise ValueError(f"model_metadata.csv: country name(s) not in EPOCH_COUNTRY_ISO: {unknown}")
    table["country"] = table["country"].map(
        lambda cell: ",".join(config.EPOCH_COUNTRY_ISO[c] for c in cell.split(",") if c))
    table["organization"] = table["organization"].replace(config.EPOCH_ORGANIZATION_CANON)
    first_non_empty = lambda s: next((x for x in s if x), "")  # noqa: E731
    return (table.sort_values(["model_id", "date"])
                 .groupby("model_id", sort=True)
                 .agg(date=("date", first_non_empty),
                      organization=("organization", first_non_empty),
                      country=("country", first_non_empty),
                      flop=("training_compute_flop", first_non_empty))
                 .reset_index())


def add_epoch_model_metadata_dates(models: pandas.DataFrame,
                                   epoch: pandas.DataFrame | None = None):
    """Fallback: Epoch's model table dates the models the score files leave undated.

    A resolved row dates the model of that identity **only if it has no date yet** (the score
    files' modal date wins: on contested models it was right more often, see
    `docs/decisions.md`).
    """
    epoch = load_epoch_model_metadata() if epoch is None else epoch
    found = dict(zip(epoch["model_id"], epoch["date"], strict=True))
    found = {k: v for k, v in found.items() if v}
    models = models.copy()
    empty = models["publication_date"] == ""
    hit = empty & models["model_id"].isin(found)
    models.loc[hit, "publication_date"] = models.loc[hit, "model_id"].map(found)
    log.info("model_metadata.csv: %d undated model(s) filled", int(hit.sum()))
    return models, (set(), set(models.loc[empty & ~hit, "base_model"]))


def add_epoch_organizations(models: pandas.DataFrame, epoch: pandas.DataFrame | None = None):
    """Fallback: Epoch's organization, country and training FLOP where ours are blank.

    organizations.csv stays the authority where it has a value, and so does the modal FLOP of the
    score files; disagreements on organization or country are reported (returned as a table,
    logged), never applied.

    Returns:
        (models, disagreements): one row per model where both sources have a value and differ.
    """
    epoch = load_epoch_model_metadata() if epoch is None else epoch
    e = epoch.set_index("model_id")
    models = models.copy()
    for col, src in (("organization", "organization"), ("country", "country"),
                     ("training_flop", "flop")):
        found = e[src][e[src] != ""]
        empty = models[col] == ""
        hit = empty & models["model_id"].isin(found.index)
        models.loc[hit, col] = models.loc[hit, "model_id"].map(found)
        log.info("model_metadata.csv: %d model(s) got their %s", int(hit.sum()), col)
    both = models.merge(epoch, on="model_id", suffixes=("", "_epoch"))
    has_org, has_country = both["organization_epoch"] != "", both["country_epoch"] != ""
    org_differs = (both["organization"] != both["organization_epoch"]) & has_org
    country_differs = (both["country"] != both["country_epoch"]) & has_country
    diff = both[org_differs | country_differs]
    cols = ["base_model", "organization", "organization_epoch", "country", "country_epoch"]
    diff = diff[cols].drop_duplicates().sort_values("base_model")
    if len(diff):
        log.warning("organizations.csv vs Epoch model_metadata: %d model(s) disagree (kept ours), "
                    "e.g. %s", len(diff), diff.head(3).to_dict("records"))
    return models, diff


def add_sibling_dates(models: pandas.DataFrame):
    """A run variant inherits the date of its siblings: same `base_model` and `snapshot`.

    Reasoning level, token budget and the run variant `thinking` describe
    how a model was run, not another release. When every dated sibling agrees on one date, the
    undated ones take it; two different dates leave them untouched (reported). Named variants
    such as fine-tunes are never filled this way.
    """
    models = models.copy()
    run = models["variant"].isin(config.RUN_VARIANTS)
    key = ["base_model", "snapshot"]
    dated = models[run & (models["publication_date"] != "")]
    per_key = dated.groupby(key)["publication_date"].agg(lambda s: sorted(set(s)))
    single = {k: v[0] for k, v in per_key.items() if len(v) == 1}
    ambiguous = {k for k, v in per_key.items() if len(v) > 1}
    empty = run & (models["publication_date"] == "")
    keys = list(zip(models["base_model"], models["snapshot"], strict=True))
    fill = [single.get(k, "") if e else "" for k, e in zip(keys, empty, strict=True)]
    filled = pandas.Series(fill, index=models.index) != ""
    models.loc[filled, "publication_date"] = pandas.Series(fill, index=models.index)[filled]
    left = {k for k, e in zip(keys, empty, strict=True) if e and k in ambiguous}
    log.info("sibling dates: %d model(s) filled, %d left because siblings disagree",
             int(filled.sum()), len(left))
    return models, ({f"{b} @{s}" if s else b for b, s in left}, set())


def add_model_version(models: pandas.DataFrame, names) -> pandas.DataFrame:
    """`model_version`: the machine name consumers key on.

    The most frequent spelling the grammar parsed for that model (the splittable feeds: Epoch,
    the live feed and Kaggle) wins;
    a model seen only through aliases (Scale, RAND) gets `identity.machine_name` of its tuple.
    """
    counts = pandas.DataFrame([(m, n, c) for (m, n), c in names.items()],
                              columns=["model_id", "name", "n"])
    # Epoch's `_unknown` suffix names the same identity as the bare spelling (identity grammar);
    # the votes of both spellings go to the bare one.
    counts["name"] = counts["name"].str.replace(r"_unknown$", "", regex=True)
    counts = counts.groupby(["model_id", "name"], as_index=False)["n"].sum()
    best = (counts.sort_values(["n", "name"], ascending=[False, True])
                  .drop_duplicates("model_id").set_index("model_id")["name"])
    models = models.copy()
    observed = models["model_id"].map(best)
    idents = models[IDENT_COLS].to_dict("records")
    models["model_version"] = [o if isinstance(o, str) else machine_name(i)
                               for o, i in zip(observed, idents, strict=True)]
    n_seen = int(observed.notna().sum())
    log.info("model_version: %d observed spelling(s), %d reconstructed",
             n_seen, len(models) - n_seen)
    return models


def add_manual_dates(models: pandas.DataFrame, metadata_dir: Path = config.METADATA_DIR):
    """release_dates.csv -> publication_date (key: base_model, snapshot, variant). Wins over Epoch.

    One row per researched date: models Epoch does not date, and models whose sources disagreed
    and were settled (`docs/decisions.md`, each row carries its source). A row with an empty
    `variant` applies to every run of that `base_model` and `snapshot` (any reasoning level,
    run variants of `config.RUN_VARIANTS`); a row naming a variant (a fine-tune such as
    `Hermes 3`) applies to that variant only.

    Raises:
        ValueError: duplicated key, or a date that is not ISO `YYYY-MM-DD`.
    """
    key = ["base_model", "snapshot", "variant"]
    manual = pandas.read_csv(metadata_dir / config.RELEASE_DATES_FILE, dtype=str).fillna("")
    if manual.duplicated(key).any():
        dups = manual.loc[manual.duplicated(key), key].to_records(index=False).tolist()
        raise ValueError(f"duplicated (base_model, snapshot, variant) in release_dates.csv: {dups}")
    bad = manual.loc[~manual["publication_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}"), key]
    if len(bad):
        rows = bad.to_records(index=False).tolist()
        raise ValueError(f"release_dates.csv: non-ISO date for {rows}")

    m = models.copy()
    m["_key_variant"] = m["variant"].where(~m["variant"].isin(config.RUN_VARIANTS), "")
    manual = (manual[[*key, "publication_date"]]
              .rename(columns={"publication_date": "_manual", "variant": "_key_variant"}))
    m = m.merge(manual, on=["base_model", "snapshot", "_key_variant"], how="left")
    hit = m["_manual"].notna()
    had = m["publication_date"].fillna("") != ""
    log.info("release_dates.csv: %d model(s) matched, %d date(s) replaced, %d filled",
             int(hit.sum()), int((hit & had & (m["publication_date"] != m["_manual"])).sum()),
             int((hit & ~had).sum()))
    m.loc[hit, "publication_date"] = m.loc[hit, "_manual"]
    mkey = ["base_model", "snapshot", "_key_variant"]
    matched = set(map(tuple, m.loc[hit, mkey].to_numpy()))
    orphans = {" ".join(x for x in (b, f"@{s}" if s else "", f"[{v}]" if v else "") if x)
               for b, s, v in map(tuple, manual[mkey].to_numpy()) if (b, s, v) not in matched}
    return m.drop(columns=["_manual", "_key_variant"]), (orphans, set())


def enrich(models: pandas.DataFrame, benchmarks: pandas.DataFrame, meta_obs: list[dict],
           metadata_dir: Path = config.METADATA_DIR, merged_parts: set[str] = frozenset(),
           names=None):
    """All the joins of pass 2, each with its leftovers report."""
    models = add_model_version(models, names or {})
    models, lo = add_organizations(models, metadata_dir)
    report_leftovers("organizations.csv", *lo)
    models, lo = add_epoch_dates_and_flop(models, meta_obs)
    report_leftovers("epoch (gleaned dates / FLOP)", *lo)
    epoch = load_epoch_model_metadata()
    models, lo = add_epoch_model_metadata_dates(models, epoch)
    report_leftovers("epoch model_metadata.csv (fallback dates)", *lo)
    models, _ = add_epoch_organizations(models, epoch)
    models, lo = add_manual_dates(models, metadata_dir)
    report_leftovers("release_dates.csv", *lo)
    models, lo = add_sibling_dates(models)
    report_leftovers("sibling dates", *lo)
    benchmarks, lo = add_benchmark_metadata(benchmarks, metadata_dir, merged_parts)
    report_leftovers("benchmarks.csv", *lo)
    benchmarks, lo = add_benchmark_release_dates(benchmarks, metadata_dir)
    report_leftovers("benchmark release dates", *lo)
    return models, benchmarks
