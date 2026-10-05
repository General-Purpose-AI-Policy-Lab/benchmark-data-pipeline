# benchmark-data-pipeline

Turns public benchmark score feeds (Epoch AI, Kaggle, RAND, Scale SEAL, the Cybench leaderboard) into CSV tables linked by UUID (`2_database/`: scores, models, benchmarks, human baselines, plus the excluded benchmarks and every raw model name) and two flat consumer views (`3_views/`).

Public scores are scattered across a handful of sources that each name models their own way: `claude-opus-4-5-20251101-thinking` here, `Claude Opus 4.5 (Thinking)` there, without saying whether the reasoning effort is known or simply missing. Reconciling those tables is where the time goes, and it usually happens by hand in a notebook that keeps no record of what was merged or why.

This repository makes it a reproducible pass. Every source keeps its own alias dictionary, anything that is neither ingested nor explicitly set aside is **reported** rather than silently handled, identifiers are deterministic `uuid5` values of the identity tuple, and two successive builds must produce a byte-identical `2_database/`. The database is the common input of the lab's modelling work, starting with [`Multiaxis_ECI`](https://github.com/General-Purpose-AI-Policy-Lab/Multiaxis_ECI) and [`benchmark-forecasting`](https://github.com/General-Purpose-AI-Policy-Lab/benchmark-forecasting).

## Layout

```
0_input/feed/<source>/      one source's raw data + its aliases.csv (one per source, never shared)
0_input/metadata/           benchmarks.csv, organizations.csv, sibling_merges.csv, release_dates.csv, benchmark_release_dates.csv,
                            human_baselines.csv, score_corrections.csv, score_drop_rules.csv, score_variant_fixes.csv
1_pipeline/benchmark_data/  the package: python -m benchmark_data {refresh,build,check,parity}
  identity.py               machine-name grammar, aliases, uuid5
  sources/<feed>.py         one module per feed: its _SPEC / _SKIP dictionaries and translate()
  sources/metr_human_baseline.py  not a feed: derives the METR row of human_baselines.csv
  steps/                    ingest -> dedup -> merge_siblings -> enrich -> human_baselines -> validate -> export
  views/                    all_scores_flat.py, dated_scores_flat.py: the consumer views
  parity.py                 views against the consumers' frozen outputs (tests/parity/golden)
  build.py  check.py  refresh.py
2_database/<YYYYMMDD>/      the tables of the build run that day (+ excluded_benchmarks.csv, model_names.csv, build_manifest.json)
3_views/<YYYYMMDD>/         all_scores_flat.csv, dated_scores_flat.csv, human_baselines.csv, same run
docs/                       decisions.md (decision log), decisions_pending.md (none open today), plan_fusion.md (merge plan, historical),
                            reviews/ (score reviews), frontier_models.csv, release_dates_consistency.csv
tests/                      unit tests, golden copies (tests/expected_database, tests/expected_views), parity goldens
```

Feeds: `epoch` (the CSV files of Epoch's ZIP), `epoch_live` (Epoch's internal evaluations), `epoch_cyber` (the long table behind Epoch's cyber capabilities index), `cybench_site` (Cybench's own leaderboard, frozen snapshot), `kaggle` (3 leaderboard JSON files), `rand` (1 CSV), `seal` (21 HTML pages). Local snapshot, refreshed by `refresh` (see "Run"); dates and sha256 in `0_input/feed/provenance.json`.

**SEAL pages are not versioned.** Scale AI publishes its leaderboards under no open license, so `0_input/feed/seal/*.html` is gitignored (see `NOTICE.md`). On a fresh clone run `python -m benchmark_data refresh` **before** the build; otherwise the build stops with an explicit message. Everything else about the SEAL feed (aliases, sha256, derived scores in `2_database/`) stays tracked.

## The tables

### models.csv

| column | role |
|---|---|
| `model_id` | uuid5 of the identity tuple. Primary key. |
| `model_version` | the machine name consumers key on (see "Consumer views") |
| `base_model`, `reasoning_level`, `reasoning_tokens`, `snapshot`, `variant` | **identity** — part of the ID |
| `organization`, `country`, `publication_date`, `training_flop` | **metadata** — NOT part of the ID |

Adding a metadata column changes no ID. Correcting an identity column changes one. `country` is ISO 3166-1 alpha-2 (`US`, `CN`, `FR`, ...; several as `US,CN`).

`publication_date` comes, in order, from the modal Epoch `Release date` of the model, from Epoch's `model_metadata.csv` for models the score files leave undated, from `0_input/metadata/release_dates.csv` where a date was researched (key `base_model, snapshot, variant`; each row carries its source; it wins over both Epoch sources), and finally from dated siblings (same `base_model` and `snapshot`, differing only by reasoning level or run variant). `organization`, `country` and `training_flop` come from `0_input/metadata/organizations.csv` (key `base_model`) and the modal FLOP of the score files, then from Epoch's `model_metadata.csv` where those are blank (country names mapped to ISO through `config.EPOCH_COUNTRY_ISO`, Google's spellings unified as `Google DeepMind`); where both have a value and disagree, ours is kept and the build logs the difference. Convention: the first day the model was publicly usable or downloadable on any surface (consumer app, API or weights), in the developer's local date; a preview restricted to invited partners does not count. When the same model reached a consumer app before its API snapshot, the consumer date wins (o1: 2024-12-05, not the 12-17 snapshot). Exception: Claude Mythos Preview keeps its announcement date although it was invitation-only.

### benchmarks.csv

| column | role |
|---|---|
| `benchmark_id` | uuid5 of `name`. Primary key. |
| `name` | identity (the only column in the ID) |
| `category`, `floor`, `ceiling`, `access` | metadata, from `0_input/metadata/benchmarks.csv` (`ceiling` empty unless the full range is demonstrably attainable) |
| `release_date` | first public release of the benchmark (arXiv v1, announcement, leaderboard or dataset, whichever came first), not its first score: Epoch's `benchmark_metadata.csv`, overridden by `0_input/metadata/benchmark_release_dates.csv` (one source URL per row). A revision keeps the date of the benchmark it revises; a new task set under a new version takes its own. |

Only benchmarks whose `status` is `included` in `0_input/metadata/benchmarks.csv` reach the database (see "Benchmark scope"). The justification columns (`floor_reason`, `floor_source`, `access_evidence_url`, `note`) stay in the metadata file.

`access` says how exposed the scored items are to training data (`config.ACCESS_CLASSES`): `public` (the scored set can be downloaded without human review: no gate, or an automatic one such as Hugging Face's `gated: auto`), `semi_private` (public sample or training split, scored set held out; an illustrative example alone is not a sample), `private` (never released, or available on request only, i.e. after a human reviews the request), `dynamic` (items regenerated or refreshed), `open_problems` (statements public but unsolved, so nothing to memorise: FrontierMath Erdos, OEIS Open Lite).

### scores.csv

`model_id`, `benchmark_id`, `score`, `stderr`, `harness`, `feed`, `source_label`, `source_url`. One row per `(model_id, benchmark_id)`; `stderr` empty when the source publishes none; `harness` is the scaffold or agent framework that produced the kept score, empty when unknown; `source_label` and `source_url` say where the feed took the number (Epoch's `Source` / `Source link` columns, a Kaggle or Scale board, RAND's report, Epoch's evaluation log), so a doubtful score can be traced without opening the feed.

### excluded_benchmarks.csv, model_names.csv, build_manifest.json

`excluded_benchmarks.csv` lists every benchmark kept out of the database (`status` excluded, review or no_source in `benchmarks.csv`) with the criterion that fails, the number of records dropped at this build and the note: the scope decisions are visible next to the data they shape. `model_names.csv` keeps every spelling a feed used for a model (`model_id, feed, raw_name, n_records`), for audits and to find a row upstream. `build_manifest.json` says what the build was made of: schema version, timestamp, git commit, the feeds' provenance (URL, date, sha256), the sha256 of every metadata and alias file, and the row counts; it carries a timestamp, so it sits outside the golden comparison.

### human_baselines.csv

`benchmark_id`, `name`, `group`, `score`, `note`, `source`. One row per **measurement** of human performance, copied from `0_input/metadata/human_baselines.csv` exactly as stated by its source: no clipping (a panel that solves everything is `1.0`; a consumer that needs `1 - ε` clips downstream), no rounding, several rows when several measurements exist for one group. `group` is one of the nine tiers of `config.HUMAN_GROUPS` (Average Human, Skilled Generalist, Domain Expert, Top Performer, committees, High School Qualifier / Top Performer). Rows for benchmarks absent from the database are dropped and reported. One row is not a published figure but a derivation: `METR Time Horizons / Committee of Domain Experts`, recomputed from METR's run table by `sources/metr_human_baseline.py`, which documents the weighting, verifies it against the `average_score` the pipeline ingests, and states the caveats (user decision of 2026-09-11, `docs/decisions.md`). Its `source` column says so.

## Consumer views (`3_views/`)

Derived from the four tables at every build, never edited by hand:

| file | schema | rows |
|---|---|---|
| `all_scores_flat.csv` | `model_version, score, release_date, organization, benchmark, stderr, source, source_url, feed, category, lower_bound, ceiling` (Multiaxis_ECI's `benchmarks_merged.csv` columns, plus the source link, the feed, the benchmark's floor and known ceiling) | every score |
| `dated_scores_flat.csv` | the same columns (benchmark-forecasting's input) | scores of dated models only |
| `human_baselines.csv` | `benchmark, group, score, note, source` | every baseline |

`lower_bound` is the benchmark floor (chance level or documented minimum, `0_input/metadata/benchmarks.csv`); `ceiling` is a known upper limit on achievable scores, empty when none is established. Today it is `1.0` for the 13 benchmarks whose full range is demonstrably attainable (a human baseline reaches the top, every problem has a verified solution, or every task is a capture-the-flag with a known flag: ARC-AGI, ARC-AGI-2, EBR-bench, VPCT, Cybench, the two FrontierMath v2 sets, the six AISI CTF and Cyber Range sets), the asymptotes benchmark-forecasting pins. Epoch's `score_ceiling` estimates are not recorded (too approximate); `ceiling_reason` in `benchmarks.csv` documents each value. `model_version` is the machine name consumers key on: the most frequent spelling Epoch or Kaggle used for the model, else `identity.machine_name` of the identity tuple (snapshot written the developer's way, effort or budget as `_high` / `_16K`, `_thinking` for the run variant, `_prounknown` for a pro variant whose effort is unknown). `source` is the fine label the feed publishes for the row (a leaderboard, a technical report, Epoch's evaluation log), the feed's name when it publishes none (`config.FEED_LABEL`, a defensive fallback: every feed labels its rows today); `source_url` and `feed` travel with it. Sibling boards are already merged, so the views carry no merge option.

`python -m benchmark_data parity` compares the views with the last files the two repositories built on their own (`tests/parity/golden/`, Multiaxis_ECI `55687ce` and benchmark-forecasting `2ed2c34`) and writes `reports/parity_<consumer>.md`: lost pairs by cause (benchmark excluded, board merged, model renamed, other), new pairs, scores and dates that moved. Every golden benchmark name must map through `previous_names` (tested); the other buckets are reviewed, not asserted.

## Schema versions

`benchmark_data.SCHEMA_VERSION`, bumped when a table gains or loses a column or when identities move en masse.

| version | change |
|---|---|
| 2.0 | uuid5 identities, four tables, harness on scores, benchmark scope at ingestion (2026-09-04) |
| 2.1 | `models.model_version`, `benchmarks.ceiling`, `scores.source_label` / `source_url`, consumer views in `3_views/` (2026-09-07) |
| 2.2 | `benchmarks.release_date` (2026-10-01) |

## Conventions (non-negotiable)

- **Empty cell = unknown.** `unknown ≠ known`: `opus-5` (empty level) and `opus-5_high` (level `high`) are two distinct models, two rows, two IDs. An unknown never merges with a known value.
- **Deterministic IDs.** `uuid5(NAMESPACE, "model|" + join(identity tuple, "|"))`. Re-run → same IDs. Correcting an alias changes the ID: intended, the ID follows the identity, not the history.
- **`variant`**: `thinking` = thinking enabled, effort and budget unknown; a named variant (`pro`, `chat`, `Cyber`, a fine-tune such as `Hermes 3`) is part of the identity and of `model_version`; empty otherwise (thinking is implicit when `reasoning_level` or `reasoning_tokens` is known).
- **Harness is not identity.** A model's score on a benchmark is its best score across harnesses; the winning harness is recorded on the score row.
- **`score ∈ [0, 1]`** (no percentages).
- **Dedup**, in this order: exact duplicates merged; otherwise `max`; then two equal scores of one release on one benchmark keep a single row (`steps/dedup.drop_bare_copies`, see "Move a score to the effort its run used"). Kaggle's independent re-runs are recorded as a harness (`Kaggle Open Benchmarks`), so they compete like any other run.
- **Sibling boards** listed in `0_input/metadata/sibling_merges.csv` (the three SWE Atlas boards; PRBench Finance + Legal too, though PRBench is excluded since 2026-09-30) are averaged per model into one series after deduplication.

## Benchmark scope

One row per benchmark in `0_input/metadata/benchmarks.csv`, with a `status`:

| status | meaning |
|---|---|
| `included` | ingested and written to the database |
| `excluded` | dropped at ingestion; `exclusion_criterion` says which criterion fails |
| `review` | new upstream benchmark not yet examined; dropped until decided |
| `no_source` | no feed supplies it today; the row keeps its metadata |

The four inclusion criteria, shared by every downstream analysis: (1) scores are a proportion in [0, 1]; (2) the benchmark measures a capability, not a propensity; (3) it was run on a good share of the frontier models of its evaluation period; (4) its quality is sufficient for the ranking of scores to be informative. Being old, saturated or no longer evaluated is not a reason to exclude, and errors in the item set are tolerated. Files whose score is not a proportion at all never get a score: they sit in the source's `_SKIP` dictionary with the reason, and carry an `excluded` row in `benchmarks.csv` so that `excluded_benchmarks.csv` lists them too.

Benchmark names follow Epoch's `benchmark_metadata.csv` when Epoch publishes the benchmark, otherwise the authors' spelling, with the version number in the name (`FrontierMath Tiers 1-3 v2`, `OSWorld 2.0`). Former names are listed in the `previous_names` column.

## Naming conventions, per source

**Hybrid Claude models** (`config.CLAUDE_HYBRID_BASES`, 3.7 Sonnet to Opus 5.5 and Fable 5.1) run with or without extended thinking, and the sources write the two modes apart: in Epoch, its live feed and Kaggle the bare name is the run without thinking (effort `none`; Epoch's own labels say "no thinking") and `_unknown` a thinking run of unknown budget (`thinking`). Rows of unknown mode (system cards, agent harnesses, SEAL's 2026 models) keep the bare name (`identity.hybrid_mode`).

| Source | Field | Format | Strategy |
|---|---|---|---|
| `epoch` (ZIP) | `Model version` | machine name `[provider/]base[-date][_suffix]` | grammar + `aliases.csv` for the exceptions |
| `epoch_live` | `model` | same | grammar + `aliases.csv` for a few spellings |
| `epoch_cyber` | `model` (display name) | Epoch's cyber long table, display names | full enumeration in `aliases.csv` |
| `cybench_site` | `Model` | display names of the Cybench leaderboard | full enumeration in `aliases.csv` |
| `kaggle` | `modelVersionSlug` | pure machine name, `-default` stripped, never an effort | grammar + `aliases.csv` for lower-case spellings of Epoch names |
| `rand` | `Model` | free display names (`Amazon Nova 1.0 Lite`) | full enumeration in `aliases.csv` |
| `seal` | `model` (JSON in the HTML) | five incompatible encodings, plus `model (harness) effort` on the agentic boards | full enumeration in `aliases.csv` (with `harness`) |

### Machine-name grammar (`identity.split_name`)

`[provider/]base[-date][_suffix]`

- `_` introduces a **configuration knob**, `-` is part of the **identity** (`kimi-k2-thinking` is a name, not a knob).
- Suffix vocabulary (case-insensitive), on the last `_` only:

  | suffix | effect |
  |---|---|
  | `minimal` `low` `medium` `high` `xhigh` `max` `none` | `reasoning_level` |
  | `<N>K` (e.g. `24K`) | `reasoning_tokens = N × 1000` |
  | `thinking` | `variant = thinking` |
  | `unknown` | dropped: Epoch's "effort unknown" is the bare identity (an effort-less row of a reasoning model says the same thing) |
  | anything else | the `_` is part of the name, nothing is split |

- **Date** extracted only at the end of the base, in the `-YYYY-MM-DD` or `-YYYYMMDD` forms → `snapshot`. Deliberate under-extraction: `2507`, `0528`, `03-2025` stay in `base_model`.
- The `provider/` prefix (a single `/`) is removed.

## Common gestures

### Fix a mistranslated name

1. In `2_database/<YYYYMMDD>/scores.csv` (the latest run), find the faulty row → the `feed` column is the source.
2. Edit `0_input/feed/<feed>/aliases.csv`. Columns: `raw_name,base_model,reasoning_level,reasoning_tokens,snapshot,variant,harness,note`. `raw_name` is the exact raw string (after stripping trailing `*`/`†` and whitespace).
3. Empty `base_model` = **deliberate DROP** (no alias file uses it today; the mechanism stays). Put the reason in `note`.
4. `python -m benchmark_data build`. The alias always wins over the grammar, with one nuance on Epoch: an effort read from the displayed `Name` may complete an identity the alias left empty.

### Add a source (e.g. MazeBench)

1. `0_input/feed/mazebench/`: the raw data + an `aliases.csv` (even empty, with the header).
2. A module `1_pipeline/benchmark_data/sources/mazebench.py` with its dictionaries (`MAZEBENCH_SPEC`: what is ingested; `MAZEBENCH_SKIP`: what is set aside, with the reason) and a `translate(feed_dir)` function yielding `Record`s.
3. An entry in `sources.TRANSLATE`, in `config.SOURCE_ORDER` and in `config.SPLITTABLE`.
4. A row per new benchmark in `0_input/metadata/benchmarks.csv` (the build refuses an unlisted one).
5. `python -m benchmark_data build`.

**`_SPEC` / `_SKIP` rule**: anything in neither dictionary is **reported**. Never ingested silently, never dropped silently. A feed that changes shape is seen, for the feeds that enumerate their own content (the Epoch ZIP, the live feed, the cyber table); Kaggle and Scale boards are fetched by name from `KAGGLE_SPEC` and `SEAL_SPEC`, so a board they add is discovered by hand, not by the build.

### Correct or drop a published score

Add a row to `0_input/metadata/score_corrections.csv` (`feed`, `benchmark`, the feed's raw name, the value the feed's translator yields, the corrected value or empty to drop the row, source URL, note). A correction stops applying when the feed changes that value, and the build reports it for review. Record the reasoning in `docs/decisions.md`.

### Drop a type of run

A row in `0_input/metadata/score_drop_rules.csv` (`rule`, `feeds`, `benchmark`, `raw_name_regex`, `keep_at_or_above`, `note`) drops every matching run scoring below the bar, for a whole class of runs known to be truncated or misconfigured (e.g. maximum-effort runs cut off by the harness's token limit). It applies after `score_corrections.csv`.

### Move a score to the effort its run used

A score whose run names no effort although its source states it (a board label, a paper's settings table, the model arguments of an Inspect log), or that copies a labelled score of the same model, gets a row in `0_input/metadata/score_variant_fixes.csv`: `feed`, `benchmark`, the score's `model_id` before the fix (`model_version` beside it for the reader), the `score` it carries, `fix` (`relabel` with the effort `suffix` in machine-name grammar, `_none`, `_high`, `_thinking`, `_16K`; or `drop`), source URL, note. Ingest applies it on the resolved identity, so it works for every feed whatever its raw spelling; a fix whose value the feed has changed stops applying and is reported. An empty `score` matches every value, for a benchmark published as the mean of several records (SWE Atlas, keyed on its three sub-boards). A third action, `remodel`, moves the score to another model (`new_model`, a machine name: an API alias such as `deepseek-chat` served a different release at each date). After deduplication, two equal scores (to 1e-6, away from 0 and 1) of one release on one benchmark are one data point (`steps/dedup.drop_bare_copies`), even when the two are separate runs: the row whose effort its source states is kept, then the bare row, then a row whose effort only a feed's hybrid-model convention gave (Epoch's `_unknown` read as thinking on a Claude hybrid). Record the reasoning in `docs/decisions.md`.

### Add or exclude a benchmark

Edit its row in `0_input/metadata/benchmarks.csv`: `status`, `exclusion_criterion`, `note`. A new Epoch file also needs a `FILE_SPEC` entry (benchmark name, score column, divisor).

### Correct a release date

Add a row to `0_input/metadata/release_dates.csv` (`base_model`, `snapshot`, `variant`, ISO date, source URL, note). With an empty `variant` the row wins over Epoch for every effort level and run variant of that exact snapshot; name the variant to date a fine-tune. A row matching no model is reported by the build. Record the reasoning in `docs/decisions.md`.

### Correct a benchmark's release date

Add a row to `0_input/metadata/benchmark_release_dates.csv` (`name`, ISO `release_date`, source URL, note). It wins over Epoch's date; a row naming no benchmark of the build, and an included benchmark left undated, are reported. Record the reasoning in `docs/decisions.md`.

### Add a metadata column

1. A column in `0_input/metadata/benchmarks.csv` or `organizations.csv`.
2. Add it to the join in `1_pipeline/benchmark_data/steps/enrich.py` and to `BENCH_COLS` or `MODEL_COLS` in `config.py`; without the latter it is silently absent from the written CSV.
3. `python -m benchmark_data build`. No ID moves. The golden test flags the new column: intended, re-bless with `cp 2_database/<YYYYMMDD>/*.csv tests/expected_database/` (the run just built).

## Continuous integration

`.github/workflows/ci.yml` runs ruff and pytest on every push and pull request; the golden test skips there because Scale's pages are not redistributed, the parity tests run against the committed views. `.github/workflows/refresh.yml` runs monthly and on demand: refresh, build, the tests except the golden one (a refresh is meant to change the tables), `check` (differences expected, reported not failed), `parity`, then opens a pull request with the data changes, the parity reports uploaded as a workflow artifact.

The build logs every score below its benchmark floor (kept as published: chance-level or weaker models); `1_pipeline/scripts/release_dates_consistency.py` regenerates `docs/release_dates_consistency.csv`, the table of models whose date sources disagree and the date kept.

## Run

```bash
uv venv --python 3.11 .venv && uv pip install -e . --group dev
python -m benchmark_data refresh      # required on a fresh clone: fetches the SEAL pages
python -m benchmark_data build        # offline, deterministic; writes 2_database/<today>/ and 3_views/<today>/
python -m benchmark_data check        # the latest run == the blessed copies under tests/ ?
pytest                                # unit tests + golden + determinism
ruff check .
```

**Dated runs.** Every build writes its tables to `2_database/<YYYYMMDD>/` and its views to `3_views/<YYYYMMDD>/`, named by the local date the build ran (`benchmark_data/runs.py`); `build_manifest.json` records the same moment in `built_at`, with its offset. A second build the same day replaces that day's folders; earlier days stay. A rebuild with no feed refresh since a run (a metadata or code fix) writes into that run instead, `python -m benchmark_data build --date YYYYMMDD`: its data still date from then. `check`, `parity` and the consumers' `sync` (Multiaxis_ECI, benchmark-forecasting) read the most recent date, and the consumers name their outputs after it, so the date carried by a result folder is the day the pipeline ran, not the day the analysis was done.

The build only needs `pandas`. Two successive builds must produce a **byte-identical** set of tables; a divergence means an unsorted `dict`/`set` somewhere (`tests/test_build_golden.py` checks it).

`check` compares the latest `2_database/<YYYYMMDD>/` and `3_views/<YYYYMMDD>/` with their blessed copies `tests/expected_database/` and `tests/expected_views/` (regression test). An intended difference (new feed, corrected alias, refreshed data) is re-blessed with the command `check` prints, `cp 2_database/<YYYYMMDD>/*.csv tests/expected_database/ && cp 3_views/<YYYYMMDD>/*.csv tests/expected_views/`.

### Refresh the feeds

`python -m benchmark_data refresh` rewrites `0_input/feed/`, then `build`. RAND stays frozen (Dev et al. 2025 report). Novelties are never ingested quietly: unknown files and tasks of the Epoch feeds and unresolved names show up in the build log, to be curated in the `*_SPEC` dictionaries and the `aliases.csv` files (new Kaggle or Scale boards are added to `KAGGLE_SPEC` / `SEAL_SPEC` by hand, see above). Provenance (URL, date, sha256): `0_input/feed/provenance.json`.

## License and sources

The code, the curated dictionaries and the CSV files in `2_database/` and `3_views/` are under **CC-BY-4.0** (`LICENSE`).

Upstream scores carry their own terms: Epoch AI is CC-BY, Kaggle under its terms of service, RAND by citation of RR-A3797-1, Scale SEAL with no open license. Per-feed detail and what to credit when republishing: [`NOTICE.md`](NOTICE.md).

## Related repositories

Formerly `eval-data-pipeline` (renamed 2026-09-04). This repository is the **successor of the internal data pipelines** of [`Multiaxis_ECI`](https://github.com/General-Purpose-AI-Policy-Lab/Multiaxis_ECI) (a Bayesian re-creation of the Epoch Capabilities Index) and of [`benchmark-forecasting`](https://github.com/General-Purpose-AI-Policy-Lab/benchmark-forecasting) (forecasting benchmark saturation). Both now read its views; the history of the merge is in [`docs/plan_fusion.md`](docs/plan_fusion.md).
