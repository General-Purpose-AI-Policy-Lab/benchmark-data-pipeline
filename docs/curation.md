# Curation guide

Curation is deciding what the feeds cannot decide: which raw names are the
same test-taker, which upstream files are which benchmark, and what metadata a
benchmark needs before a fit can use it. Decisions live in three tracked
files: [`canonical/model_aliases.csv`](../data/pipeline/canonical/model_aliases.csv)
(variant → canonical model name, 390 rows), [`canonical/reviewed_models.txt`](../data/pipeline/canonical/reviewed_models.txt)
(850 names already reviewed), and [`canonical/benchmark_metadata.csv`](../data/pipeline/canonical/benchmark_metadata.csv)
(benchmark → category, 104 rows). The Curate tab performs the mechanical
appends; this guide holds the rules.

## 1. The review loop

Refresh (notebook Run-All, or the Refresh tab), then read the report (Report
tab, or [`output/pipeline_report.md`](../data/pipeline/output/pipeline_report.md)).
Three queues can appear:

1. **New models** — `output/missing_models.csv`, 29 models as of 2026-08-19.
   Act in the Curate tab. Rules in section 2.
2. **Benchmarks missing metadata** — the report nags until a row lands in
   `benchmark_metadata.csv`. Act in the Curate tab. Rules in section 3.
3. **Unrecognized feed files or tasks** — the 2026-08-19 report lists
   `mirrorcode.csv` (ZIP) and `MirrorCode` / `OEIS Open` / `OEIS Open Lite`
   (live feed). These need a spec entry or a skip reason, which is a notebook
   edit in section 3 of `pipeline.ipynb`. Rules in section 3 below.

A curation decision applies on the NEXT run. To apply it offline, replay the
same snapshot: put its date in the Refresh tab's date field (no re-download).

## 2. New models

**Queue rule.** A name queues iff its resolved identity is in neither
`model_aliases.csv`'s variant column nor `reviewed_models.txt`. Resolved means
after two steps: trailing `*`/`†` markers are stripped, then the alias map is
applied. The strip runs first because, per the notebook (cell 18), trailing
markers are "score-provenance footnotes (self-reported etc.), NOT model
identity" and keeping them "split one model into marker-variant phantoms".

**Three decisions**, one per queued name:

- **Review** — a genuinely new model whose queued form is already canonical.
  Append the name to `reviewed_models.txt`. Example, reviewed 2026-08-19:
  `nova-2.0-pro-preview_unknown`.
- **Alias** — another spelling of a known test-taker. Append
  `variant,canonical,note` to `model_aliases.csv`. Real rows:
  `Qwen3-235B-A22B,qwen3-235b-a22b,defrag: case-only duplicate` and
  `o3,o3-2025-04-16_medium,RAND generic 'o3' -> default reasoning effort = medium`.
- **Drop** — a name whose scores should not enter the table at all. An alias
  row with an EMPTY canonical is the drop sentinel; the note is required
  because it is printed on every run. Real row: `Unsafety Llama,,"DROP —
  uncensored fine-tune; bio/chem scores reflect willingness to answer, not
  capability"`.

**Choosing the canonical name.** Canonical = Epoch's `Model version` spelling.
In practice that is lowercase-dash-dated (`claude-3-5-sonnet-20241022`), but
the Epoch registry's own casing wins (`Qwen3-235B-A22B-Thinking-2507`).
Validate that an alias target exists in the data before writing it. Matching
is byte-exact and case-sensitive, never fuzzy or prefix: a prefix rule
swallows longer names, the `gpt-4.1-mini` example in
[`every_eval_ever.md`](every_eval_ever.md). Case-only and
provider-prefix duplicates get `defrag:` alias rows onto the canonical form.

**Effort variants.** Canonical form is `<base>_<effort>` with vocabulary
`minimal|low|medium|high|xhigh|max|none` plus `_<N>K` thinking budgets and
`_unknown`. Every variant is its own test-taker and its own
`reviewed_models.txt` line. `_unknown` is the unspecified-effort bucket;
notebook cell 8 treats it as a placeholder and substitutes the real effort in
when the human-readable `Name` label states one. A generic vendor name maps to
the default variant (`o3` → `o3-2025-04-16_medium`): the eval was almost
certainly run at default effort, and a separate test-taker would split one
model's posterior across two names (policy (a) in the
[pipeline README](../data/pipeline/README.md#model-aliasing--how-generic-names-get-resolved)).
Thinking and non-thinking runs are never merged.

**Downstream contract.** The modeling repo's `data.py` strips variants back to
a base model with

```python
_EFFORT_SUFFIX_RE = re.compile(
    r"_(?:low|medium|high|minimal|max|xhigh|none|unknown|web-?app|"
    r"\d+K|reasoning-(?:low|medium|high))$"
)
```

A new suffix outside that vocabulary must be added there in the same change,
or the variant silently becomes its own base model. That happened with
`_none`: per the regex's own comment, leaving it out made all 15 `_none`
test-takers their own base models, "which silently defeated
collapse_effort_variants and the lineage's variant collapse for those rows".

## 3. New benchmarks

**Detection.** Three allowlist/skiplist pairs in the notebook: `FILE_SPEC` /
`FILE_SKIP` for the Epoch ZIP, `LIVE_TASK_SPEC` / `LIVE_TASK_SKIP` for the
live feed, `SEAL_SPEC` / `SEAL_SKIP` for Scale SEAL. A file or task in neither
dict is reported, never silently ingested or silently dropped. An entry in
both raises (skip is checked first, so the spec line would be dead). The
decision is a spec entry (benchmark name, score column, divisor or transform)
or a skip with a reason string. The 2026-08-19 report shows the two-transport
case: `mirrorcode.csv` in the ZIP and `MirrorCode` in the live feed are the
same benchmark arriving twice. The rule, from the pipeline README, is prefer
the ZIP for any board Epoch publishes.

**Naming rules.** Never merge different instruments under one name: GDPval and
GDP.pdf share no models and measure different things; FrontierMath v1 and v2
are separate benchmarks because v2 shifted the level +0.20 with the ranking
intact. The canonical name DOES survive a problem-set version swap on the same
instrument (the `source` column records the version, e.g.
`EpochAI (FrontierMath v2)`). Check score direction on every new column: sort
it and confirm known-strong models land high. A loss column ingested as-is
inverts the ability axis.

**Required rows** for an ingested benchmark:

- [`canonical/benchmark_metadata.csv`](../data/pipeline/canonical/benchmark_metadata.csv)
  — a category. The report nags until it is added. The 10 categories in use
  (104 rows): Domain Specific Questions (16), Autonomous SWE (15), General
  Reasoning (14), Agentic Computer Use (14), Multimodal Understanding (10),
  Biology (10), Core AGI Progress (7), High End Math Reasoning (7), Advanced
  Language and Writing (6), Chemistry (5).
- [`data/curated/benchmark_lower_bounds.csv`](../data/curated/benchmark_lower_bounds.csv)
  — the chance floor, deliberately kept out of the metadata file (110 rows,
  75 of 110 are 0). Multiple choice gets 1/k; a non-MC benchmark gets 0
  (inert) or a stated uninformed baseline (ForecastBench 0.5, the score of an
  uninformed guess on its Brier index).
- [`data/curated/benchmark_n_items.csv`](../data/curated/benchmark_n_items.csv)
  — item count plus a verification stamp (`UNVERIFIED`, or the evidence kind:
  `primary-source`, `score-grid`, `not-item-mean`, `stderr-inversion`; 91 rows). This feeds the n_eff identity guard, which checks a board's
  claimed identity against the item count its own confidence intervals imply.
- [`data/curated/benchmark_upper_bounds.csv`](../data/curated/benchmark_upper_bounds.csv)
  — only for a measured ceiling, 2 rows today (FrontierMath v1 and Tier 4 v1,
  from their measured problem-set error rates).

`canonical/benchmark_names.csv` holds variant → canonical benchmark spellings.
Currently all 45 of 45 rows are identity: no benchmark rename has been needed
yet, but the map is where one would go.

## 4. Variables

Section-00 parameters (`EPOCH_ZIP_URL`, `APPLY_CURATED_EXCLUSIONS`,
`DEDUP_POLICY`, `ECI_EPS`) are documented in the
[pipeline README's parameter table](../data/pipeline/README.md#parameters).
One knob is not in that table: `SNAPSHOT_DATE`, an environment variable read
in the snapshot cell of the notebook, replays an existing snapshot folder
instead of fetching. The Refresh tab's date field sets it.

Curated files: which ones to edit by hand, and how, is the
[edit-by-hand table in `data/curated/README.md`](../data/curated/README.md).
Locally measured cells enter as `data/curated/row_adds_YYYY-MM-DD_<name>.csv`
(8-column schema plus a `reason` column; see the
[repo README](../README.md#your-own-runs)). The notebook appends them after
the curated drops and RAISES on collision with a feed. The fix for that raise
is retiring the manual rows, not deduplicating: when the 2026-08-19 refresh
brought the inkling ARC ladder and the AA cells in through the feeds, the two
row_adds files were deleted (commit f2e70e2; the paired refresh commit
dff5696 records the reason).

## 5. Known gaps

- `_thinking` (8 rows of 5,247), `_promax` (4), and `_prounknown` (1) are not
  matched by `_EFFORT_SUFFIX_RE`, so effort-collapse treats those names as
  their own base models. The fix belongs in the modeling repo's regex, not in
  renames here.
- The queue tests alias VARIANTS, not targets: an alias target that is absent
  from `reviewed_models.txt` re-queues on every refresh. Append targets to
  `reviewed_models.txt` when adding alias rows.
