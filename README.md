# eval-data-pipeline

Canonical home for the benchmark score data and the pipeline that refreshes
it. Extracted from the ECI Bayesian modeling repo; the full history of
`data/` came along. Consumers (the ECI fits, future projects) read the
files below. Nothing here depends on any modeling code.

## The dashboard

Start the server. It opens the page for you:

```bash
./scripts/serve.sh
```

The dashboard is at <http://localhost:8130>. Press Ctrl-C to stop the server.

`python3 scripts/serve.py` starts the same server without opening a browser.
Browsers block `fetch` from `file://`, so you cannot open `index.html` as a file.

Six tabs:

- **Browse** — filter the merged table by model, benchmark, source, category,
  organization, and release date. Sort any column. Each row shows its chance floor.
- **Benchmarks** — one row per benchmark: category, notes, chance floor, coverage.
- **Download** — the filtered rows as CSV, plus links to the raw files.
- **Report** — the report from the last refresh.
- **Refresh** — run the pipeline. See below.
- **Curate** — decide new model names and missing benchmark metadata.

`python3 -m http.server` serves the page as well, but the Refresh and Curate
tabs need `serve.py`. Without it, both tabs show a hint instead of the form.

## Paths of truth

| File | What it is |
|---|---|
| `data/processed/benchmarks_merged.csv` | the merged table: `model_version,score,release_date,organization,benchmark,stderr,source,category` |
| `data/curated/human_baselines.csv` | human tiers as test-takers — **derived**, written by the refresh |
| `data/curated/human_baselines_source.csv` | the hand-maintained baselines the refresh reads |
| `data/curated/*.csv` | per-benchmark facts (chance floors, ceilings, item counts, score clips) and curated corrections |
| `data/pipeline/canonical/*` | name/alias maps and benchmark metadata |
| `data/pipeline/output/pipeline_report.md` | provenance report of the last refresh |

Future projects clone this repo and read those paths. No API layer.

## Refreshing

Open `data/pipeline/pipeline.ipynb`, Restart Kernel → Run All (needs
pandas, numpy, requests — no modeling stack). The notebook writes only to
`data/pipeline/output/`. Then:

```bash
python3 scripts/check.py
```

`check.py` validates those outputs. It copies them into
`data/{processed,curated}/` only if every check passes, so a failed run leaves
the previous data in place. Then commit. Full pipeline docs (the five feeds,
merge policy, guards) are in
[`data/pipeline/README.md`](data/pipeline/README.md). Same-UTC-day re-runs
reuse the snapshot folder; `snapshots/` and `intermediate/` are gitignored
and regenerable.

## Refreshing from the page

The Refresh tab runs the same notebook headlessly, then `scripts/check.py`.
Leave the date blank to fetch or reuse today's snapshot. A past date replays
that snapshot offline. The force re-fetch checkboxes delete that source's
cache in the target snapshot before the run, so it is downloaded again. The
merged table always contains all five feeds; a checkbox controls the fetch,
not the scope.

When a refresh lists new models or unrecognized benchmarks, and for how
canonical names are chosen: [`docs/curation.md`](docs/curation.md).

## Where to edit what

Two kinds of decision live in two different places.

**Names live in files.** Edit them by hand, or use the Curate tab.

| File | What you put there |
|---|---|
| `data/pipeline/canonical/model_aliases.csv` | `variant,canonical,note`. One row per renamed model. An empty `canonical` drops the model from the dataset. |
| `data/pipeline/canonical/reviewed_models.txt` | One name per line. The name is already correct, so the pipeline keeps it. |
| `data/pipeline/canonical/benchmark_names.csv` | `variant,canonical,note`. The same idea, for benchmark names. |
| `data/pipeline/canonical/benchmark_metadata.csv` | `benchmark,category,notes`. One row per benchmark. |

A refresh lists every model name it does not recognize in
`data/pipeline/output/missing_models.csv`. Decide each name, then refresh
again. A decided name leaves that list.

The score needs no decision. It enters the merged table as soon as a feed
carries it. Your decision only sets the name the score is filed under.

**Which upstream files to read lives in the notebook**, not in a config file.
Each `_SPEC` maps an upstream file, slug, or task to a benchmark name. Each
`_SKIP` records what the pipeline ignores, and why. The pipeline reports
anything that is in neither, so a new benchmark cannot arrive unnoticed.

| Section | Cell | What to edit | Feed |
|---|---|---|---|
| 03 | 8 | `FILE_SPEC`, `FILE_SKIP`, `FILE_SCORE_TRANSFORM` | Epoch ZIP |
| 03b | 10 | `RAND_BENCH_COLS` | RAND biology and chemistry |
| 03c | 12 | `SEAL_SPEC`, `SEAL_SKIP` | Scale SEAL boards |
| 03d | 14 | `LIVE_TASK_SPEC`, `LIVE_TASK_SKIP` | Epoch live feed |
| 03e | 16 | `KAGGLE_SPEC` | Kaggle boards |

Adding a benchmark is a notebook edit. Adding a name is a file edit.

## Your own runs

Aggregate scores from local eval runs enter as
`data/curated/row_adds_YYYY-MM-DD_<name>.csv` (8-column schema + `reason`;
the notebook appends them after the curated drops and raises on collision
with a feed). Keep the reproducibility package — grader prompt, config,
raw per-item results — in `data/evals/<name>/` (see its README).

## Scripts

- `scripts/serve.sh` — starts the server and opens the dashboard.
- `scripts/serve.py` — serves the page on port 8130 and backs the Refresh and
  Curate tabs (`/api/snapshots`, `/api/run`, `/api/queue`, `/api/curate`). It
  answers on localhost only, and it does not serve `.git/`, `snapshots/`, or
  `intermediate/`.
- `scripts/check.py` — post-refresh gate **and** the swap: validates
  `data/pipeline/output/` (schema, field counts, no duplicate
  `(model, benchmark)` cell, a row floor derived from the file being replaced,
  non-empty baselines and report) and only then copies it into
  `data/{processed,curated}/`.
- `scripts/test_pipeline.py` — asserts the standing invariants against the
  committed files (no duplicate cells, no stacked config suffixes, one category
  per benchmark, no unreachable alias rows). Run it after `check.py`.

## License note

Epoch AI data is CC-BY; RAND is cited under RR-A3797-1; Kaggle boards are
public JSON. Scale SEAL rows carry no open license (fair-use research
aggregation): resolve before making this repo public. It is private.
