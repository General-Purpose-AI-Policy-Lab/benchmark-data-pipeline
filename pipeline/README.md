# Data pipeline — refreshable, sourced from upstream

One notebook (`pipeline.ipynb`) that pulls a dated snapshot of Epoch AI's
public benchmark ZIP (CC-BY, refreshed ~weekly) and assembles a
`benchmarks_merged.csv` matching the schema `data.py` already consumes.

The current `data/processed/benchmarks_merged.csv` is built by a separate
notebook (`process_benchmarks/1_Merge_and_filter.ipynb`) from two
hand-managed files in `data/raw/`, which go stale immediately when Epoch
publishes new results. This pipeline replaces that workflow with a
self-refreshing online fetch.

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
│       └── provenance.json              {url, fetched_at, sha256, license}
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
    ├── content_diff_vs_current.csv      score deltas vs existing dataset
    └── pipeline_report.md               provenance summary
```

## Parameters

All at the top of section 00. Change them there.

| Parameter | Default | Effect |
|---|---|---|
| `EPOCH_ZIP_URL` | `https://epoch.ai/data/benchmark_data.zip` | Source URL |
| `APPLY_CURATED_EXCLUSIONS` | `False` | If `True`, drop benchmarks in `data/curated/excluded_benchmarks.txt`. Off keeps the canonical broad-index config. |
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

## Sources

| Section | Source | License | Benchmarks |
|---|---|---|---|
| 01 (Epoch) | `epoch.ai/data/benchmark_data.zip` | CC-BY (Epoch AI) | Reasoning, math, QA, multimodal, agentic — 45 benchmarks |
| 03b (RAND) | [`benchmark-forecasting`](https://github.com/General-Purpose-AI-Policy-Lab/benchmark-forecasting/blob/main/Data/benchmark_data_RAND/benchmark_scores_RAND.csv) — digitized from RAND **RR-A3797-1** (Dev et al. 2025, *Toward Comprehensive Benchmarking of the Biological Knowledge of Frontier LLMs*) | Citation: [RR-A3797-1](https://www.rand.org/pubs/research_reports/RRA3797-1.html) | Biology + chemistry safety suite (WMDP, LAB-Bench, MMLU/MMLU Pro Bio/Chem, GPQA Diamond/Main Bio/Chem, BioLP-bench) — 15 benchmarks |

When citing analysis built on this pipeline, credit both Epoch AI and the
RAND techreport.

## Out of scope for v1 (out-of-band, manual)

These benchmarks are in the legacy dataset but not yet covered:

- **Scale SEAL** (12 benchmarks: PRBench Finance/Legal, VISTA, EnigmaEval, MultiNRC, MultiChallenge, AudioMultiChallenge, TutorBench, SWE-Bench Pro, VisualToolBench, MCP Atlas, Remote Labor Index). Hosted on `scale.com/leaderboard/...`. No public API — needs an HTML scraper, written as `section 01c` once available.
- **GeoBench & GDPVal** are in Epoch's ZIP but skipped in `FILE_SKIP` because the score scale is ambiguous (GeoBench is multi-axis, GDPVal is win-rate-vs-other-models). 5-minute fix once you commit to one column.
- **SWE-Bench Bash Only** — genuinely not in Epoch's ZIP this week.
- **OSUniverse**, **Lech Mazur Writing** — Lech Mazur is already in via Epoch's `lech_mazur_writing_external.csv`. OSUniverse is on GitHub (`agentsea/osuniverse`), no central leaderboard.

If you have CSVs for any of the Scale benchmarks, drop them into the
current snapshot folder and add a `FILE_SPEC` entry in section 03 — they'll
be picked up automatically.

## License

Epoch AI benchmark data is **CC-BY**. Cite Epoch AI when publishing analysis
based on this pipeline's output.
