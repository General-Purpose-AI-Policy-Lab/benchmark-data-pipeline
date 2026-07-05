# Augmented sources — supplementary, fit-time only

These CSVs were added **after** the main data pipeline (Epoch + RAND + Scale
SEAL → `data/processed/benchmarks_merged.csv`). They are **not** part of that
notebook and are **never** written into `benchmarks_merged.csv`. They are folded
into a fit only on demand, via `load_eci_data(augment=True)` / the `--augment`
CLI flag, under the rules in [`augment.py`](../../augment.py):

- **existing-models-only** — a row is kept only if its model, after
  canonicalization through the shared `data/pipeline/canonical/model_aliases.csv`,
  is already in the database. No new test-takers are introduced (this keeps the
  model index — and the lineage / human-tier priors keyed on it — unchanged).
- **add-only-new-cells** — a row is kept only if its `(model, benchmark)` pair
  isn't already in the database, so an augmented score never double-counts an
  observation the main fit already has.
- unmatched source models are dropped and listed in `unmatched_models.csv`
  (regenerate with `python scripts/build_augment_report.py`) for incremental
  alias curation.

All three files share the 9-column schema of `benchmarks_merged.csv`
(`model_version, score, release_date, organization, benchmark, stderr, source,
lower_bound, category`); Steel adds a passthrough `reported_date` that
`augment.py` drops. Scores are on the raw `[0,1]` scale. Fetched **2026-07-03**.

## Files

### `helm_classic.csv` — legacy-model back-fill
- **Source:** Stanford CRFM **HELM Classic v0.3.0**, raw results in the public
  GCS bucket `gs://crfm-helm-public/classic/benchmark_output/releases/v0.3.0/`
  (per-benchmark tables under `groups/*.json`). Landing page:
  <https://crfm.stanford.edu/helm/classic/latest/>. License: HELM data is
  released for research use (Apache-2.0 codebase; per-scenario dataset licenses vary).
- **Fetched by:** [`scripts/fetch_helm_classic.py`](../../scripts/fetch_helm_classic.py).
- **Preprocessing:** for each mapped HELM group, take the **primary
  accuracy-like metric** (column 1 of each table; lower-is-better blocks such as
  inference-time are skipped), keep the best block per model, then keep a
  `(benchmark, model)` row only if it isn't an exact duplicate of an Epoch cell
  (raw-name gap-fill; the fit-time alias step + add-only-new-cells does the
  authoritative dedup). ~1,400 rows, 25 benchmarks, 79 models.
- **Why:** HELM Classic evaluated the 2022–2023 legacy fleet (GPT-3 family,
  GPT-J, GPT-NeoX, BLOOM, OPT, LLaMA-1/2, Falcon, MPT, T5, …) on modern hard
  benchmarks (MATH, MMLU, GSM8K, HumanEval, APPS, TruthfulQA, …). Those models
  are in our DB under different name formats (`LLaMA (65B)` → `LLaMA-65B`), so
  the alias map recovers them — addressing the era-confound (old models only
  ever evaluated on easy benchmarks → extrapolated hard-axis ability).

### `livebench.csv` — contamination-controlled aggregate
- **Source:** **LiveBench** public leaderboard table, raw asset
  `table_2026_01_08.csv` from the deploy repo
  <https://github.com/LiveBench/livebench.github.io> (`public/`), with the
  category map `categories_2026_01_08.json`. Site: <https://livebench.ai>.
  Per-question judgments also mirrored on HuggingFace
  (`livebench/model_judgment`).
- **Fetched by:** [`scripts/fetch_livebench.py`](../../scripts/fetch_livebench.py).
- **Preprocessing:** overall score = **mean of category means** (each category
  mean = mean of its task columns) across the 7 LiveBench categories, then
  normalised 0–100 → `[0,1]`. One `LiveBench` row per model, 127 models.
  `LiveBench` already exists as a benchmark in the DB, so under add-only-new-cells
  these rows only fill models that lacked a LiveBench score.

### `steel_dev.csv` — agentic-axis fill
- **Source:** **Steel.dev agent leaderboard index**,
  <https://leaderboard.steel.dev/results/> — a server-rendered aggregation of
  ~13 agent benchmarks (SWE-bench Verified, Aider, OSWorld, WebVoyager,
  WebArena, GAIA, tau-bench, BrowseComp, Terminal-Bench, …), each row sourced
  from papers / model cards / launch posts. Aggregation by Steel.dev; cite the
  underlying benchmark for any single number.
- **Fetched by:** [`scripts/fetch_steel_dev.py`](../../scripts/fetch_steel_dev.py).
- **Preprocessing:** parse each `<tr class="lb-row">`'s `data-*` attributes and
  cells; percentages → proportion (`72.5%` → 0.725). 311 rows, 13 benchmarks,
  253 models. Its new agentic benchmarks (OSWorld, WebArena, GAIA, WebVoyager,
  BrowseComp, tau-bench, …) are absent from the DB, so they enter as new
  benchmarks for the models we already track.

## Refresh

Re-run the matching `scripts/fetch_*.py` (each is standalone and idempotent),
then `python scripts/build_augment_report.py` to regenerate the unmatched-models
worklist and curate `model_aliases.csv` for any newly-added models.
