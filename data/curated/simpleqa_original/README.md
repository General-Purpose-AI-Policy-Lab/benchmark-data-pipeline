# SimpleQA (original)

SimpleQA (Wei et al., OpenAI, arXiv 2411.04368) is a 4,326-question benchmark
of short, fact-seeking questions with a single verifiable answer, graded
correct / incorrect / not-attempted by a prompted grader model. The score
here is "overall correct": percent of all questions answered correctly.

## Why a separate column from "SimpleQA Verified"

SimpleQA Verified (Google DeepMind, arXiv 2509.07968) re-filters and
re-grades a subset of the same underlying questions with a different grader
and different question inclusion criteria. The two are not psychometrically
comparable: different item pool, different grader, different pass/fail
boundary per item. `benchmark = "SimpleQA"` here is kept distinct from
`"SimpleQA Verified"` for that reason.

## Chance floor

0. Open-ended free-text answer, no multiple-choice options, so there is no
guessing floor.

## Fetch date

2026-08-05.

## Provenance

**Source 1 — [openai/simple-evals README](https://github.com/openai/simple-evals/blob/main/README.md)**
(MIT license), "Benchmark Results" table, SimpleQA column. Covers the
majority of rows: o3 (high/medium/low), o4-mini (high/medium/low), o3-mini
(high/medium/low), o1, o1-preview, o1-mini, GPT-4.1 / mini / nano, GPT-4o
(2024-05-13 / 2024-08-06 / 2024-11-20), GPT-4o-mini, GPT-4.5-preview,
GPT-4-turbo-2024-04-09, Claude 3.5 Sonnet, Claude 3 Opus. Scores read off the
table verbatim and divided by 100.

Reasoning-effort mapping for the plain "o3" / "o3-mini" / "o1" README rows
(no `-high`/`-low` suffix) follows the same "generic name -> default effort
= medium" convention already used in `canonical/model_aliases.csv` for these
model families, so they map to the `_medium` canonical IDs. The
effort-less "o1-mini" row maps to `_unknown`, matching the existing
"effort-less -> `_unknown`" convention for SEAL rows.

**Source 2 — [SimpleQA paper, Table 3](https://arxiv.org/abs/2411.04368)**
(page 7). Used for two models the current README table does not carry at
all: `claude-3-haiku-20240307` (5.1% correct) and `claude-3-sonnet-20240229`
(5.7% correct).

**Source 3 — official vendor reports.** Searched xAI's Grok 2 announcement,
the Gemini 1.5 technical report, and Meta's Llama 3.1 model card for a
SimpleQA (original) number. None report one — SimpleQA postdates all three
releases and none of these vendors re-ran it retroactively on these specific
checkpoints in a citable official document. Later reports (Grok 3, Gemini
2.0+) report SimpleQA only for their own newer models, not for Grok 2 /
Gemini 1.5 / Llama 3.1. These three model families are therefore absent from
this dataset rather than estimated.

## Discrepancies (paper vs. README, same or overlapping model)

The README table postdates the paper and gives an exact dated snapshot per
row; the paper's Table 3 uses undated generic names for some rows. Where
both report a number, the README value was kept (more specific, more
recent) and the paper's number is logged here rather than silently dropped:

| model | README (used) | paper Table 3 |
|---|---|---|
| o1-preview-2024-09-12 | 0.424 | 0.427 |
| o1-mini-2024-09-12 | 0.076 | 0.081 ("o1-mini", no date given) |
| gpt-4o-mini-2024-07-18 | 0.095 | 0.086 ("GPT-4o-mini", no date given) |

The paper's undated "GPT-4o" row (0.382) was not added as a separate line:
it is ambiguous between the three dated GPT-4o snapshots already in this
file (2024-05-13 / 2024-08-06 / 2024-11-20) and none of their README values
match it exactly, so mapping it to one specific snapshot would be a guess.

Claude 3.5 Sonnet (0.289) and Claude 3 Opus (0.235) agree exactly between
the two sources.

## Needs review

None. Every row above was mapped to an existing canonical `model_version`
in `data/processed/benchmarks_merged.csv` with high confidence (exact
dated-snapshot string match, or the documented default-effort convention).
