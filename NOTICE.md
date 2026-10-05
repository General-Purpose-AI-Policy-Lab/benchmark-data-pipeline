# NOTICE: third-party data

The `LICENSE` (CC-BY-4.0) covers what this project produces: the code, the curated dictionaries under `0_input/`, and the CSV tables in `2_database/` and `3_views/`.

It does **not** cover the upstream scores those files are derived from. Each feed carries its own terms, listed below. Anyone republishing `2_database/` or an analysis built on it must credit Epoch AI, Kaggle, the RAND report, Scale AI and the Cybench authors.

Per-artifact URL, fetch date, sha256 and byte size: `0_input/feed/provenance.json`.

## Feeds

| Feed | Source | Terms | Redistributed here? |
|---|---|---|---|
| `epoch` | [`epoch.ai/data/benchmark_data.zip`](https://epoch.ai/data/benchmark_data.zip) | **CC-BY 4.0** (Epoch AI), attribution required ([terms](https://epoch.ai/benchmarks/use-this-data)); results Epoch compiles from papers and leaderboards keep their original terms, with the source given per row | Yes, the CSV files of the ZIP under `0_input/feed/epoch/` |
| `epoch_live` | [`epoch.ai/data/benchmarks.csv`](https://epoch.ai/data/benchmarks.csv) | **CC-BY 4.0** (Epoch AI), attribution required | Yes, 1 CSV under `0_input/feed/epoch_live/` |
| `epoch_cyber` | [`epoch.ai/data/cyber/processed_data_for_eci.csv`](https://epoch.ai/data/cyber/processed_data_for_eci.csv) | **CC-BY 4.0** (Epoch AI), attribution required; described in Chauvin et al., ["Are Mythos' cyber capabilities overhyped?"](https://epoch.ai/gradient-updates/are-mythos-cyber-capabilities-overhyped) (Epoch AI, 2026); some values were read off plots published by the UK AI Security Institute and others | Yes, 1 CSV under `0_input/feed/epoch_cyber/` |
| `cybench_site` | [`cybench.github.io`](https://cybench.github.io) leaderboard, frozen snapshot | No license stated on the leaderboard; cite the Cybench paper (Zhang et al., ICLR 2025) | Yes, 1 CSV under `0_input/feed/cybench_site/` |
| `kaggle` | `kaggle.com/api/v1/benchmarks/<board>/leaderboard`, boards `open-benchmarks/mmlu`, `open-benchmarks/mmlu-pro`, `deepmind/simpleqa-verified` | Each board states "This benchmark has been released under the Apache 2.0 License"; cite the board and the benchmark paper. Kaggle's Terms of Service apply to the site | Yes, 3 JSON under `0_input/feed/kaggle/` |
| `rand` | Digitized from RAND **RR-A3797-1** (Dev et al. 2025, *Toward Comprehensive Benchmarking of the Biological Knowledge of Frontier LLMs*) | Copyright RAND Corporation: only the numeric scores are reproduced, for non-commercial research and with citation of [RR-A3797-1](https://www.rand.org/pubs/research_reports/RRA3797-1.html); neither the report nor its figures are redistributed, and commercial reuse of these rows requires RAND's permission. Frozen: never refreshed | Yes, 1 CSV under `0_input/feed/rand/` |
| `seal` | [`labs.scale.com/leaderboard/<slug>`](https://labs.scale.com/leaderboard), scores parsed from the page's Next.js payload | **No open license.** Scale AI Terms of Service apply | **No**, see below |

## Scale SEAL

Scale AI publishes the SEAL leaderboards without an open license, so the captured HTML pages are **not redistributed in this repository**. They are gitignored (`0_input/feed/seal/*.html`) and fetched on demand by `python -m benchmark_data refresh`, which is why a fresh clone must run `python -m benchmark_data refresh` before `build`.

What *is* tracked is our own work over those pages: the curated `0_input/feed/seal/aliases.csv`, the sha256 of each page in `provenance.json`, and the resulting numeric scores in `2_database/<run>/scores.csv` and the views (feed `seal`): one score per model and benchmark, factual results kept for non-commercial research with attribution to Scale AI. No page, layout or other content of the leaderboards is redistributed, in the current tree or in the history of this repository.

If you redistribute those scores, attribute Scale AI and confirm the current terms at <https://scale.com/legal/terms> before doing so.

## Attribution when citing

> Benchmark scores aggregated from Epoch AI (CC-BY 4.0), Kaggle Open Benchmarks (Apache 2.0),
> RAND RR-A3797-1 (Dev et al. 2025), Scale AI SEAL and the Cybench leaderboard, via the
> General-Purpose AI Policy Lab `benchmark-data-pipeline` (CC-BY-4.0).
