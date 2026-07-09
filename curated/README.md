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

The `_YYYY-MM-DD` suffix on the row-audit files is the date of the data audit
that produced them. Each audit adds a new dated pair rather than editing an
old one, so the history of manual row surgery stays reconstructible.

Schema of the row-audit files:
`model_version, benchmark, score, source, reason` — enough to identify the
exact offending row and why it was dropped/fixed.
