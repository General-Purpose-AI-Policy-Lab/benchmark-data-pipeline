# every_eval_ever: pertinence assessment

Assessed 2026-08-19 against schema v0.3.0 and the live datastore.

**Result.** Do not adopt every_eval_ever (EEE) as the internal format. Our
data fits its schema with two lossy corners (release date, category), but
the shape is wrong for our workflow: 5,064 score cells become 5,064 JSON
files where one 580 KB CSV does the job. EEE is pertinent in three other
roles, in decreasing order of value: a design cross-check (already
banked), a candidate sixth ingest feed, and an export target if the data
is ever published.

## What it is

EEE is the EvalEval Coalition's standardized evaluation-results database:
a JSON Schema (v0.3.0, MIT license) plus a Hugging Face datastore
(`evaleval/EEE_datastore`, 108 benchmark collections, updated daily,
~11,500 downloads). One JSON record per evaluation run, filed as
`data/{benchmark}/{developer}/{model}/{uuid}.json`. Per-sample results are
an optional JSONL sidecar; aggregate-only records are fully supported,
which is our case. Contribution is by pull request with schema
validation. The repo ships converter adapters for ~20 sources (HELM,
Inspect AI, lm-evaluation-harness, ARC-AGI, HLE, leaderboard scrapes).

## How our columns map

Our merged schema is 8 columns per (model, benchmark) cell. The mapping:

| Ours | EEE | Fit |
|---|---|---|
| score | `evaluation_results[].score_details.score` | clean |
| stderr | `score_details.uncertainty.standard_error.value` | clean; `num_samples` also takes our n_eff work |
| benchmark | `evaluation_name` + required `metric_config.lower_is_better` and `source_data` | clean; floors/ceilings map to `min_score`/`max_score` |
| model_version | `model_info.name` / `id` | clean; their guidance puts effort variants in `evaluation_id`, not the model id, matching our variant convention but making the variant a run property rather than a test-taker |
| organization | `model_info.developer` | clean |
| source | `source_metadata` (`source_type: documentation` for leaderboard rows, `evaluator_relationship` first/third party) | clean, richer than ours |
| release_date | none | gap: goes to `additional_details`, a string map |
| category | none | gap: same |

Required fields we do not carry: `eval_library` (fallback `"unknown"` is
sanctioned), `retrieved_timestamp` (our snapshot date serves),
`evaluation_id` (derivable from source + model + benchmark + date).

## Why not as the internal format

- One JSON file per cell. Our 5,064 cells and every refresh diff become
  thousands of files against one CSV the pipeline already
  reads, dedups, and content-diffs.
- The two gaps sit on columns the fits depend on. release_date drives the
  era filters, the time prior, and the lineage clock; category drives the
  axis maps. Both would live in an untyped string map.
- Effort variants as run metadata instead of test-taker identity would
  need re-flattening on every load to recover our
  one-row-per-(taker, benchmark) panel.

## Where it is pertinent

1. **Design cross-check, already banked.** Their conversion guide
   independently converges on rules this pipeline learned the hard way:
   exact longest-first name matching (their example is `gpt-4.1-mini`
   swallowed by a `gpt-4.1` prefix rule), one shared developer map instead
   of per-source maps, variant axes kept out of the model id, org-owned
   sources only. Independent convergence is evidence both designs are
   right.
2. **Candidate sixth ingest feed.** The datastore covers benchmarks we
   already track (MMLU-Pro, ARC-AGI, FrontierMath, GPQA Diamond,
   SWE-bench Verified, HLE) plus agentic ones we lack. Same admission
   test as Kaggle: verify each collection's identity from its own
   uncertainty fields before trusting it, and watch their naming hygiene
   (the store holds both `gpqa-diamond` and `gpqa_diamond`). Worth a
   scoped trial when the pipeline next needs coverage, not before.
3. **Export target.** If this data is ever published, EEE is the natural
   interchange: the mapping above is a small script, their validator
   gates submissions, and local eval packages kept under `data/evals/`
   with raw harness logs are exactly what their Inspect/HELM converters
   consume. Moot while the repo is private.

## Recommendation

Keep the CSV as the working format. Revisit EEE at the next coverage
push (as feed) or at first publication (as export). No code now.
