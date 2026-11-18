# evals/: the lab's own benchmark runs

Scores no public feed carries, measured by the lab when a forecasting model needs them (the first
ones fill the cells of Multiaxis_ECI's data wishlist that best separate the modes of its K=4
flagship). They enter the pipeline as the feed `gpai_runs`, like any other source.

## What a run publishes

`0_input/feed/gpai_runs/runs/<run_id>/`, one folder per run (`<YYYYMMDD>_<model>_<regime>_<benchmarks>`):

| File | Content |
|---|---|
| `manifest.json` | the protocol (reference, template, parser, shuffle, scoring), request parameters, model id returned by the API, dataset URL and sha256, software versions and the script's sha256, token counts, the results per benchmark (score, clustered stderr, score per epoch, stop reasons, unparsed answers), the run's history and audit notes, and the sha256 of the other files |
| `samples.csv` | one row per question and epoch: record id, target and parsed answer, correct, stop reason, refusal category, tokens, whether the model reasoned visibly, the completion's length and sha256, message and request ids, start time. **No question or completion text.** |
| `transcripts.zip` | the full log, one JSON line per call with the completion, behind GPQA's published password (`deserted-untie-orchid`), first line the canary strings of the datasets that have one (GPQA, LAB-Bench) |

`0_input/feed/gpai_runs/scores.csv` holds one row per (model, benchmark, run): `model` is the
pipeline's machine name (`claude-sonnet-5_none`), `score` the mean over questions and epochs,
`stderr` the standard deviation of the per-question means over the square root of the number of
questions (clustered by question, so it counts item sampling, not only the model's), with
`n_items`, `n_epochs` and `run_id`. `tests/test_gpai_runs.py` recomputes every row from the run's
`samples.csv` and checks the manifest's hashes.

**Why the transcripts are zipped.** GPQA's and LAB-Bench's authors ask that their questions never
appear in plain text online, and completions quote them. The archive follows their own practice for the dataset
(a password-protected zip whose password is published, plus a canary string), which keeps the
log out of web crawls without hiding it from a reader.

## Protocols

`rand_protocol.py`: the biology and chemistry benchmarks of the `rand` feed (GPQA Main / Diamond
Biology / Chemistry, WMDP Biology / Chemistry, LAB-Bench LitQA2 / Protocol / SeqQA / Cloning,
MMLU and MMLU-Pro Biology / Chemistry) under RAND's protocol (RR-A3797-1, Dev et al. 2025,
chapter 2 and appendices B and D), so that a new row is on the same footing as RAND's:

- inspect_ai's `multiple_choice()` single-answer template, verbatim, and its answer parser
  (commit `ccdc03f`): no chain-of-thought instruction, no few-shot examples;
- the choices shuffled, per question and epoch (`random.Random(f"{record_id}|{epoch}")`);
- provider defaults for every sampling parameter; `max_tokens` 16,000 by default, thinking
  included (`--max-tokens` raises it, streamed above 16,000); RAND's Inspect default is not stated;
- unparseable answers scored incorrect; refusals and answers cut at `max_tokens` are not scored
  (see below);
- one departure from Inspect's parser, for answers that are unambiguous but that it misses: the
  template's `$` copied literally (`ANSWER: $D`, which Claude Sonnet 4.6 writes in about a quarter
  of its MMLU answers) a final `<answer>D</answer>` tag with no ANSWER line, and an ANSWER line glued to a visible
  `</think>` tag (both Claude Opus 5, which writes such tags with thinking disabled).
  Scoring those as wrong would measure a formatting habit. The strict Inspect score stays in the
  manifest (`score_inspect_strict`, `n_normalised`) and in `samples.csv` (`answer_strict`);
- several epochs where RAND ran one: the mean has the same expectation with less sampling noise;
- RAND's subsets, checked against its question counts at load time. Every file is pinned (URL at
  a fixed revision, sha256). MMLU's "college-level" subjects of RAND's appendix B are in fact
  `high_school_biology` + `virology` (536) and `high_school_chemistry` (230), all three splits:
  only those match RAND's counts.

**Commonsense benchmarks (campaign of 2026-11-12).** The same template, parser and shuffle also
run OpenBookQA (test, 500), ARC AI2 (ARC-Challenge test, 1,172), HellaSwag (validation, 10,042),
PIQA (validation, 1,838) and WinoGrande (xl validation, 1,267), on which no model released after
2024 had a score; one epoch, since the sets are large. They are not RAND's benchmarks, and older
rows of these benchmarks in other feeds were mostly measured few-shot or by log-likelihood, not
with this template. GSM8K (test, 1,319), whose answer is a number, uses the prompt of
inspect_evals' `gsm8k` task (commit `50b8b19`: "step by step", the answer on a last `ANSWER:`
line) with no few-shot example, so the model reasons in its visible answer whatever the thinking
regime. Its answer is read on the last `ANSWER:` line and counts when the target is one of the
numbers written there (`225 minutes (3 hours and 45 minutes)`, `6th place`, `2:00 PM`);
Inspect's `match(numeric=True)`, which takes the last number of the completion, stays in the
manifest as `score_inspect_strict`. Reading the wrong answers of the strongest runs shows label
noise on all six (wrong or ambiguous gold answers; on HellaSwag nearly all in its ActivityNet
half): about 1 point of each score, so a practical ceiling near 0.98-0.99. The published gold
labels are kept, as every other score of these benchmarks uses them.

**TriviaQA (prepared 2026-11-18, no run published yet).** Closed-book TriviaQA, whose last
published frontier score dates from July 2023, has a protocol of its own (`TRIVIAQA_TEMPLATE`,
`parse_text`): the validation split of `rc.wikipedia.nocontext` (7,993 questions), the "Wiki
validation subset" of the filtered dev set on which the Llama 2 paper reports the series' best
score; zero-shot, the answer on an `ANSWER:` line; exact match after the normalisation of
TriviaQA's official script against the question's aliases. A pilot (Claude Haiku 5.5 and Opus
5.5, 100 to 200 questions) shows what exact match costs a chat model: the aliases are short
("crawford", "colorado", "george") and a fuller correct answer ("Joan Crawford", "Colorado
River", "King George III") misses them, about 10 points at every level (Opus 5.5 at max effort:
0.88 by exact match, 0.98 with an alias contained in the answer). The published rows are few-shot
completions, whose examples teach the short form. Which rule the score uses is to be decided
before any run is packaged.

A call refused by the API's safety layer can be run again (`run --retry-refusals N`, up to N
times each until it is answered; every attempt is kept in `<log>.superseded.jsonl`). In this
campaign the refusals did not yield: the same questions were refused five more times in every
run concerned (HellaSwag row 6425 for Sonnet 5.5 and Opus 5.5, WinoGrande rows 401 and 402 for
Haiku 5.5 and Opus 4.8).

Where the reproduction is less certain (kept in each manifest under `protocol.notes`): RAND wrote
its own LAB-Bench formatting without publishing it (here the ideal answer plus the distractors,
the protocol above the question for ProtocolQA), and it reports using Inspect's existing MMLU and
MMLU-Pro tasks, whose current versions read the test split only and cap answers at a few tokens
without chain of thought; the appendix-D template is used for them too.

**Calls without an answer: refusals and cut answers.** The API's safety layer can decline a
question (`stop_reason: refusal`, with a category), and a long reasoning can run into the
`max_tokens` budget (`stop_reason: max_tokens`). Neither is an answer, so neither is scored wrong
(user, 2026-10-15, for cut answers: a budget is a measurement setting, not the model's
capability). Refusals depend on the question, not on the draw (Claude Sonnet 5 refuses 95% of
the WMDP Biology questions it ever refuses in every epoch, whatever the order of the choices),
and they fall on harder questions than average (Claude Haiku 4.5, which answers everything,
scores 0.80 on those and 0.85 on the others), so "answered questions only" would be biased
upwards too. A call without an answer is treated as missing and gets the score the model is
expected to earn on that question (`impute_missing`; the `credit` and `imputation` columns of
`samples.csv`):

- `own`: when the run finished the same question in other epochs, its mean score there;
- `rasch` otherwise: a Rasch model with fixed item difficulties, taken from every other
  published run on the benchmark, and the model's level fitted on the run's answers to it.

Checked on the cut calls later run again with a larger budget (16,000 to 32,000 tokens for
Sonnet and Opus, 32,000 to 64,000 for Haiku 5.5 at max effort; 165 finished): the imputation
stays within a few points of the scores measured, where scoring the cut calls wrong is off by
0.4 to 0.8. A forced answer would score less (about 0.30 on the 25 cut answers read by hand,
against 0.40 measured with more budget): the imputation targets the capability, since the cut
is the budget's. A variant fitting the level on the long answers only did better on cuts
simulated at 2,000-4,000 tokens but worse at 8,000 and above, where real cuts happen, and was
dropped (2026-10-16).

The manifest keeps
RAND's score (`score_refusals_wrong`, missing = wrong), the refusal and cut shares, the fitted
shift, and the list of cut calls (`protocol.truncated_calls`), which `run` and `package` also
print. Cut calls are best run again with a larger budget (`run --retry-truncated --max-tokens
32000`, the new rows replace the cut ones and the old rows go to `<log>.superseded.jsonl`). A cell
where more than 30% of the calls have no answer would rest mostly on the imputation: it is
reported under `excluded_from_scores` and left out of `scores.csv` (`MAX_MISSING_SHARE`); Claude
Sonnet 5 on WMDP Biology is one. Since the difficulties come from the other runs, `package` is run
again on every run with missing calls once all runs of a campaign are in.

The model's regime is the suffix of the pipeline's name grammar: `none` sends thinking disabled,
an effort level (`low` ... `max`) sends adaptive thinking at that effort, `<N>K` a thinking budget
of N thousand tokens.

## Reproduce a run, or run a new one

```bash
export ANTHROPIC_API_KEY=...        # never committed; evals/raw/ and evals/.cache/ are gitignored
uv run evals/rand_protocol.py run --model claude-sonnet-5 --regime none --epochs 4 \
    --bench "GPQA Main Chemistry" --bench "GPQA Diamond Chemistry" \
    --out evals/raw/20261014_claude-sonnet-5_none_gpqa-chemistry.jsonl
uv run evals/rand_protocol.py package evals/raw/20261014_claude-sonnet-5_none_gpqa-chemistry.jsonl \
    --run-id 20261014_claude-sonnet-5_none_gpqa-chemistry --model claude-sonnet-5 --regime none \
    [--notes notes.json]            # history / audit notes merged into the manifest
.venv/bin/python -m benchmark_data build && .venv/bin/pytest -q
```

`run` downloads the datasets itself and checks their sha256, pins its dependencies
(`anthropic`, `pandas`, `pyarrow`, PEP 723 header), and is resumable: rerunning the same command retries only
the calls missing from the log. Sampling is at the provider's default temperature, so a rerun
reproduces the score within its stderr, not answer for answer; the recorded transcripts are the
reference. A model the API no longer serves cannot be rerun at all, which is why the full log is
kept.

Before packaging, read the wrong answers: an API error, a refusal, a completion cut by
`max_tokens` or an answer the parser missed is a measurement problem, not a model error. Note
what was checked in the manifest (`--notes`, key `audit`).
