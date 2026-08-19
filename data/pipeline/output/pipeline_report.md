# Pipeline report — 2026-08-19 13:35:33 UTC

- **Snapshot:** `2026-08-19`
- **Epoch ZIP sha256:** `89a9c3d9962d11f17a4a35eaf5b89ff5e4dcdd63282e74363e82c671bc0f5c13`
- **Fetched at:** 2026-08-19T12:44:15.863662+00:00

## Row counts

- After load:           6,189
- After dedup:          5,249
- After metadata join:  5,249
- After optional filter:5,249
- Final:                5,247

## Distinct counts

- Benchmarks: 100
- Models:     860

## Coverage vs current `data/processed/benchmarks_merged.csv`

- Overlapping (model, benchmark) pairs: 5,247
- Current file pairs: 5,247
- New file pairs:     5,247
- Significant score deltas (|Δ|>0.01): 0

## Unrecognized live-feed tasks (3)

In `epoch.ai/data/benchmarks.csv` but in neither `LIVE_TASK_SPEC` nor `LIVE_TASK_SKIP` (section 03d). Map them or skip them with a reason:
- `MirrorCode`
- `OEIS Open`
- `OEIS Open Lite`

## Rows dropped for a blank `Model version` (417)

Valid scores with no versioned Epoch id, so no test-taker to key on. A mix of real base models missing from Epoch's registry, agent scaffolds, and task-specific fine-tunes. Recovering the first group needs a curated `Name -> model_version` map.

- `science_qa_external.csv` (ScienceQA): **78** — e.g. Mutimodal-T-SciQ_Large 🥇, MC-CoT_F-Large 🥈, Honeybee (Vicuna-13B) 🥉
- `bool_q_external.csv` (BoolQ): **70** — e.g. XVerse, Palmyra X (43B), Cohere Command beta (52.4B)
- `gsm8k_external.csv` (GSM8K): **65** — e.g. Palmyra X (43B), gpt-3.5-turbo-0301, Jurassic-2 Jumbo (178B)
- `os_world_external.csv` (OS World (Screenshot)): **37** — e.g. agi-0 (50 steps), DeepMiner-Mano-72B (100 steps), UI-TARS-2-2509 (100 steps)
- `mmlu_external.csv` (MMLU): **32** — e.g. AquilaChat2 34B, AquilaChat2 34B, Arctic Instruct
- `lambada_external.csv` (LAMBADA): **27** — e.g. XVerse, GLaM (MoE) 0.1B/64E, GLaM (MoE) 1.7B/64E
- `piqa_external.csv` (PIQA): **27** — e.g. GLaM (MoE) 0.1B/64E, GLaM (MoE) 1.7B/64E, GLaM (MoE) 8B/64E
- `hella_swag_external.csv` (HellaSwag): **22** — e.g. Anthropic-LM v4-s3 (52B), Cohere Command beta (6.1B), Cohere Command beta (52.4B)
- `live_bench_external.csv` (LiveBench): **10** — e.g. 
- `arc_ai2_external.csv` (ARC (AI2)): **8** — e.g. Falcon-rw-1.3B, GPT-Neo-2.7B, phi-1.5-web-only (1.3B)
- `wino_grande_external.csv` (WinoGrande): **8** — e.g. PaLM-cont 62B, Falcon-rw-1.3B, GPT-Neo-2.7B
- `aider_polyglot_external.csv` (Aider Polyglot): **5** — e.g. 
- `frontiercode_external.csv` (FrontierCode): **5** — e.g. SWE-1.7, Composer 2.5, Inkling
- `bbh_external.csv` (BIG-Bench Hard (BBH)): **4** — e.g. Chinese-Alpaca-Plus-13B, XVERSE-13B, AquilaChat2 34B
- `common_sense_qa_2_external.csv` (CSQA2): **4** — e.g. Unicorn-Large, Unicorn-11B, Unicorn 770M
- `arc_agi_external.csv` (ARC-AGI): **3** — e.g. Gemini 3 Deep Think (2/26), o3-preview (Low)*, GPT-5.1 (Low)
- `gdp_pdf_external.csv` (GDP.pdf): **3** — e.g. Mistral Large 3, Nova 2 (Pro), NVIDIA Nemotron 3 Nano Omni
- `simplebench_external.csv` (SimpleBench): **2** — e.g. 
- `terminalbench_external.csv` (TerminalBench): **2** — e.g. 
- `adversarial_nli_external.csv` (Adversarial NLI): **1** — e.g. UNICORN
- `deepresearchbench_external.csv` (DeepResearchBench): **1** — e.g. 
- `fictionlivebench_external.csv` (Fiction.LiveBench): **1** — e.g. 
- `open_book_qa_external.csv` (OpenBookQA): **1** — e.g. Falcon-rw-1.3B
- `weirdml_external.csv` (WeirdML): **1** — e.g. 

## Unrecognized upstream files (1)

In the feed but in neither `FILE_SPEC` nor `FILE_SKIP`. Map them or skip them with a reason:
- `mirrorcode.csv`

## New models since last canonicalization (29)

See `output/missing_models.csv`. Add canonical aliases in `canonical/model_aliases.csv` and re-run section 04.
