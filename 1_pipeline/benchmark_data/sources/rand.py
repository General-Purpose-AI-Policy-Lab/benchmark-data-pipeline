"""Feed `rand`: RAND RR-A3797-1 (Dev et al. 2025), biology / chemistry, wide format, frozen."""

from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.sources.record import Record

# The first two rows of the CSV are the human baseline (score, description): set aside.
_HUMAN_ROWS = 2
SOURCE_LABEL = "RAND RR-A3797-1 (Dev et al. 2025)"
SOURCE_URL = "https://www.rand.org/pubs/research_reports/RRA3797-1.html"


def translate(feed_dir: Path) -> Iterator[Record]:
    """One "Bio: X" / "Chem: Y" column = one benchmark X / Y; every cell is a score."""
    rand = pandas.read_csv(feed_dir / "rand/rand_benchmark_scores.csv")
    long = rand.iloc[_HUMAN_ROWS:].melt(id_vars=["Model"], var_name="col", value_name="raw")
    for row in long.itertuples():
        score = pandas.to_numeric(row.raw, errors="coerce")  # 'N/A' -> set aside
        if pandas.isna(score):
            continue
        yield Record(row.Model, row.col.split(": ", 1)[-1], score / 100, "", "", "", {},
                     SOURCE_LABEL, SOURCE_URL)
