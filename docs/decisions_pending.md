# Open decisions

Each point below is a place where two of the three repositories (Multiaxis_ECI = **MX**, benchmark-forecasting = **MBF**, this one = **BDP**) made a different choice, or where the right value is in doubt. No point is open today: every section below was settled, and its decision is in `decisions.md`.

Figures computed on 2026-09-04 against MX `55687ce`, MBF `2ed2c34`, BDP `9326f84` (feeds of 2026-08-28), then refreshed feeds of 2026-09-04. Settled items of the two 2026-09-04 batches (A1-A5, B2, B3, B6, most of B1) have been removed; see `decisions.md`.

## B. Benchmark vocabulary

### B1. Names — settled 2026-09-04

See `decisions.md` (fourth batch).

### B4. Score columns — settled 2026-09-04

See `decisions.md`. Only Fiction.LiveBench and The Agent Company differ from Epoch's own `score_column`; the choice is recorded there.

### B5. Scope — closed

OEIS Open Lite included, OEIS Open excluded (2026-09-07, tenth batch).

### B7. Access classes — closed

Settled on 2026-09-07 (eleventh batch): DTBench and LMCA `private`, FrontierSWE v2 `public`, FrontierMath Erdos and OEIS Open Lite in the new `open_problems` class.

## C. Models

C1, C2 and C3 settled on 2026-09-04 (see `decisions.md`, fifth batch).

C4 settled on 2026-09-04 (sixth batch).

## D. Release dates

Settled on 2026-09-07 (`decisions.md`, seventh and eighth batches): convention (public availability), the 34 disagreements under one month, the 12 of one month or more, the alias merges, and the four date tiers of the build. What follows is what remains.

### D4. Undated models — closed

Settled on 2026-09-07 (ninth batch). Only `ml-elephant` and `tml-interaction-small` stay undated, by decision.

## E. Human baselines

All settled on 2026-09-07 (ninth batch, `decisions.md`).

## F. Epoch cyber ECI benchmarks — closed

Settled on 2026-09-07 (`decisions.md`, cyber batch): 11 included, 7 excluded, BBH and BoolQ excluded as well. The frontier list built for the analysis is kept in `docs/frontier_models.csv`.
