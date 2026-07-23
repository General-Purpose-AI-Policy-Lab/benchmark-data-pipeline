# Pipeline report — 2026-07-21 12:38:25 UTC

- **Snapshot:** `2026-07-21`
- **Epoch ZIP sha256:** `15e499c84282c62d2398701f5d6db4afea1e74a7a2063b7a8debe2233919feeb`
- **Fetched at:** 2026-07-21T12:38:20.335233+00:00

## Row counts

- After load:           4,983
- After dedup:          4,107
- After metadata join:  4,107
- After optional filter:4,107
- Final:                4,105

## Distinct counts

- Benchmarks: 85
- Models:     736

## Coverage vs current `data/processed/benchmarks_merged.csv`

- Overlapping (model, benchmark) pairs: 3,917
- Current file pairs: 3,998
- New file pairs:     4,105
- Significant score deltas (|Δ|>0.01): 12

### Top 10 score changes

- `gemini-2.5-flash` on `AudioMultiChallenge`: 0.261 → 0.400 (Δ=+0.139)
- `gemini-3.1-flash-live-preview` on `AudioMultiChallenge`: 0.268 → 0.361 (Δ=+0.093)
- `glm-4.5` on `Lech Mazur Writing`: 0.780 → 0.734 (Δ=-0.046)
- `grok-4-0709` on `Lech Mazur Writing`: 0.807 → 0.769 (Δ=-0.038)
- `glm-5.1` on `SimpleBench`: 0.587 → 0.551 (Δ=-0.036)
- `Qwen3-235B-A22B-Thinking-2507` on `Lech Mazur Writing`: 0.849 → 0.824 (Δ=-0.025)
- `gemini-2.5-pro` on `Lech Mazur Writing`: 0.860 → 0.838 (Δ=-0.022)
- `o3-pro-2025-06-10_medium` on `Lech Mazur Writing`: 0.863 → 0.844 (Δ=-0.019)
- `gpt-5-2025-08-07_unknown` on `VisualToolBench`: 0.170 → 0.187 (Δ=+0.017)
- `Llama-4-Maverick-17B-128E-Instruct` on `Lech Mazur Writing`: 0.637 → 0.620 (Δ=-0.017)

## New models since last canonicalization (67)

See `output/missing_models.csv`. Add canonical aliases in `canonical/model_aliases.csv` and re-run section 04.
