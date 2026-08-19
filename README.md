# eval-data-pipeline

Canonical home for the benchmark score data and the pipeline that refreshes
it. Extracted from the ECI Bayesian modeling repo; the full history of
`data/` came along. Consumers (the ECI fits, future projects) read the
files below. Nothing here depends on any modeling code.

## The interface

Open `index.html` through a local server (browsers block `fetch` from
`file://`):

```bash
python3 -m http.server 8000
```

then visit <http://localhost:8000>. Four views: **Browse** (filter the
merged table by model, benchmark, source, category, organization, date
range; sort; chance floor shown per row), **Benchmarks** (one row per
benchmark: category, notes, chance floor, coverage), **Download**
(filtered slice as CSV, plus the raw files), **Report** (the latest
pipeline refresh report).

## Paths of truth

| File | What it is |
|---|---|
| `data/processed/benchmarks_merged.csv` | the merged table: `model_version,score,release_date,organization,benchmark,stderr,source,category` |
| `data/curated/human_baselines.csv` | human tiers as test-takers |
| `data/curated/*.csv` | per-benchmark facts (chance floors, ceilings, item counts, score clips) and curated corrections |
| `data/pipeline/canonical/*` | name/alias maps and benchmark metadata |
| `data/pipeline/output/pipeline_report.md` | provenance report of the last refresh |

Future projects clone this repo and read those paths. No API layer.

## Refreshing

Open `data/pipeline/pipeline.ipynb`, Restart Kernel → Run All (needs
pandas, numpy, requests — no modeling stack). Section 10 swaps outputs
into `data/{processed,curated}/`. Then:

```bash
python3 scripts/check.py
```

and commit. Full pipeline docs (the five feeds, merge policy, guards) in
[`data/pipeline/README.md`](data/pipeline/README.md). Same-UTC-day re-runs
reuse the snapshot folder; `snapshots/` and `intermediate/` are gitignored
and regenerable.

## Your own runs

Aggregate scores from local eval runs enter as
`data/curated/row_adds_YYYY-MM-DD_<name>.csv` (8-column schema + `reason`;
the notebook appends them after the curated drops and raises on collision
with a feed). Keep the reproducibility package — grader prompt, config,
raw per-item results — in `data/evals/<name>/` (see its README).

## Scripts

- `scripts/check.py` — post-refresh gate: paths exist, merged CSV schema
  and row count hold, the section-10 swap ran, report non-empty.
- `scripts/build_lineage_map.py` — regenerates
  `data/curated/lineage_map.csv` from the merged table after a refresh;
  never hand-edit the map.

## License note

Epoch AI data is CC-BY; RAND is cited under RR-A3797-1; Kaggle boards are
public JSON. Scale SEAL rows carry no open license (fair-use research
aggregation): resolve before making this repo public. It is private.
