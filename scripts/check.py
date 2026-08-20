"""Post-refresh gate: validates data/pipeline/output/ and swaps it into the tree.

Run after the pipeline notebook. Nothing reaches data/processed/ or
data/curated/ until every assertion below passes, so a bad run leaves the
previous data in place. This script owns the swap; the notebook no longer
copies anything (that ordering meant a failing check reported on files it
had already overwritten).
"""
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/pipeline/output"
CURRENT = ROOT / "data/processed/benchmarks_merged.csv"
COLUMNS = ["model_version", "score", "release_date", "organization",
           "benchmark", "stderr", "source", "category"]
HUMAN_COLUMNS = ["benchmark", "group", "score", "note", "source"]

# Validated candidate -> the runtime path it replaces.
SWAP = [(OUT / "benchmarks_merged.csv", CURRENT),
        (OUT / "human_baselines.csv", ROOT / "data/curated/human_baselines.csv")]


def rows_of(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


# Every file index.html fetches, plus the notebook and the two swap candidates.
for p in [OUT / "benchmarks_merged.csv", OUT / "human_baselines.csv",
          OUT / "pipeline_report.md",
          ROOT / "data/pipeline/canonical/benchmark_metadata.csv",
          ROOT / "data/curated/benchmark_lower_bounds.csv",
          ROOT / "data/pipeline/pipeline.ipynb"]:
    assert p.is_file(), f"missing: {p}"

rows = rows_of(OUT / "benchmarks_merged.csv")
assert rows[0] == COLUMNS, f"header changed: {rows[0]}"
bad = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(COLUMNS)]
assert not bad, f"rows with wrong field count at lines {bad[:5]}"

# One row per (model, benchmark) is the invariant the whole merge policy exists
# to produce; nothing downstream resolves a cell that ships twice.
i_model, i_bench = COLUMNS.index("model_version"), COLUMNS.index("benchmark")
seen, dupes = set(), []
for r in rows[1:]:
    key = (r[i_model], r[i_bench])
    if key in seen:
        dupes.append(key)
    seen.add(key)
assert not dupes, f"{len(dupes)} duplicate (model, benchmark) cell(s), e.g. {dupes[:3]}"

# Floor derived from the file being replaced, so it tracks the dataset instead
# of a constant that silently tolerates a 24% loss.
n_new = len(rows) - 1
assert n_new > 0, "no data rows"
if CURRENT.is_file():
    n_old = len(rows_of(CURRENT)) - 1
    assert n_new >= 0.95 * n_old, (
        f"row count fell {n_old} -> {n_new} (>5%). Inspect output/pipeline_report.md; "
        f"re-run this script once the drop is understood to accept it.")

humans = rows_of(OUT / "human_baselines.csv")
assert humans[0] == HUMAN_COLUMNS, f"human_baselines header changed: {humans[0]}"
assert len(humans) > 1, "human_baselines.csv has no rows"

assert (OUT / "pipeline_report.md").read_text().strip(), "pipeline report is empty"

for src, dst in SWAP:
    shutil.copy(src, dst)

print(f"OK: {n_new} rows, {len(humans) - 1} human baselines — validated, swapped into the tree")
