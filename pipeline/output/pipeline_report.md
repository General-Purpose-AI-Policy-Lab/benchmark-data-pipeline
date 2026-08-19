# Pipeline report — 2026-08-07 10:43:56 UTC

- **Snapshot:** `2026-08-07`
- **Epoch ZIP sha256:** `591b9f32b820c19e8e7684cb193a1b6efa05378dd09ad349e7c82f240bd5f07b`
- **Fetched at:** 2026-08-07T10:43:50.508600+00:00

## Row counts

- After load:           5,968
- After dedup:          5,052
- After metadata join:  5,052
- After optional filter:5,052
- Final:                5,064

## Distinct counts

- Benchmarks: 100
- Models:     835

## Coverage vs current `data/processed/benchmarks_merged.csv`

- Overlapping (model, benchmark) pairs: 4,894
- Current file pairs: 4,954
- New file pairs:     5,064
- Significant score deltas (|Δ|>0.01): 13

### Top 10 score changes

- `qwen3.5-plus` on `Chess Puzzles`: 0.170 → 0.220 (Δ=+0.050)
- `qwen3.7-max` on `Chess Puzzles`: 0.220 → 0.190 (Δ=-0.030)
- `qwen3.6-max-preview` on `Chess Puzzles`: 0.170 → 0.200 (Δ=+0.030)
- `qwen3.6-flash` on `Chess Puzzles`: 0.172 → 0.200 (Δ=+0.028)
- `qwen3.6-plus` on `OTIS Mock AIME 2024-2025`: 0.906 → 0.933 (Δ=+0.028)
- `qwen3.6-max-preview` on `GPQA Diamond`: 0.891 → 0.874 (Δ=-0.017)
- `qwen3.6-flash` on `OTIS Mock AIME 2024-2025`: 0.861 → 0.844 (Δ=-0.017)
- `qwen3.5-plus` on `OTIS Mock AIME 2024-2025`: 0.850 → 0.867 (Δ=+0.017)
- `kimi-k2.7-code` on `GPQA Diamond`: 0.895 → 0.879 (Δ=-0.016)
- `qwen3.5-flash` on `GPQA Diamond`: 0.838 → 0.823 (Δ=-0.015)

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

## New models since last canonicalization (22)

See `output/missing_models.csv`. Add canonical aliases in `canonical/model_aliases.csv` and re-run section 04.
