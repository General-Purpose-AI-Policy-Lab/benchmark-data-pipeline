"""Invariants the pipeline is supposed to guarantee. Run after scripts/check.py.

check.py gates a single refresh; this asserts the properties that past bugs
broke silently. Stdlib only, reads the committed files, no network.
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "data/pipeline/canonical"
CURATED = ROOT / "data/curated"


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


merged = read(ROOT / "data/processed/benchmarks_merged.csv")

# One row per cell: the invariant the whole merge policy exists to produce.
dupes = [k for k, c in Counter((r["model_version"], r["benchmark"]) for r in merged).items() if c > 1]
assert not dupes, f"duplicate (model, benchmark) cells: {dupes[:3]}"

# Two config tokens stacked means one test-taker was split (glm-4.5_thinking_high).
STACKED = re.compile(r"_(?:thinking|promax|unknown|\d+K)_(?:minimal|low|medium|high|xhigh|max|none)$")
stacked = sorted({r["model_version"] for r in merged if STACKED.search(r["model_version"])})
assert not stacked, f"model_version carries two config suffixes: {stacked}"

# Category belongs to the benchmark; a row_adds file must not ship a second one.
cats = defaultdict(set)
for r in merged:
    cats[r["benchmark"]].add(r["category"])
split = {b: sorted(c) for b, c in cats.items() if len(c) > 1}
assert not split, f"benchmark with more than one category: {split}"

# `source` must not carry pure case variants of one string.
by_fold = defaultdict(set)
for r in merged:
    by_fold[r["source"].casefold()].add(r["source"])
variants = {k: sorted(v) for k, v in by_fold.items() if len(v) > 1}
assert not variants, f"source spelled more than one way: {variants}"

# The pipeline must never overwrite the hand-maintained baselines it reads.
source = CURATED / "human_baselines_source.csv"
assert source.is_file(), f"missing hand-maintained baselines: {source}"
assert len(read(source)) >= len(read(CURATED / "human_baselines.csv")), \
    "the derived baselines file has more rows than its source - the ratchet is back"

# Alias rows that cannot fire, and targets that do not exist.
aliases = read(CANON / "model_aliases.csv")
padded = [a["variant"] for a in aliases if a["variant"] != a["variant"].strip()]
padded += [a["canonical"] for a in aliases if (a["canonical"] or "") != (a["canonical"] or "").strip()]
assert not padded, f"alias rows with padding, which can never match: {padded}"
known = {r["model_version"] for r in merged}
ghosts = sorted({a["canonical"] for a in aliases if a["canonical"] and a["canonical"] not in known}
                - {a["variant"] for a in aliases})
assert not ghosts, f"alias targets absent from the data: {ghosts}"

# A duplicated benchmark row fans out every score row for that benchmark.
meta = read(CANON / "benchmark_metadata.csv")
mdupes = [k for k, c in Counter(m["benchmark"] for m in meta).items() if c > 1]
assert not mdupes, f"benchmark_metadata.csv has duplicate benchmarks: {mdupes}"

# Curated edits: no cell added twice, and nothing both dropped and added.
adds, drops = [], set()
for p in sorted(CURATED.glob("row_adds_*.csv")):
    adds += [(r["model_version"], r["benchmark"]) for r in read(p)]
for p in sorted(CURATED.glob("row_drops_*.csv")):
    drops |= {(r["model_version"], r["benchmark"]) for r in read(p)}
adupes = [k for k, c in Counter(adds).items() if c > 1]
assert not adupes, f"row_adds supplies the same cell twice: {adupes}"
resurrected = sorted(set(adds) & drops & {(r["model_version"], r["benchmark"]) for r in merged})
assert not resurrected, f"cells both dropped and added, yet shipped: {resurrected}"

print(f"OK: {len(merged)} rows — 9 invariants hold "
      f"({len(cats)} benchmarks, {len(known)} models, {len(aliases)} alias rows)")
