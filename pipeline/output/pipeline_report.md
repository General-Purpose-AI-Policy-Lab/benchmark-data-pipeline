# Pipeline report — 2026-06-19 14:54:16 UTC

- **Snapshot:** `2026-06-19`
- **Epoch ZIP sha256:** `9f9526cd33e6fe7a52a823095e6a0deb3745d9809f3cc367fd0070322a78a7d9`
- **Fetched at:** 2026-06-19T14:10:16.890743+00:00

## Row counts

- After load:           4,054
- After dedup:          3,213
- After metadata join:  3,213
- After optional filter:2,560
- Final:                2,560

## Distinct counts

- Benchmarks: 52
- Models:     583

## Coverage vs current `data/processed/benchmarks_merged.csv`

- Overlapping (model, benchmark) pairs: 1,502
- Current file pairs: 2,537
- New file pairs:     2,560
- Significant score deltas (|Δ|>0.01): 156

### Top 10 score changes

- `DeepSeek-R1` on `Fiction.LiveBench`: 0.694 → 0.333 (Δ=-0.361)
- `o1-2024-12-17_medium` on `Fiction.LiveBench`: 0.833 → 0.531 (Δ=-0.302)
- `claude-3-7-sonnet-20250219_8K` on `Fiction.LiveBench`: 0.833 → 0.531 (Δ=-0.302)
- `text-davinci-003` on `GSM8K`: 0.506 → 0.782 (Δ=+0.276)
- `Mixtral-8x7B-v0.1` on `ARC (AI2)`: 0.597 → 0.873 (Δ=+0.276)
- `fireworks/Kimi-K2-Instruct-0905` on `Fiction.LiveBench`: 0.667 → 0.406 (Δ=-0.261)
- `gemini-2.5-flash-lite-preview-06-17-thinking` on `Fiction.LiveBench`: 0.472 → 0.219 (Δ=-0.253)
- `gemma-7b` on `ARC (AI2)`: 0.532 → 0.783 (Δ=+0.251)
- `PaLM 540B` on `ARC (AI2)`: 0.601 → 0.852 (Δ=+0.251)
- `Cerebras-GPT-13B` on `MMLU`: 0.016 → 0.262 (Δ=+0.246)
