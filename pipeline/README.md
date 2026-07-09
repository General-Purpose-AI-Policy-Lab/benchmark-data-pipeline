# Data pipeline — refreshable, sourced from upstream

One notebook (`pipeline.ipynb`) that pulls a dated snapshot of Epoch AI's
public benchmark ZIP (CC-BY, refreshed ~weekly) and assembles a
`benchmarks_merged.csv` matching the schema `data.py` already consumes.

This notebook is the authoritative refresh path for
`data/processed/benchmarks_merged.csv`. It replaces an earlier two-notebook
workflow (archived under `archive/legacy_pipeline.zip`) that built the
processed file from a hand-managed snapshot in `data/raw/` — that snapshot
went stale immediately when Epoch published new results.

## Refresh workflow

1. Open `pipeline.ipynb` from this directory and **Restart Kernel → Run All**.
2. Inspect `output/pipeline_report.md`:
   - Snapshot date + ZIP sha256
   - Row counts at each stage
   - Top-10 score changes vs the current dataset (sanity check)
   - Any benchmarks missing metadata (= you need to edit `canonical/benchmark_metadata.csv`)
   - Any new models since the last review (= you may want to edit `canonical/model_aliases.csv`)
3. If satisfied, swap the outputs into the project tree:
   ```bash
   cp output/benchmarks_merged.csv ../processed/benchmarks_merged.csv
   cp output/human_baselines.csv   ../curated/human_baselines.csv
   ```
4. Re-run the model: `python run.py` from the repo root.

Re-running the notebook within the same UTC day reuses today's snapshot
folder (no re-download). To force a refresh, delete `snapshots/YYYY-MM-DD/`
before running.

## Folder layout

```
data/pipeline/
├── README.md                            (this file)
├── pipeline.ipynb                       the single notebook — sections 00 → 09
├── canonical/                           human-edited, version-controlled
│   ├── benchmark_names.csv              variant → canonical benchmark name
│   ├── model_aliases.csv                variant → canonical model_version
│   └── benchmark_metadata.csv           benchmark → category, lower_bound
├── snapshots/                           gitignored; one folder per fetch
│   └── YYYY-MM-DD/
│       ├── epoch_benchmark_data.zip
│       ├── epoch/                       unzipped CSVs
│       ├── provenance.json              {url, fetched_at, sha256, license}
│       └── seal/                        Scale SEAL raw HTML + provenance
│           ├── <slug>.html              cached page per leaderboard
│           └── seal_provenance.json     {fetched_at, per-slug sha256, n_rows}
├── intermediate/                        gitignored; CSV per stage
│   ├── 02_scores_long.csv
│   ├── 03_scores_named.csv
│   └── 04_scores_deduped.csv
└── output/                              reviewed manually, then swapped in
    ├── benchmarks_merged.csv            matches data/processed/ schema
    ├── human_baselines.csv              matches data/curated/ schema
    ├── duplicates_report.csv            any (model, benchmark) collisions
    ├── name_changes.csv                 every variant → canonical rename
    ├── missing_models.csv               models not yet in alias map
    ├── seal_alias_review.csv            proposed (unapplied) SEAL model aliases
    ├── content_diff_vs_current.csv      score deltas vs existing dataset
    └── pipeline_report.md               provenance summary
```

Sections run `00 → 09`, with `03b` (RAND) and `03c` (Scale SEAL) between
the Epoch load (03) and canonicalization (04).

## Parameters

All at the top of section 00. Change them there.

| Parameter | Default | Effect |
|---|---|---|
| `EPOCH_ZIP_URL` | `https://epoch.ai/data/benchmark_data.zip` | Source URL |
| `APPLY_CURATED_EXCLUSIONS` | `False` | If `True`, drop benchmarks in `data/curated/excluded_benchmarks.txt` here. Kept **off** — the pipeline emits every benchmark and the exclusion list is applied at *fit time* by `data.py` (`load_eci_data`, default), so the processed file is the complete record. |
| `DEDUP_POLICY` | `"max"` | Resolution for the rare case of disagreeing duplicates on `(model, benchmark)`. Exact-row dupes are always dropped regardless. |
| `ECI_EPS` | `1e-3` | Open-interval clip for humans (matches `data.py`). |

## Provenance trace

Every row is traceable back through the intermediate CSVs
(`_source_file`, `_source_row`, `_score_col` columns preserved) to a
specific row in a specific CSV inside `snapshots/YYYY-MM-DD/epoch/`. Keep
the snapshot folder for audit purposes.

The per-file mapping (filename → benchmark name + score column + divisor)
lives in `FILE_SPEC` at the top of section 03 of the notebook. When Epoch
publishes a new file, section 03 prints it as "unrecognized" — add a row
there.

## Model aliasing — how generic names get resolved

The RAND data uses pretty model names (`o3`, `Claude 3.5 Sonnet`, `GPT 4o`)
while Epoch carries dated, fully-specified IDs (`o3-2025-04-16_medium`,
`claude-3-5-sonnet-20240620`, `gpt-4o-2024-08-06`). Two policies are
worth considering:

- **(a) Default-variant mapping** — pick one Epoch ID per generic name
  (e.g. `o3` → `o3-2025-04-16_medium`). RAND's bio/chem rows then merge
  with that Epoch row, contributing extra observations to the same model
  in the IRT.
- **(b) Treat unmapped as separate** — leave the generic name as-is,
  fit it as its own test-taker. Honest to the input data but the IRT
  sees `o3` and `o3-2025-04-16_medium` as different models.

**This pipeline uses (a).** Reasoning: when RAND's report says "we ran
o3 on WMDP Biology", the evaluation was almost certainly conducted at
the default reasoning effort (medium) on the latest available snapshot
at eval time. Treating it as a separate test-taker would split capability
posteriors across what are effectively the same model under two names.
The cost is small: the few cases where the generic name actually maps
to a non-default variant become a known source of bias in the bio/chem
posteriors for those specific models.

**Edge case — fine-tunes are *not* aliased.** Three RAND model rows are
deliberately **dropped** rather than mapped, via the empty-canonical
sentinel in `canonical/model_aliases.csv`:

| RAND name | Drop reason |
|---|---|
| `Llama 3.1 405b (Bio Llama)` | RAND-specific biology fine-tune. Its WMDP/LAB-Bench scores reflect that bio-specific post-training, not base-model capability. Including it would confound the capability axis. |
| `Llama 3.1 405b (Hermes 3)` | NousResearch chat fine-tune. Different post-training pipeline than Meta's Instruct; pooling with `Llama-3.1-405B-Instruct` is incorrect, but treating as a separate test-taker adds noise with only 11 obs. |
| `Unsafety Llama` | Uncensored fine-tune. Its bio/chem benchmark scores reflect *willingness to answer* hazardous prompts, not the underlying capability. Confounds the index with safety-training removal. |

To re-include any of these, restore a canonical Epoch ID (or the variant
name itself) in `model_aliases.csv` — section 04 logs every drop with
its justification on each run, so the effect is visible in the report.

The full mapping is in `canonical/model_aliases.csv` — 36 RAND names
mapped to default Epoch IDs, 3 dropped, with one-line justifications
in the `note` column.

## Scale SEAL leaderboards (section 03c)

Scale's [SEAL leaderboards](https://labs.scale.com/leaderboard) are scraped
live. There is **no public CSV/API**: each board is a Next.js page that
server-renders its rows into `self.__next_f` streaming chunks (the visible
HTML `<table>` is a stale snapshot, so we parse the chunks, not the table).
Each board exposes an `entries` array of `{model, score,
confidenceInterval_upper, company, createdAt, deprecated, ...}`, scores 0–100.

- **`SEAL_SPEC`** (`slug → (benchmark, divisor, status)`) lists the 15 boards
  ingested. **Slugs come from Scale's Sanity CMS** — query
  `https://5uhyv5jy.apicdn.sanity.io/v2022-03-07/data/query/production?query=*[_type=="leaderboard"]{"slug":slug.current,title}`
  for the full, current list. Note hyphens/short forms: `prbench-finance`,
  `vtb`, `rli`, `audiomc` (not the underscored guesses).
- **`SEAL_SKIP`** records boards omitted by **score scale**, not fetchability:
  `coding` and multilingual `arabic/chinese/japanese/spanish` are Elo-rated
  (~600–1240), and the text-only HLE would collide with Epoch's full HLE.
- Raw HTML per slug + `seal_provenance.json` (per-slug sha256, row counts,
  parse method) are cached in `snapshots/<date>/seal/` for reproducibility.
- `createdAt` is the leaderboard-add date, **not** a model release date, so
  `release_date` is left null (mirrors RAND); `company` populates `organization`.
- The ± confidence interval is **not** captured — the long-frame schema carries
  no `stderr` downstream (Epoch's measured stderr is likewise dropped). Wiring
  stderr end-to-end is a tracked follow-up.

**SEAL model aliasing.** SEAL uses messy, inconsistent model names
(`Claude 3.5 Sonnet (October 2024)`, `o3 (high) (April 2025)`,
`gpt-5.4 (xHigh)*`). They are matched to Epoch IDs in `canonical/model_aliases.csv`:

- date → versioned ID, explicit effort tokens → Epoch's `_high/_medium/_xhigh/_max`
  suffixes, and effort-less reasoning runs → the `_unknown` (or `_none`) bucket.
- **"thinking"/"non-thinking" variants are kept as *distinct* test-takers**,
  consistent with the project's effort-variants-are-distinct convention
  (`collapse_effort_variants=False`) — they are *not* merged into the base model.
- Every alias target is validated to exist in the Epoch set before it is
  applied; genuinely new models (e.g. SEAL audio models, `Muse Spark`) stay as
  their own test-takers. Proposed-but-unapplied matches are written to
  `output/seal_alias_review.csv` for manual review.

## Sources

| Section | Source | License | Benchmarks |
|---|---|---|---|
| 01 (Epoch) | `epoch.ai/data/benchmark_data.zip` | CC-BY (Epoch AI) | Reasoning, math, QA, multimodal, agentic — ~45 benchmarks |
| 03b (RAND) | [`benchmark-forecasting`](https://github.com/General-Purpose-AI-Policy-Lab/benchmark-forecasting/blob/main/Data/benchmark_data_RAND/benchmark_scores_RAND.csv) — digitized from RAND **RR-A3797-1** (Dev et al. 2025, *Toward Comprehensive Benchmarking of the Biological Knowledge of Frontier LLMs*) | Citation: [RR-A3797-1](https://www.rand.org/pubs/research_reports/RRA3797-1.html) | Biology + chemistry safety suite (WMDP, LAB-Bench, MMLU/MMLU Pro Bio/Chem, GPQA Diamond/Main Bio/Chem, BioLP-bench) — 15 benchmarks |
| 03c (Scale SEAL) | `labs.scale.com/leaderboard/<slug>` (scraped from `__next_f`; slugs from Scale's Sanity CMS) | **Not CC-BY** — Scale AI ToS; used as fair-use research aggregation, attribute Scale AI | EnigmaEval, MCP Atlas, MultiChallenge, MultiNRC, VISTA, TutorBench, SEAL Tool Use, SWE-Bench Pro (public+private), SEAL Instruction Following, PRBench Finance/Legal, Remote Labor Index, VisualToolBench, AudioMultiChallenge — 15 benchmarks |

When citing analysis built on this pipeline, credit Epoch AI, the RAND
techreport, and Scale AI.

## Out of scope / not ingested

- **OSUniverse** — `agentsea/osuniverse` on GitHub is a run-it-yourself
  benchmark *framework* (no published model×score leaderboard); scores exist
  only in its paper. Not ingestable as a model×score table without manual
  extraction.
- **SEAL Elo boards** — `coding` and multilingual `arabic/chinese/japanese/spanish`
  use Elo-style ratings (~600–1240), incompatible with the `[0,1]` Beta model.
- **SEAL boards left out of the canonical index** (reachable, not yet added):
  safety (Fortress, MASK, PropensityBench), Math, Tool Use (Chat), SWE Atlas ×3,
  SciPredict, HiL-Bench, Korean. One-line additions to `SEAL_SPEC` if wanted.
- **GDPVal** — in Epoch's ZIP but skipped in `FILE_SKIP`: win-rate-vs-other-models,
  not an absolute [0,1] capability.
- **GeoBench — ingested, but only the `ACW Country %` column.** GeoBench is a
  multi-axis file (ACW/AVW/Rural/Urban/Photos splits × Avg/Median/Distance/Country%/Refusal).
  Its headline `ACW Avg Score` is a GeoGuessr *points* score (~0–5000, seen
  2131–4333) — not a [0,1] proportion, so it can't feed the Beta model. The one
  clean, full-coverage (n=32) [0,1] column is `ACW Country %` — the fraction of
  images whose country the model names correctly — so that is what `FILE_SPEC`
  ingests as benchmark **GeoBench**. It lines up with the curated 0.90
  "top player" human baseline (best model ≈ 0.88). The other splits are sparse
  (AVW/Rural/Urban n=3, Photos n=16) and left out.
- **Lech Mazur Writing** — already ingested via Epoch's `lech_mazur_writing_external.csv`.

## License

Epoch AI benchmark data is **CC-BY**. RAND scores are cited under RR-A3797-1.
**Scale SEAL data carries no open license** — it is aggregated here as fair-use
research with attribution to Scale AI; confirm terms before publishing derived
analysis. Cite all three sources when publishing analysis based on this output.
