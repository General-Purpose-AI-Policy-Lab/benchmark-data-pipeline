"""Feed registry. A source is a module exposing `translate(feed_dir) -> Iterator[Record]`.

Adding a source: a module here, an entry in TRANSLATE, an `0_input/feed/<name>/aliases.csv` (even
empty, with the header), and entries in `config.SOURCE_ORDER` / `config.SPLITTABLE`.
"""

from benchmark_data.sources import (
    cybench_site,
    epoch_cyber,
    epoch_live,
    epoch_zip,
    kaggle,
    rand,
    seal,
)
from benchmark_data.sources.record import Record

TRANSLATE = {
    "epoch": epoch_zip.translate,
    "epoch_live": epoch_live.translate,
    "epoch_cyber": epoch_cyber.translate,
    "cybench_site": cybench_site.translate,
    "kaggle": kaggle.translate,
    "rand": rand.translate,
    "seal": seal.translate,
}

__all__ = ["Record", "TRANSLATE"]
