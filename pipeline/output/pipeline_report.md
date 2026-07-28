# Pipeline report — 2026-07-28 14:30:51 UTC

- **Snapshot:** `2026-07-28`
- **Epoch ZIP sha256:** `69f6fc403e056bc884b6ad865cd2a9c02fe15f7bb4b7e8b2f879682f0aab48ef`
- **Fetched at:** 2026-07-28T08:23:42.761958+00:00

## Row counts

- After load:           5,276
- After dedup:          4,394
- After metadata join:  4,394
- After optional filter:4,394
- Final:                4,390

## Distinct counts

- Benchmarks: 98
- Models:     756

## Coverage vs current `data/processed/benchmarks_merged.csv`

- Overlapping (model, benchmark) pairs: 4,390
- Current file pairs: 4,392
- New file pairs:     4,390
- Significant score deltas (|Δ|>0.01): 0

## Rows dropped for a blank `Model version` (416)

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
- `gdp_pdf_external.csv` (GDP.pdf): **3** — e.g. Mistral Large 3, Nova 2 (Pro), NVIDIA Nemotron 3 Nano Omni
- `arc_agi_external.csv` (ARC-AGI): **2** — e.g. o3-preview (Low)*, GPT-5.1 (Low)
- `simplebench_external.csv` (SimpleBench): **2** — e.g. 
- `terminalbench_external.csv` (TerminalBench): **2** — e.g. 
- `adversarial_nli_external.csv` (Adversarial NLI): **1** — e.g. UNICORN
- `deepresearchbench_external.csv` (DeepResearchBench): **1** — e.g. 
- `fictionlivebench_external.csv` (Fiction.LiveBench): **1** — e.g. 
- `open_book_qa_external.csv` (OpenBookQA): **1** — e.g. Falcon-rw-1.3B
- `weirdml_external.csv` (WeirdML): **1** — e.g. 

## New models since last canonicalization (87)

See `output/missing_models.csv`. Add canonical aliases in `canonical/model_aliases.csv` and re-run section 04.
