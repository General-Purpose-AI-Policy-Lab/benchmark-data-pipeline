"""METR Time Horizons: the human baseline of `human_baselines.csv`, recomputed from METR's runs.

Not a feed. This module yields no `Record` and is absent from `TRANSLATE`; it documents and
reproduces the one row of `0_input/metadata/human_baselines.csv` that no publication states:
`METR Time Horizons / Committee of Domain Experts = 0.8301`.

Input, not shipped (15 MB), the run table behind METR-Horizon-v1.1, the version Epoch ingests:

    curl -sLO https://raw.githubusercontent.com/METR/eval-analysis-public/main/\
reports/time-horizon-1-1/data/raw/runs.jsonl

One JSON object per run over the three suites of the benchmark (HCAST, SWAA, RE-Bench). Runs of the
human baseliners carry `alias == "human"`, the others are the agents Epoch charts.

Weighting. A run scores `score_binarized`; runs are averaged with `invsqrt_task_weight`, METR's
diversity weight (a family of n tasks counts 1/sqrt(n), split across the runs of each task, so a
task weighs the same whether it was run once or sixty-nine times). `check_weighting` verifies on
the agents that this reproduces the `average_score` column of `metr_time_horizons_external.csv`,
which is what the pipeline ingests: exact to four decimals (GPT-5.3-Codex 0.7454, Claude Opus 4.6
0.7886, Gemini 3 Pro 0.7098). The human figure therefore sits on the ingested metric.

Aggregation. `committee` counts a task solved when at least one baseliner succeeded. Attempts are
independent people: HCAST assigns one baseliner per task (screened by qualification tasks, degree
from a top-100 university or 3+ years of relevant experience), SWAA was baselined 3 to 4 times per
task by METR employees, RE-Bench reuses the RE-Bench expert pool. Attempts per task run from 1 to
69 and METR collected more of them where baselines failed, so the lift lands on the hard, densely
baselined tasks while sparsely baselined ones stay near their single-attempt value (user decision
of 2026-09-11; a fixed best-of-3 would give 0.80, best-of-2 0.77, best-of-5 0.83).

What is deliberately not published. `single` returns the mean of individual attempts, 0.6632, kept
out of `human_baselines.csv` as too biased (user, 2026-09-11): METR declines to use it because many
baseline failures come from reasons that do not apply to models (expertise mismatched with the
task, giving up, a speed bonus that rewards abandoning hard tasks), and the HCAST paper warns it
"is not directly comparable to the success rates of agents". It is the reference point of the
committee figure, not a baseline.

Scope and asymmetry. Humans cover 188 of the 228 tasks; the other 40 carry an estimated
`human_minutes` and no human run, and models score 3 to 4 points above their full-suite value on
that subset. `average_score` is also a mean over runs while the baseline is a best-of-N: under the
same rule the models rise too (Claude Opus 4.6 from 0.825 to 0.886 on these tasks), which is why
the row must never be read without its note.

See `docs/decisions.md`, 2026-09-11.
"""

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

RUNS_URL = ("https://raw.githubusercontent.com/METR/eval-analysis-public/main/"
            "reports/time-horizon-1-1/data/raw/runs.jsonl")
HUMAN_ALIAS = "human"
# Published in 0_input/metadata/human_baselines.csv, on METR-Horizon-v1.1.
PUBLISHED_COMMITTEE = 0.8301

# Task-level aggregations of the binarised scores of one task's attempts.
AGGREGATES: dict[str, Callable[[list[int]], float]] = {
    "committee": lambda scores: 1.0 if any(scores) else 0.0,
    "single": lambda scores: sum(scores) / len(scores),
}


def load_runs(path: Path) -> list[dict]:
    """Read the JSONL run table.

    Raises:
        FileNotFoundError: with the URL to fetch, since the file is not shipped.
    """
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; fetch it from {RUNS_URL}")
    return [json.loads(line) for line in path.open() if line.strip()]


def _by_task(runs: list[dict]) -> dict[str, tuple[float, list[int]]]:
    """Group runs by task: (total weight of the task, one binarised score per attempt)."""
    weight: dict[str, float] = defaultdict(float)
    scores: dict[str, list[int]] = defaultdict(list)
    for run in runs:
        weight[run["task_id"]] += run["invsqrt_task_weight"]
        scores[run["task_id"]].append(run["score_binarized"])
    return {task: (weight[task], scores[task]) for task in weight}


def weighted_score(runs: list[dict], aggregate: str = "committee") -> float:
    """Weighted mean over tasks of the aggregated attempts, METR's own weighting.

    Args:
        runs: runs of a single test-taker (one agent, or the human baseliners).
        aggregate: a key of `AGGREGATES`.

    Returns:
        The score in [0, 1].

    Raises:
        KeyError: unknown aggregate.
        ZeroDivisionError: no run.
    """
    fold = AGGREGATES[aggregate]
    per_task = _by_task(runs)
    total = sum(weight for weight, _ in per_task.values())
    return sum(weight * fold(scores) for weight, scores in per_task.values()) / total


def human_baseline(runs: list[dict], aggregate: str = "committee",
                   task_source: str = "") -> float:
    """The baseline itself: `weighted_score` restricted to the baseliners' runs.

    Args:
        runs: the whole run table.
        aggregate: a key of `AGGREGATES`.
        task_source: one suite (`HCAST`, `SWAA`, `RE-Bench`), or "" for the three together.
    """
    human = [run for run in runs if run["alias"] == HUMAN_ALIAS
             and (not task_source or run["task_source"] == task_source)]
    return weighted_score(human, aggregate)


def check_weighting(runs: list[dict]) -> dict[str, float]:
    """Recompute each agent's score; compare with Epoch's `average_score` to trust the weighting.

    Returns:
        alias -> mean over runs, the column `metr_time_horizons_external.csv` ingests.
    """
    agents: dict[str, list[dict]] = defaultdict(list)
    for run in runs:
        if run["alias"] != HUMAN_ALIAS:
            agents[run["alias"]].append(run)
    return {alias: weighted_score(rows, "single") for alias, rows in sorted(agents.items())}


def main() -> None:
    """Print the baseline, its breakdown, and the agent scores that validate the weighting."""
    parser = argparse.ArgumentParser(description=f"Recompute the METR human baseline. {RUNS_URL}")
    parser.add_argument("runs", type=Path, help="runs.jsonl of METR-Horizon-v1.1")
    runs = load_runs(parser.parse_args().runs)

    committee = human_baseline(runs, "committee")
    print(f"committee of domain experts : {committee:.4f}  (published {PUBLISHED_COMMITTEE})")
    print(f"single attempt, not published: {human_baseline(runs, 'single'):.4f}")
    for suite in ("HCAST", "SWAA", "RE-Bench"):
        single = human_baseline(runs, "single", suite)
        print(f"  {suite:9s} committee={human_baseline(runs, 'committee', suite):.4f} "
              f"single={single:.4f}")
    print("\nagents (compare with average_score of metr_time_horizons_external.csv):")
    for alias, score in check_weighting(runs).items():
        print(f"  {alias:34s} {score:.4f}")


if __name__ == "__main__":
    main()
