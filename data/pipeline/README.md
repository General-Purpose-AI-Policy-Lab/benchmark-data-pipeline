# Data pipeline — refreshable, sourced from upstream

One notebook (`pipeline.ipynb`) that pulls a dated snapshot of Epoch AI's
public benchmark ZIP (CC-BY, refreshed ~weekly) and assembles a
`benchmarks_merged.csv` matching the schema `data.py` already consumes.

This notebook is the authoritative refresh path for
`data/processed/benchmarks_merged.csv`.

## Refresh workflow

1. Open `pipeline.ipynb` from this directory and **Restart Kernel → Run All**.
2. Inspect `output/pipeline_report.md`:
   - Snapshot date + ZIP sha256
   - Row counts at each stage
   - Top-10 score changes vs the current dataset (sanity check)
   - **Any unrecognized upstream files** (= new benchmarks in the feed; map them
     in `FILE_SPEC` or skip them with a reason in `FILE_SKIP`). This section was
     added 2026-07-27: the list had previously existed only in the notebook cell
     output, so seven benchmarks sat unmapped for at least one refresh cycle
     while the report looked clean.
   - Any benchmarks missing metadata (= you need to edit `canonical/benchmark_metadata.csv`)
   - Any new models since the last review (= you may want to edit `canonical/model_aliases.csv`)
3. Run the gate, which is what puts the outputs into the tree:

   ```bash
   python3 scripts/check.py
   ```

   It validates `output/` — schema, field counts, no duplicate
   `(model, benchmark)` cell, a row floor derived from the file it is about to
   replace, non-empty baselines and report — and only then copies into
   `data/processed/` and `data/curated/`. A failed check leaves the previous
   data in place. Revert an accepted swap with
   `git checkout data/processed data/curated`.
4. Optionally assert the standing invariants: `python3 scripts/test_pipeline.py`.
5. Re-fit in the modeling repo, which reads
   `data/processed/benchmarks_merged.csv` from here.

Re-running the notebook within the same UTC day reuses today's snapshot
folder (no re-download). To force a refresh, delete `snapshots/YYYY-MM-DD/`
before running.

## Folder layout

```
data/pipeline/
├── README.md                            (this file)
├── pipeline.ipynb                       the single notebook — sections 00 → 10
├── canonical/                           human-edited, version-controlled
│   ├── benchmark_names.csv              variant → canonical benchmark name
│   ├── model_aliases.csv                variant → canonical model_version
│   ├── benchmark_metadata.csv           benchmark → category (+ notes)
│   └── reviewed_models.txt              model names already reviewed for aliasing
├── snapshots/                           gitignored; one folder per fetch
│   └── YYYY-MM-DD/
│       ├── epoch_benchmark_data.zip
│       ├── epoch/                       unzipped CSVs
│       ├── provenance.json              {url, fetched_at, sha256, license}
│       ├── epoch_live_benchmarks.csv    epoch.ai/data/benchmarks.csv (internal evals)
│       ├── live_provenance.json         {url, fetched_at, sha256, used_for}
│       ├── rand_benchmark_scores.csv    the digitized RAND table (section 03b)
│       ├── kaggle/                      one JSON per Open Benchmarks board (03e)
│       └── seal/                        Scale SEAL raw HTML + provenance
│           ├── <slug>.html              cached page per leaderboard
│           └── seal_provenance.json     {fetched_at, per-slug sha256, n_rows}
├── intermediate/                        gitignored; CSV per stage
│   ├── 02_scores_long.csv
│   ├── 03_scores_named.csv
│   └── 04_scores_deduped.csv
└── output/                              validated and swapped by scripts/check.py
    ├── benchmarks_merged.csv            matches data/processed/ schema
    ├── human_baselines.csv              matches data/curated/ schema
    ├── duplicates_report.csv            any (model, benchmark) collisions
    ├── name_changes.csv                 every variant → canonical rename
    ├── missing_models.csv               models not yet in alias map
    ├── seal_alias_review.csv            FROZEN manual-review artifact from the
    │                                    modeling repo; nothing here writes it
    ├── name_audit.csv                   FROZEN manual-review artifact; produced by
    │                                    the modeling repo's audit_model_names.py
    ├── content_diff_vs_current.csv      score deltas vs existing dataset
    │                                    (header-only = no deltas found)
    └── pipeline_report.md               provenance summary
```

Sections run `00 → 10`, with `03b` (RAND), `03c` (Scale SEAL), `03d`
(live feed) and `03e` (Kaggle) between the Epoch load (03) and canonicalization
(04). Section 10 writes nothing into the tree: `scripts/check.py` validates
`output/` and performs the swap.

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

- **`SEAL_SPEC`** (`slug → (benchmark, divisor, status)`) lists the 14 boards
  ingested. `rli` is deliberately kept even though Epoch ships
  `rli_external.csv`: it is a PARTIAL overlap, not a duplicate (ZIP 11 models,
  board 15, union 19), so dropping the scrape would lose 8 models. **EnigmaEval left this list on 2026-07-27**: its board stopped
  serving rows to the scraper (47 → 5) and Epoch now ships the full file in the
  ZIP, with stderr and CI bounds, so it is ingested via `FILE_SPEC` in section
  03. Prefer the ZIP for any board Epoch starts publishing.
  **Slugs come from Scale's Sanity CMS** — query
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
- The Curate tab validates an alias target against the merged data before
  writing the row, and section 04 warns on any target that is absent at run time;
  genuinely new models (e.g. SEAL audio models, `Muse Spark`) stay as
  their own test-takers. Proposed-but-unapplied matches are written to
  `output/seal_alias_review.csv` for manual review.

## Epoch internal evals — the live feed (section 03d)

The published ZIP lags the site whenever a benchmark's **problem set** changes,
and its per-benchmark CSVs carry no version column to tell the series apart.
FrontierMath v2 was released 2026-06-12, correcting errors in 42% of problems.
Six weeks later the ZIP still exported only pre-update runs, while the epoch.ai
pages had switched to the v2 re-runs.

The fix is a second Epoch feed: `epoch.ai/data/benchmarks.csv`, the table the
benchmark pages actually read. It carries every internal-eval run with a `task`
name and a `task version` stamp, so a specific problem set can be selected.

**Every Epoch internal eval is read from this feed**, not just FrontierMath:
the seven that also ship in the ZIP (Chess Puzzles, GPQA Diamond, MATH Level 5,
OTIS Mock AIME, SWE-Bench Verified, SimpleQA Verified, Mystery Game Puzzles) are
byte-identical there
(same run ids, same scores, identical model ids, 0 mismatches — verified
2026-07-28), so routing them here gives every internal eval one transport at no
cost in rows. Their ZIP files sit in `FILE_SKIP`. The ZIP remains the source for
all *external* benchmarks. `LIVE_TASK_SKIP` records the tasks deliberately not
ingested, so a genuinely NEW task in the feed is reported instead of silently
ignored — the same guard section 03 has for unmapped ZIP files.

Caveat worth knowing: `task version` is a **harness** version for most tasks
(Chess Puzzles has 8 distinct values, GPQA 12), not a problem-set marker. Only
FrontierMath uses it as one, and even there the real discriminator is the `task`
NAME (`-v2-Private`). So the version pin is per-task and `None` for the rest.

- **`LIVE_TASK_SPEC`** carries **twelve** tasks, not two. Besides the two v2
  FrontierMath sets it maps the two v1 sets (kept as their own benchmarks), the
  seven internal evals that also ship in the ZIP (Chess Puzzles, GPQA Diamond,
  MATH Level 5, OTIS Mock AIME, SWE-Bench Verified, SimpleQA Verified, Mystery
  Game Puzzles) and `EBR-bench`, which has no ZIP file at all. Private sets only,
  matching the ZIP convention (only twelve problems are public, so the public
  splits are far too small to model). Read the dict for the current list.
- **The canonical benchmark names are kept.** The curated floors, the exclusion
  list, and every downstream figure keep resolving. What changed is which
  problem set those names refer to. `source` records it as
  `EpochAI (FrontierMath v2)`.
- Every accepted row is asserted to carry a `2.x` `task version`, and the stage
  fails if any row already claims those benchmark names — a guard against the
  v1 `FILE_SPEC` entries being silently un-skipped.
- The v1 ZIP files are in **`FILE_SKIP`**, not `FILE_SPEC`. The two series are
  **not pooled**: v2 shifted the score level by about +0.20 on Tiers 1-3 while
  leaving the ranking intact (paired *r* = 0.988, n = 18), so one benchmark
  column would carry a bimodal difficulty.

**No coverage is lost.** v1 is re-ingested from the same live feed as its own
benchmark rather than discarded: `FrontierMath v1` (101 rows) and
`FrontierMath Tier 4 v1` (72 rows) sit alongside `FrontierMath` (48) and
`FrontierMath Tier 4` (50). A model never re-run on v2 keeps its observation
under the v1 name. As its own item each version gets its own `D`, `A` and
`sigma_b`, so the defective v1 instrument reads as a low-discrimination noisy
one instead of contaminating the v2 scale.

**Watch item.** Ability estimates from before and after this change are not
comparable on FrontierMath difficulty. `D` falls sharply, because the same
benchmark name now refers to an easier-scoring instrument.

**The same pattern hit FrontierCode on 2026-07-27.** Epoch stopped publishing
`Diamond score` and now reports `Main score`. This is *not* a header rename: on
the 3 models present in both snapshots `Main` runs 6-8x higher (`gpt-5.5`
0.063 → 0.430), so it is an easier subset, and the model set largely turned over
(11 rows → 19, only 3 shared). `Diamond` no longer exists upstream, so it cannot
be kept current; `FILE_SPEC` reads `Main score` and FrontierCode difficulty is
likewise **not comparable across this change**. Watch for this whenever a score
column disappears: check overlapping models before assuming a rename.

## Kaggle Open Benchmarks

Endpoint: `https://www.kaggle.com/api/v1/benchmarks/<owner>/<slug>/leaderboard`,
public JSON, no auth. The first INDEPENDENTLY RE-RUN source in the pipeline:
the other five feeds are vendor self-reports or leaderboard scrapes, and every
Kaggle row carries a binomial 95% confidence interval, so this is the first
feed to supply real per-row stderr at scale (`--known-se`, in the modeling repo, currently has
stderr on about a quarter of cells).

**Boards ingested**, each merged per its own `kaggle_wins` boolean:

| Kaggle slug | → benchmark | kaggle_wins | models | policy |
|---|---|---|---|---|
| `open-benchmarks/mmlu` | MMLU | `True` | 51 | Kaggle authoritative on collisions; the ZIP's 136 rows backfill the rest, 180 obs total |
| `open-benchmarks/mmlu-pro` | MMLU-Pro | `True` | 55 | the sole source for this column |
| `deepmind/simpleqa-verified` | SimpleQA Verified | `False` | 46 | our Epoch-live-feed column wins every collision; Kaggle fills the 25 models we lack |

**`open-benchmarks/mmlu` → MMLU, kaggle_wins=True.** No offset is detectable
against the existing column: 7 overlapping models, mean +0.021, sd 0.044,
p = 0.25, and the construct is identical (57 subjects, 4 choices, 0.25 floor).
Replacing the column outright was rejected: 128 non-Kaggle rows have
no Kaggle equivalent, and 8 test-takers would leave the fit if dropped.
Kaggle wins on the collisions and the ZIP backfills the rest, for 179 obs.

**`open-benchmarks/mmlu-pro` → MMLU-Pro, kaggle_wins=True.** Kaggle is the sole
source for this column, at 55 rows. The alternative is TIGER-Lab's
own leaderboard
([`TIGER-Lab/mmlu_pro_leaderboard_submission`](https://huggingface.co/datasets/TIGER-Lab/mmlu_pro_leaderboard_submission/blob/main/results.csv)),
which mixes rows TIGER-Lab ran with rows the model vendors submitted, and
splitting its offset against Kaggle by that distinction is what decides the
question: the TIGER-Lab-run rows agree with Kaggle (9 models, mean -0.007,
p = 0.35), the vendor-submitted rows do not (16 models, mean -0.026, p = 0.014,
worst case `claude-3-7-sonnet` 0.840 vs 0.719). Vendor optimism, not an
instrument difference, so the independently re-run board is the one to trust.
Its 55 models span 0.383-0.917. Chance floor 0.10 (10 answer options).

**`deepmind/simpleqa-verified` → SimpleQA Verified, kaggle_wins=False.** Our
Epoch-live-feed column is already the better instrument here: 77 models,
single source, stderr on 77/77, and correctly
effort-tagged. It wins every collision. Kaggle contributes only the
models we lack (38 rows today), filed as `_unknown` effort, because Kaggle publishes no
effort suffix and its rows cannot be filed to a specific test-taker. Filing
them under a real effort tag would be worth up to 14 points: our
`gpt-5.4-2026-03-05_xhigh` scores 0.448 against Kaggle's untagged 0.305.

### The n_eff identity guard

A board's identity is verified from its own confidence interval, not its
documentation. Each Kaggle row's binomial 95% CI implies an effective item
count, `n_eff = p(1-p)/(ci/1.96)^2`, which should match the benchmark's known
item count if the board is what it claims to be:

| board | implied n_eff | true item count |
|---|---|---|
| MMLU | 14,043 | 14,042 |
| MMLU-Pro | 12,032 | 12,032 (exact) |
| SimpleQA Verified | ~938 | 1,000 |

The same reasoning settles the prompt configuration, which Kaggle does not
state. On MMLU-Pro the gap against TIGER-Lab's own runs is 0.7 points, far
under the ~20 points a chain-of-thought-versus-direct mismatch produces, so
Kaggle's MMLU-Pro board runs chain-of-thought.

**Rejected boards:**

| Kaggle slug | reason |
|---|---|
| `bobfraserg/gsm8k` | personal account, not org-owned; scores run to 65,250 with a CI of 0 |
| `open-benchmarks/aime-2025` | CI reported as 0, no usable stderr on a 30-item exam |
| `open-benchmarks/math-500` | CI implies 8,000 items for a 500-item set |

Corollary rule: **org-owned boards only, never personal accounts.**

**SciCode — examined, not ingested.** Kaggle's SciCode board reports a
Subproblem-level CI implying n_eff 291, i.e. all 288 subproblems treated as
independent items. `data/curated/benchmark_n_items.csv` records SciCode as
65 independent units: the 288 subproblems nest inside 65 problems, and the
harness feeds each problem's earlier solutions forward, so the subproblems
are not independent trials. Kaggle's stderr would therefore run about 2.1x
too tight. SciCode stays sourced from the Epoch ZIP (`scicode_external.csv`,
itself a republish of Artificial Analysis); Kaggle's 39-model overlap
corroborates that column (offset -0.027, corr 0.894) without replacing it.

## Score columns that need a transform (`FILE_SCORE_TRANSFORM`)

Some upstream columns are not a `[0,1]` capability proportion. `FILE_SCORE_TRANSFORM`
maps those onto one, applied after the divisor. A transform is only admissible if
the reference it is measured against is **exogenous** — a fixed baseline, a
published human figure, a library implementation. Anything measured against the
other models on a leaderboard stays out entirely: no rescaling repairs it,
because the quantity is not a property of the model (see `FILE_SKIP` for
`frontierswe` and `webdev_arena`).

**Currently one entry: AlgoTune.** The board reports a harmonic-mean speedup
`s >= 1` against a fixed library implementation (SciPy / sklearn / CVXPY), so
`1 - 1/s` is the fraction of the original runtime eliminated: `s=1` maps to 0,
`s=2` to 0.5, and the observed 1.31–2.05x to 0.237–0.512, all interior.
Unbounded above in principle, so 1.0 means infinite speedup and is unreachable;
the 4PL ceiling stays inert at `d=1` rather than inventing a finite cap.

**Check the direction whenever a score column is added.** Sort by the column and
confirm the known-strong models land on the high end. A column where lower is
better (a loss) inverts the ability axis if ingested as-is, and it still passes
the `[0,1]` range assertion.


## Sources

| Section | Source | License | Benchmarks |
|---|---|---|---|
| 01 (Epoch) | `epoch.ai/data/benchmark_data.zip` | CC-BY (Epoch AI) | Reasoning, math, QA, multimodal, agentic — 59 `FILE_SPEC` entries |
| 03d (Epoch live) | `epoch.ai/data/benchmarks.csv` — version-tagged internal evals | CC-BY (Epoch AI) | Every Epoch internal eval — 12 tasks in `LIVE_TASK_SPEC`, ~1,200 rows (23% of the table) |
| 03b (RAND) | [`benchmark-forecasting`](https://github.com/General-Purpose-AI-Policy-Lab/benchmark-forecasting/blob/main/Data/benchmark_data_RAND/benchmark_scores_RAND.csv) — digitized from RAND **RR-A3797-1** (Dev et al. 2025, *Toward Comprehensive Benchmarking of the Biological Knowledge of Frontier LLMs*) | Citation: [RR-A3797-1](https://www.rand.org/pubs/research_reports/RRA3797-1.html) | Biology + chemistry safety suite (WMDP, LAB-Bench, MMLU/MMLU Pro Bio/Chem, GPQA Diamond/Main Bio/Chem, BioLP-bench) — 15 benchmarks |
| 03c (Scale SEAL) | `labs.scale.com/leaderboard/<slug>` (scraped from `__next_f`; slugs from Scale's Sanity CMS) | **Not CC-BY** — Scale AI ToS; used as fair-use research aggregation, attribute Scale AI | MCP Atlas, MultiChallenge, MultiNRC, VISTA, TutorBench, SEAL Tool Use, SWE-Bench Pro (public+private), SEAL Instruction Following, PRBench Finance/Legal, Remote Labor Index, VisualToolBench, AudioMultiChallenge — 14 benchmarks (EnigmaEval moved to the Epoch ZIP, 2026-07-27) |

When citing analysis built on this pipeline, credit Epoch AI, the RAND
techreport, and Scale AI.

## Out of scope / not ingested

- **BTF3 — examined, not ingested.** A pooled Brier/RPS *loss*. The `1 - loss`
  inversion is sound, but the floor is not derivable: a coin-flip binary
  forecaster scores Brier 0.25 (index 0.75), yet the pooled score also weights a
  normalized numeric RPS 3x per question (392 numeric vs 1515 binary) whose
  uninformative level is unpublished. Parked rather than shipping a guessed
  chance floor. In `FILE_SKIP`.
- **Vending-Bench 2 — ingested 2026-07-29, retired 2026-08-04.** Scored by the
  dollar bank balance after a simulated year, so it needed a log transform onto
  `[0,1]`. Retired because the panel cannot identify the loading row: 54 rows but
  only 3 informative takers, so the loading direction was set by whatever the
  rest of the fit settled into. The dollar transform also put it on a scale no
  other benchmark shares. In `FILE_SKIP`.

- **OSUniverse** — `agentsea/osuniverse` on GitHub is a run-it-yourself
  benchmark *framework* (no published model×score leaderboard); scores exist
  only in its paper. Not ingestable as a model×score table without manual
  extraction.
- **SEAL Elo boards** — `coding` and multilingual `arabic/chinese/japanese/spanish`
  use Elo-style ratings (~600–1240), incompatible with the `[0,1]` Beta model.
- **SEAL boards left out of the canonical index** (reachable, not yet added):
  safety (Fortress, MASK, PropensityBench), Math, Tool Use (Chat), SWE Atlas ×3,
  SciPredict, HiL-Bench, Korean. One-line additions to `SEAL_SPEC` if wanted.
- **GDPval and GDP.pdf are two different benchmarks, both ingested (2026-07-27).**
  `gdpval_external.csv` is OpenAI's GDPval (blinded win rate against a fixed
  human-expert deliverable). `gdp_pdf_external.csv` is Surge AI's
  [GDP.pdf](https://surgehq.ai/leaderboards/gdp-pdf) leaderboard, a multimodal
  benchmark over real-world professional PDFs; `GDP.pdf` is its literal name
  (Epoch's score column is `GDP.pdf score`), not a filename artifact. The two
  share no models (0 of 12 × 11) and measure different things, so they are
  **never merged** under one canonical name.
- **GeoBench — ingested, but only the `ACW Country %` column.** GeoBench is a
  multi-axis file (ACW/AVW/Rural/Urban/Photos splits × Avg/Median/Distance/Country%/Refusal).
  Its headline `ACW Avg Score` is a GeoGuessr *points* score (~0–5000, seen
  2131–4333) — not a [0,1] proportion, so it can't feed the Beta model. The one
  clean, full-coverage (n=31) [0,1] column is `ACW Country %` — the fraction of
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
