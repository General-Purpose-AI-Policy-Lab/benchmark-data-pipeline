# MMLU-Pro (full, overall score)

MMLU-Pro (Wang et al., TIGER-Lab, NeurIPS 2024, [arXiv 2406.01574](https://arxiv.org/abs/2406.01574))
is a 12,032-question benchmark across 14 domains (Biology, Business, Chemistry,
Computer Science, Economics, Engineering, Health, History, Law, Math,
Philosophy, Physics, Psychology, Other), each with up to 10 multiple-choice
options instead of MMLU's 4. `benchmark = "MMLU-Pro"` here is the overall
score across all 14 domains, one row per model.

## Why a separate column from "MMLU Pro Biology" / "MMLU Pro Chemistry"

RAND's two subject-split columns (`data/curated` via the pipeline's RAND feed)
are single-domain slices of the same question pool. This file is the
aggregate over all 14 domains, a materially different capability read: a
model can be strong on the Bio/Chem slice and mediocre overall, or vice versa.
Keeping `"MMLU-Pro"` as its own benchmark avoids conflating the two.

## Difference from MMLU

MMLU is saturated at the frontier and its 4-choice format has a 0.25 chance
floor. MMLU-Pro increases each question to up to 10 options (chance floor
0.10), removes trivial/ambiguous MMLU items, and adds harder items from
STEM-website, TheoremQA and SciBench sources, which pushes scores well below
ceiling even for 2025-2026 frontier models (best score in this file: 0.9116,
Gemini 3.1 Pro) and raises the reasoning load enough that chain-of-thought
(CoT) beats direct answering by up to ~20 points, the reverse of the original
MMLU (where CoT typically hurt, per the TIGER-Lab leaderboard's own README).

**Chance floor = 0.10** — add to `data/curated/benchmark_lower_bounds.csv`
when wiring the `--floors` flag.

## Prompting

CoT is the TIGER-Lab leaderboard's default and the setting used for every
score in this file. No direct-answer numbers were substituted.

## Fetch date

2026-08-05.

## Provenance

**Source — [`TIGER-Lab/mmlu_pro_leaderboard_submission`](https://huggingface.co/datasets/TIGER-Lab/mmlu_pro_leaderboard_submission/blob/main/results.csv)**,
the results file the HF Space [`TIGER-Lab/MMLU-Pro`](https://huggingface.co/spaces/TIGER-Lab/MMLU-Pro)
renders as its leaderboard table (the Space's `app.py`/`utils.py` are a
generic HF leaderboard template that reads this file via `SUBMISSION_URL`;
the GitHub README table (`raw.githubusercontent.com/TIGER-AI-Lab/MMLU-Pro/main/README.md`)
is a stale, much shorter snapshot of the same numbers and was not used once
the full submissions file was found).

**`Data Source` column, carried into this file's `source` column:**

- **`TIGER-Lab`** — run directly by the TIGER-Lab team on their own harness.
  Includes the 14-domain per-category breakdown in the source file (not
  carried into this file, which is overall-only).
- **`Self-Reported`** — submitted by the model vendor or a third party
  (vendor release blog, model card, or community submission), overall score
  only, no per-domain breakdown. This is the only way most 2025-2026 frontier
  checkpoints (GPT-5.x, Claude 4.x, Gemini 3.x, Grok 4.x, DeepSeek-V3.x, Qwen3.x,
  GLM-4.5+) enter the leaderboard, since TIGER-Lab does not re-run every new
  release on their own infrastructure.

Every row below traces to a specific line in that CSV; no score was computed,
interpolated, or copied from a third-party aggregator.

## Discrepancies

`Claude-3.5-Sonnet (2024-10-22)` appears twice in the source: TIGER-Lab-run
at 0.7764 and self-reported at 0.780. Kept the TIGER-Lab number
(`claude-3-5-sonnet-20241022`, 0.7764); the self-reported 0.780 is logged
here rather than silently dropped.

## Canonicalization

124 / 262 source rows matched an existing `model_version` in
`data/processed/benchmarks_merged.csv`: 76 by exact name (after
punctuation/case normalization), 31 by a hand-verified name override (mostly
effort/thinking-suffix conventions already used elsewhere in this repo, e.g.
generic "(Thinking)" → the `_unknown` effort bucket, `Phi3-medium-128k` →
`Phi-3-medium-128k-instruct`), and 17 via `canonical/model_aliases.csv`.

**One alias-table pattern was deliberately not used for this benchmark.**
`model_aliases.csv` maps bare names like `Llama 3 70b` / `Llama 3.1 70b` /
`Llama 3.1 8b` / `Llama 3.1 405b` straight to the `-Instruct` canonical ID,
annotated "QA-bench eval -> Instruct variant" — valid for RAND/QA-bench,
which only ever tested the Instruct checkpoint under that bare name. MMLU-Pro
tests base and Instruct as separate rows with different scores
(`Llama-3-70B` 0.5278 vs `Llama-3-70B-Instruct` 0.562, for example), so
applying that alias here would silently overwrite one checkpoint's score
with the other's identity. Those 4 alias rows were excluded for this import;
`Llama-3-70B`/`Llama-3-8B` (base) instead map to the pre-existing separate
base canonical IDs `Meta-Llama-3-70B` / `Meta-Llama-3-8B`. `Llama-3.1-70B`
and `Llama-3.1-8B` (base) have no separate base ID anywhere in the current
data (only `-Instruct` was ever tracked), so they are added as new rows with
no release date rather than borrowed from the Instruct ID (see Needs review).

54 rows have no existing `model_version` anywhere in the data. All 54 were
kept anyway under this rule: **include a new checkpoint only if its vendor
family already has at least one other canonical entry in
`benchmarks_merged.csv`** (OpenAI, Anthropic, Google/DeepMind, Meta, xAI,
DeepSeek, Alibaba/Qwen, Mistral AI, Zhipu/GLM, MiniMax, 01.AI/Yi,
Microsoft/Phi, NVIDIA/Nemotron, Moonshot/Kimi are all represented elsewhere
in this repo). These 54 get `release_date` empty (new to us) and no
`organization` (matching the rest of the file's convention).

**Excluded (83 rows).** Two categories:

1. **Community/derivative fine-tunes**, not the primary lab: Zephyr, WizardLM-2
   is the one exception (already tracked separately), MAmmoTH2 (TIGER-Lab's
   own research model), OpenChat, Neo-7B(-Instruct), Staring-7B, InternMath,
   Llama3-Smaug, Higgs-Llama, Reflection-Llama, Athene-V2-Chat (both rows),
   magnum, azerogpt, ECHO_Ego, RRD2.5, General-Reasoner, SkyThought-T1,
   NewenAI/Phi4-sft, Llemma-7B, Mimo-7B (base/RL), c4ai-command-r-v01.
2. **Vendor family not tracked anywhere else in the data**: AI21/Jamba,
   Cohere (command-r, Aya-Expanse, Aya-Vision), IBM/Granite (all 9 sizes),
   LG/EXAONE-3.5 (all 3 sizes), ByteDance/Seed and Doubao (all 9 rows:
   Seed-Thinking-v1.5, Seed1.6-\*, Seed2.0-\*, Seed-OSS-36B-\*, Doubao-1.5-Pro),
   Tencent/Hunyuan (all 4 rows), Baidu/ERNIE-4.5 (all 3 rows),
   Meituan/LongCat, Shanghai AI Lab/InternLM3 and Intern-S1, HuggingFace/SmolLM
   (both generations, all sizes — additionally near the 0.10 chance floor,
   zero capability signal).

Also excluded: `LLaDA` (duplicate identical row, and an academic diffusion-LM
release, not a frontier lab), `GPT-4-mini (high)` (not a real OpenAI model
ID — no "GPT-4-mini" was ever released; could be a mislabeled GPT-4.1-mini or
GPT-5-mini submission, excluded rather than guessed), and the smallest
size in an otherwise-included family purely for chance-floor-adjacent
uninformativeness: `Llama-3.2-1B` (0.1195), all 6 SmolLM/SmolLM2 sizes
(0.108-0.183), `Gemma-3-1B-it` (0.147), `Qwen2-{0.5B,1.5B}(-Instruct)` (4
rows, 0.150-0.226), `Qwen2.5-{0.5B,1.5B}` (0.149, 0.321), `Qwen3.5-0.8B`
(0.297).

## Needs review

Ambiguous mappings kept as best-guess new rows (no forced merge into an
existing ID) because a confident 1:1 match could not be established:

- **`Grok-2`, `Grok-2-mini`** — xAI shipped Grok 2 in Aug 2024 and refreshed
  it as `grok-2-1212` in Dec 2024 (the only Grok-2-era checkpoint currently
  in `benchmarks_merged.csv`). The leaderboard's undated "Grok-2" could be
  either checkpoint; not merged into `grok-2-1212` to avoid misattributing a
  date/checkpoint.
- **`Grok-3-mini`, `Grok3-mini-Beta`** — `benchmarks_merged.csv` carries
  `grok-3-mini-beta_{high,low,medium}` (2025-04-09) and
  `grok-3-mini_{high,low}` (2025-06-24) but no bare/`_unknown` variant for
  either generation, so an unqualified "Grok-3-mini" name cannot be assigned
  a specific effort suffix or date without guessing.
- **`Qwen3-Max-Thinking`** — data has `qwen3-max-2025-09-23` (no thinking
  variant tracked); not merged.
- **`Qwen2.5-Turbo`** — data has `qwen-turbo-2024-11-01` (no "2.5" in the
  name); possibly the same API model under Alibaba's later naming, possibly
  a distinct release. Not merged.
- **`Reka 3`** — data has `reka-flash-3` (2025-03-10); "Reka 3" may be an
  abbreviation of the same model or a different Reka release. Not merged.
- **`DeepSeek-V2-Chat`** — data has bare `DeepSeek-V2` (2024-05-07, no
  "-Chat" suffix); plausibly the same chat-tuned default, not merged since
  the naming isn't exact.
- **`DeepSeek-V3.2-Thinking`** — data already carries `DeepSeek-V3.2-Exp`,
  `DeepSeek-V3.2-Exp_thinking`, `DeepSeek-V3.2-Speciale`, and bare
  `deepseek-v3.2`; this leaderboard row doesn't specify which, so it's kept
  separate rather than folded into any of the four.
- **`Mistral-Small-base`, `Mistral-Small-instruct`** — self-reported, no
  date or version suffix, so the specific Mistral Small generation (3 vs
  3.1 vs 3.2) is unclear; not merged into any of the dated `mistral-small-*`
  IDs.
- **`Llama-3.1-70B`, `Llama-3.1-8B`** (base, non-Instruct) — only the
  Instruct checkpoints of Llama 3.1 were ever tracked in this data; these
  base rows are new with no release date (see Canonicalization above).
- **`Qwen3-30B-A3B-Thinking`** — mapped to the existing bare `Qwen3-30B-A3B`
  canonical ID, following the same collapse already made for this exact
  model in `canonical/model_aliases.csv` ("LiveBench thinking suffix; DB has
  only base Qwen3-30B-A3B"). `Qwen3-30B-A3B-Thinking-2507`, a later/separate
  checkpoint, was NOT folded into the same ID and is kept as its own new row.

None of the above affects a row already used elsewhere in the ECI fit; all
are either brand-new checkpoints or ones whose only existing use is this
file.
