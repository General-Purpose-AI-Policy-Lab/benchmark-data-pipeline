# data/curated/

Small hand-reviewed inputs that shape the fits. Two kinds live here — check
the table before editing:

| File | Kind | Consumed by | Edit by hand? |
|---|---|---|---|
| `excluded_benchmarks.txt` | hand-maintained list | `data.py` (applied at fit time, canonical preset only) | yes — one benchmark name per line, `#` comments allowed |
| `human_baselines.csv` | hand-selected, this is the authoritative file | `data.py` (humans as IRT test-takers); pipeline notebook (reads it as input) | yes — add new baselines here by hand. On refresh the notebook reads this file, canonicalizes benchmark names, appends RAND-extracted baselines, and round-trips it via `output/` |
| `sota_models.txt` | generated | `config.SOTA_MODELS` (plot exemptions + drop-filter protection) | no — regenerate with `python diagnostics/compute_sota.py` after a data/fit refresh |
| `lineage_map.csv` | generated draft, then hand-reviewed | `lineage.py` (lineage prior), `diagnostics/compute_sota.py` (flagship chains) | yes — it is the reviewed source of truth; `diagnostics/build_lineage_map.py` drafts new rows |
| `row_drops_YYYY-MM-DD.csv` | dated audit record | pipeline notebook (anti-join: these rows are removed on every refresh) | append-only — new audit, new dated file |
| `row_fixes_YYYY-MM-DD.csv` | dated audit record | nothing reads it — it documents fixes that were applied through the notebook's name/config parsing; kept as the audit trail | append-only |
| `benchmark_lower_bounds.csv` | hand-reviewed, sourced — authoritative (all 85 floors verified against primary sources 2026-07-13) | `data.py` `load_benchmark_floors` for the `--floors` fixed-c 3PL fit (opt-in, exploration only) | yes — `benchmark, lower_bound, reason, source_url`; edit directly, then sanity-check with `diagnostics/audit_lower_bounds.py` |
| `benchmark_score_clips.csv` | generated draft, then reviewed | `data.py` `clip_scores_to_floors` APPLIES these row-level clips at fit time (`--floors` only) — the explicit record of every score the fit modifies; drift vs the current data/floors warns loudly | no — refresh with `diagnostics/audit_lower_bounds.py --write-clips` after a data or floor change, review the diff, commit |

The `_YYYY-MM-DD` suffix on the row-audit files is the date of the data audit
that produced them. Each audit adds a new dated pair rather than editing an
old one, so the history of manual row surgery stays reconstructible.

Schema of the row-audit files:
`model_version, benchmark, score, source, reason` — enough to identify the
exact offending row and why it was dropped/fixed.

## `_unknown` model variants — expected, not a bug

A model appears as both a bare `X` and an `X_unknown` test-taker when the
source data records it in more than one run configuration: `_unknown` collects
thinking-mode or unspecified-effort rows, the bare name is the base config.
These are kept as **separate test-takers**, matching the `_low`/`_high`
effort-variant convention — merging them would mix configs.

Two consequences a data reader will notice:

- **Divergent scores** on the same benchmark (e.g. a thinking vs base
  TerminalBench number) are the point of the split — genuinely different runs.
- **Identical scores** on a handful of cells (~6 of ~4,000 rows) come from
  Epoch's own upstream double-logging: Epoch's external CSVs occasionally list
  the same model twice, once bare and once `_unknown`, with the same score
  (distinct Airtable record IDs, different evaluation dates). The pipeline
  mirrors the source faithfully, so these carry through. Benign — identical
  scores don't move any fit.
