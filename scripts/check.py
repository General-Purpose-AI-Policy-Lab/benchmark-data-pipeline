"""Post-refresh gate: run after the pipeline notebook, before committing."""
import csv
import filecmp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MERGED = ROOT / "data/processed/benchmarks_merged.csv"
COLUMNS = ["model_version", "score", "release_date", "organization",
           "benchmark", "stderr", "source", "category"]

# Every file index.html fetches, plus the notebook itself.
for p in [MERGED,
          ROOT / "data/pipeline/canonical/benchmark_metadata.csv",
          ROOT / "data/curated/benchmark_lower_bounds.csv",
          ROOT / "data/pipeline/output/pipeline_report.md",
          ROOT / "data/pipeline/pipeline.ipynb"]:
    assert p.is_file(), f"missing: {p}"

with open(MERGED, newline="") as f:
    rows = list(csv.reader(f))
assert rows[0] == COLUMNS, f"header changed: {rows[0]}"
bad = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(COLUMNS)]
assert not bad, f"rows with wrong field count at lines {bad[:5]}"
assert len(rows) > 4000, f"only {len(rows) - 1} rows"

# The section-10 swap copies output/ -> processed/; identical files prove it ran.
assert filecmp.cmp(MERGED, ROOT / "data/pipeline/output/benchmarks_merged.csv",
                   shallow=False), "processed CSV differs from pipeline output — swap did not run"

report = (ROOT / "data/pipeline/output/pipeline_report.md").read_text()
assert report.strip(), "pipeline report is empty"

print(f"OK: {len(rows) - 1} rows, header and swap verified")
