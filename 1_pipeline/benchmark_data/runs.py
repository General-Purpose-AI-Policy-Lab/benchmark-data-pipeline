"""Dated build folders: `2_database/<YYYYMMDD>/` and `3_views/<YYYYMMDD>/`.

Every build writes its tables and views under the date it ran (local time); a second build the
same day replaces that day's folders. `check`, `parity` and the consumers' `sync` read the most
recent date, and the consumers name their outputs after it: the date that dates the data is the
day the pipeline ran, never the day an analysis read it.
"""

import datetime
import re
from pathlib import Path

DATE_FORMAT = "%Y%m%d"
_DATE_DIR = re.compile(r"\d{8}")


def today() -> str:
    """The local date as YYYYMMDD: the folder name of a build run now."""
    return datetime.datetime.now().astimezone().strftime(DATE_FORMAT)


def dates(root: Path) -> list[str]:
    """The run dates found under `root` (2_database/ or 3_views/), oldest first."""
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and _DATE_DIR.fullmatch(p.name))


def latest(root: Path) -> Path:
    """`root/<most recent date>`; FileNotFoundError when no build has run."""
    found = dates(root)
    if not found:
        raise FileNotFoundError(f"{root}: no dated build folder, "
                                "run `python -m benchmark_data build`")
    return root / found[-1]
