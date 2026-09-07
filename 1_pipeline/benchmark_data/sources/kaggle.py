"""Feed `kaggle`: Kaggle Open Benchmarks boards, one leaderboard JSON per board."""

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

# Dictionary: board -> benchmark.
KAGGLE_SPEC = {
    'deepmind/simpleqa-verified': 'SimpleQA Verified',
    'open-benchmarks/mmlu':       'MMLU',
    'open-benchmarks/mmlu-pro':   'MMLU-Pro',
}

# Kaggle re-runs every model itself, in its own standardized setup: that setup is recorded as the
# harness, so a Kaggle score and an Epoch score of the same model are two harness runs and the
# deduplication keeps the best one (decision of 2026-09-04).
HARNESS = "Kaggle Open Benchmarks"
BOARD_URL = "https://www.kaggle.com/benchmarks/{}"

# 95% confidence-interval half-width -> standard deviation.
_CI_TO_SD = 1.96


def board_filename(board: str) -> str:
    return board.replace("/", "_") + ".json"


def translate(feed_dir: Path) -> Iterator[Record]:
    """One board = one benchmark; the only name cleanup is the "-default" harness tag."""
    for path in sorted((feed_dir / "kaggle").glob("*.json")):
        if path.stem.replace("_", "/", 1) not in KAGGLE_SPEC:
            log.warning("kaggle: ? %s: not in KAGGLE_SPEC", path.name)
    for board, bench in KAGGLE_SPEC.items():
        payload = json.loads((feed_dir / "kaggle" / board_filename(board)).read_text())
        for row in payload.get("rows", []):
            raw = re.sub(r"-default$", "", row.get("modelVersionSlug", ""))
            for tr in row.get("taskResults", []):
                num = (tr.get("result") or {}).get("numericResult") or {}
                if "value" not in num:
                    continue
                ci = num["confidenceInterval"] if num.get("hasConfidenceInterval") else ""
                yield Record(raw, bench, num["value"], ci / _CI_TO_SD if ci != "" else "", "", HARNESS,
                             {}, f"Kaggle Open Benchmarks ({board})", BOARD_URL.format(board))
