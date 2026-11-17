"""Rows of public boards, or of a paper's table, that no other feed carries, transcribed by hand.

Epoch relays most boards with a delay and stops following some, and its files leave a few rows of
papers without a model: a row a source shows and no feed carries is written in `board_rows.csv`,
with the day the source was read. `model` is a machine
name (the grammar of `identity.split_name`) carrying only the settings the board states, a bare
name when it states none; `board_name` keeps the board's own spelling. The benchmark, the metric
and the run settings must be the ones of the rows the other feeds already carry for that
benchmark (same board, same column, same step budget).

The file is not refreshed: `refresh` records its hash. When another feed starts carrying a score
of the same release on the same benchmark, the build says so (`build._log_superseded_board_rows`)
and the row is retired from the file, so that one run is not counted under two labels.
"""

from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.sources.record import Record

FILE = "board_rows.csv"
COLUMNS = ["benchmark", "model", "score", "board_name", "source_label", "source_url", "read_on",
           "note"]


def translate(feed_dir: Path) -> Iterator[Record]:
    """One record per row.

    Raises:
        ValueError: unexpected header, or a row without benchmark, model, score, label or date.
    """
    table = pandas.read_csv(feed_dir / "board_rows" / FILE, dtype=str).fillna("")
    if list(table.columns) != COLUMNS:
        raise ValueError(f"board_rows/{FILE}: expected columns {COLUMNS}, got {list(table.columns)}")
    required = ["benchmark", "model", "score", "source_label", "read_on"]
    empty = table[(table[required] == "").any(axis=1)]
    if len(empty):
        raise ValueError(f"board_rows/{FILE}: row(s) {empty.index.tolist()} lack one of {required}")
    for row in table.itertuples():
        yield Record(row.model, row.benchmark, float(row.score), "", "", "", {},
                     row.source_label, row.source_url)
