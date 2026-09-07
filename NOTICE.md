# NOTICE: third-party data

The `LICENSE` (CC-BY-4.0) covers what this project produces: the code, the curated dictionaries under `0_input/`, and the three CSV in `2_database/`.

It does **not** cover the upstream scores those files are derived from. Each feed carries its own terms, listed below. Anyone republishing `2_database/` or an analysis built on it must credit Epoch AI, Kaggle, the RAND report and Scale AI.

Per-artifact URL, fetch date, sha256 and byte size: `0_input/feed/provenance.json`.

## Feeds

| Feed | Source | Terms | Redistributed here? |
|---|---|---|---|
| `epoch` | [`epoch.ai/data/benchmark_data.zip`](https://epoch.ai/data/benchmark_data.zip) | **CC-BY** (Epoch AI), attribution required | Yes, 76 CSV under `0_input/feed/epoch/` |
| `epoch_live` | [`epoch.ai/data/benchmarks.csv`](https://epoch.ai/data/benchmarks.csv) | **CC-BY** (Epoch AI), attribution required | Yes, 1 CSV under `0_input/feed/epoch_live/` |
| `kaggle` | `kaggle.com/api/v1/benchmarks/<board>/leaderboard`, boards `open-benchmarks/mmlu`, `open-benchmarks/mmlu-pro`, `deepmind/simpleqa-verified` | Kaggle Terms of Service; per-board dataset licenses | Yes, 3 JSON under `0_input/feed/kaggle/` |
| `rand` | Digitized from RAND **RR-A3797-1** (Dev et al. 2025, *Toward Comprehensive Benchmarking of the Biological Knowledge of Frontier LLMs*) | Cite [RR-A3797-1](https://www.rand.org/pubs/research_reports/RRA3797-1.html). Frozen: never refreshed | Yes, 1 CSV under `0_input/feed/rand/` |
| `seal` | [`labs.scale.com/leaderboard/<slug>`](https://labs.scale.com/leaderboard), scores parsed from the page's Next.js payload | **No open license.** Scale AI Terms of Service apply | **No**, see below |

## Scale SEAL

Scale AI publishes the SEAL leaderboards without an open license, so the captured HTML pages are **not redistributed in this repository**. They are gitignored (`0_input/feed/seal/*.html`) and fetched on demand by `python -m benchmark_data refresh`, which is why a fresh clone must run `python3 refresh.py` before the notebook.

What *is* tracked is our own work over those pages: the curated `0_input/feed/seal/aliases.csv`, the sha256 of each page in `provenance.json`, and the resulting numeric scores in `2_database/scores.csv` (feed `seal`), aggregated as research with attribution to Scale AI.

If you redistribute those scores, attribute Scale AI and confirm the current terms at <https://scale.com/legal/terms> before doing so.

## Attribution when citing

> Benchmark scores aggregated from Epoch AI (CC-BY), Kaggle Open Benchmarks,
> RAND RR-A3797-1 (Dev et al. 2025) and Scale AI SEAL, via the
> General-Purpose AI Policy Lab `benchmark-data-pipeline` (CC-BY-4.0).
