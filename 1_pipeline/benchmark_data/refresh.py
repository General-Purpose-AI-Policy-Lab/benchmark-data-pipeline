"""Refresh `0_input/feed/` from the network. The build itself stays offline.

RAND is not refreshed: frozen report (Dev et al. 2025). The board lists (Kaggle, SEAL) are
those of the source modules: one source of truth.
"""

import hashlib
import io
import json
import logging
import socket
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from benchmark_data import config
from benchmark_data.sources.kaggle import KAGGLE_SPEC, board_filename
from benchmark_data.sources.seal import SEAL_SPEC

log = logging.getLogger(__name__)

EPOCH_ZIP_URL = "https://epoch.ai/data/benchmark_data.zip"
EPOCH_LIVE_URL = "https://epoch.ai/data/benchmarks.csv"
EPOCH_CYBER_URL = "https://epoch.ai/data/cyber/processed_data_for_eci.csv"
KAGGLE_URL = "https://www.kaggle.com/api/v1/benchmarks/{}/leaderboard"
SEAL_URL = "https://labs.scale.com/leaderboard/{}"
SEAL_HEADERS = {"User-Agent": "Mozilla/5.0"}  # without a browser header the page does not render
RAND_URL = "https://www.rand.org/pubs/research_reports/RRA3797-1.html"
TIMEOUT_S = 60  # a stalled connection fails instead of hanging


class Refresher:
    """Downloads the artifacts and keeps `provenance.json` up to date."""

    def __init__(self, feed_dir: Path = config.FEED_DIR):
        self.feed_dir = feed_dir
        self.fetched_at = datetime.now(UTC).isoformat()
        self.prov_path = feed_dir / "provenance.json"
        # Start from the existing provenance: a page kept because its source stopped answering
        # keeps its entry instead of vanishing from the rewritten file.
        self.provenance = json.loads(self.prov_path.read_text()) if self.prov_path.exists() else {}

    def fetch(self, key: str, url: str, headers=None) -> bytes:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {})) as r:
            data = r.read()
        self.provenance[key] = {"url": url, "fetched_at": self.fetched_at,
                                "sha256": hashlib.sha256(data).hexdigest(), "byte_size": len(data)}
        log.info("%s: %s bytes", key, f"{len(data):,}")
        return data

    def epoch_zip(self) -> None:
        """Replace every CSV of the epoch directory, except aliases.csv."""
        data = self.fetch("0_input/feed/epoch (benchmark_data.zip)", EPOCH_ZIP_URL)
        # The ZIP is opened BEFORE anything is deleted: a corrupt archive must fail without
        # having destroyed the feed in place.
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            fresh = {Path(n).name: z.read(n) for n in z.namelist()
                     if n.endswith(".csv") and Path(n).name != "aliases.csv"}
        if not fresh:
            raise RuntimeError("the Epoch ZIP holds no CSV: feed left untouched")
        for p in (self.feed_dir / "epoch").glob("*.csv"):
            if p.name != "aliases.csv":
                p.unlink()
        for name, blob in fresh.items():
            (self.feed_dir / "epoch" / name).write_bytes(blob)

    def epoch_live(self) -> None:
        (self.feed_dir / "epoch_live/epoch_live_benchmarks.csv").write_bytes(
            self.fetch("0_input/feed/epoch_live/epoch_live_benchmarks.csv", EPOCH_LIVE_URL))

    def epoch_cyber(self) -> None:
        (self.feed_dir / "epoch_cyber/cyber_benchmarks.csv").write_bytes(
            self.fetch("0_input/feed/epoch_cyber/cyber_benchmarks.csv", EPOCH_CYBER_URL))

    def kaggle(self) -> None:
        for board in KAGGLE_SPEC:
            name = board_filename(board)
            (self.feed_dir / "kaggle" / name).write_bytes(
                self.fetch(f"0_input/feed/kaggle/{name}", KAGGLE_URL.format(board)))

    def seal(self) -> None:
        """One HTML page per board; a board that stops answering keeps its page (stale > empty)."""
        for slug in SEAL_SPEC:
            try:
                data = self.fetch(f"0_input/feed/seal/{slug}.html", SEAL_URL.format(slug),
                                  SEAL_HEADERS)
            except urllib.error.HTTPError as e:
                log.warning("seal/%s: HTTP %s, existing page kept", slug, e.code)
                continue
            (self.feed_dir / "seal" / f"{slug}.html").write_bytes(data)

    def cybench_site(self) -> None:
        path = self.feed_dir / "cybench_site/cybench_leaderboard.csv"
        self.provenance["0_input/feed/cybench_site/cybench_leaderboard.csv"] = {
            "url": "https://cybench.github.io/data/leaderboard.csv", "fetched_at": "2026-09-07",
            "note": "frozen snapshot: the benchmark is saturated, no further rows expected",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "byte_size": path.stat().st_size}
        log.info("cybench_site: not refreshed (frozen snapshot of 2026-09-07)")

    def rand(self) -> None:
        path = self.feed_dir / "rand/rand_benchmark_scores.csv"
        self.provenance["0_input/feed/rand/rand_benchmark_scores.csv"] = {
            "url": RAND_URL, "fetched_at": "frozen",
            "note": "RAND RR-A3797-1 (Dev et al. 2025), never refreshed",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "byte_size": path.stat().st_size}
        log.info("rand: not refreshed (frozen report, Dev et al. 2025)")

    def write_provenance(self) -> None:
        self.prov_path.write_text(json.dumps(self.provenance, indent=2, sort_keys=True) + "\n")
        log.info("provenance.json: %d artifact(s). Data diff: git diff --stat 0_input/feed/",
                 len(self.provenance))


def refresh(feed_dir: Path = config.FEED_DIR) -> None:
    socket.setdefaulttimeout(TIMEOUT_S)
    r = Refresher(feed_dir)
    log.info("%d Kaggle board(s), %d SEAL board(s)", len(KAGGLE_SPEC), len(SEAL_SPEC))
    r.epoch_zip()
    r.epoch_live()
    r.epoch_cyber()
    r.cybench_site()
    r.kaggle()
    r.seal()
    r.rand()
    r.write_provenance()
