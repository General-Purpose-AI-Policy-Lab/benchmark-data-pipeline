"""Parity of the consumer views against the outputs the two repositories produced on their own.

The goldens (`tests/parity/golden/`) are the last files Multiaxis_ECI (commit 55687ce) and
benchmark-forecasting (commit 2ed2c34) built before the merge. Their benchmark names are mapped to
the current names through `previous_names`; the join key is (model_version, benchmark). The
differences are listed by cause, never hidden; `reports/parity_<consumer>.md` is written for review.
"""

import logging
from pathlib import Path

import pandas

from benchmark_data import config

log = logging.getLogger(__name__)

GOLDENS = {
    "multiaxis": ("multiaxis_benchmarks_merged_55687ce.csv", "all_scores_flat.csv"),
    "forecasting": ("mbf_all_normalized_updated_benchmarks_2ed2c34.csv", "dated_scores_flat.csv"),
}
KEY = ["model_version", "benchmark"]


def name_map(metadata_dir: Path = config.METADATA_DIR) -> dict[str, str]:
    """previous name -> current name, from benchmarks.csv."""
    table = pandas.read_csv(metadata_dir / config.BENCHMARKS_FILE, dtype=str).fillna("")
    out = {}
    for name, previous in zip(table["name"], table["previous_names"], strict=True):
        for p in previous.split(","):
            if p.strip():
                out[p.strip()] = name
    return out


def compare(golden: pandas.DataFrame, candidate: pandas.DataFrame, status: dict[str, str],
            merged_parts: set[str] = frozenset(), tol: float = 1e-3) -> dict[str, pandas.DataFrame]:
    """Golden pairs the view lacks, split by cause, and the shared pairs that moved.

    Buckets: `lost_excluded` (benchmark excluded since), `lost_merged_part` (board averaged into a
    merged series, e.g. PRBench Finance), `lost_renamed_model` (the golden's model_version does not
    exist in the view: alias or spelling changed, or the effort was completed), `lost_other`
    (model and benchmark both known, the pair is gone: upstream feed change, or a score column
    decision), `lost_unknown_benchmark` (a golden name no `previous_names` entry maps: to fix),
    `new`, `score_changed` (> tol), `date_changed`.
    """
    g = golden.drop_duplicates(KEY).set_index(KEY)
    c = candidate.drop_duplicates(KEY).set_index(KEY)
    lost = g.loc[g.index.difference(c.index)].reset_index()
    bench_status = lost["benchmark"].map(status)
    known_model = lost["model_version"].isin(set(candidate["model_version"]))
    included = bench_status == config.STATUS_INCLUDED
    part = lost["benchmark"].isin(merged_parts)
    out = {
        "lost_excluded": lost[bench_status.isin(["excluded", "review", "no_source"])],
        "lost_merged_part": lost[part],
        "lost_renamed_model": lost[included & ~part & ~known_model],
        "lost_other": lost[included & ~part & known_model],
        "lost_unknown_benchmark": lost[bench_status.isna()],
        "new": c.loc[c.index.difference(g.index)].reset_index(),
    }
    both = g.join(c, how="inner", lsuffix="_golden", rsuffix="_candidate")
    gs = pandas.to_numeric(both["score_golden"], errors="coerce")
    cs = pandas.to_numeric(both["score_candidate"], errors="coerce")
    moved = (gs - cs).abs() > tol
    out["score_changed"] = (both.loc[moved, ["score_golden", "score_candidate"]]
                                .assign(delta=(cs - gs)[moved]).reset_index())
    gd = both["release_date_golden"].fillna("").astype(str).str[:10]
    cd = both["release_date_candidate"].fillna("").astype(str).str[:10]
    changed = gd != cd
    out["date_changed"] = (both.loc[changed, []].assign(golden=gd[changed], candidate=cd[changed])
                               .reset_index())
    return out


def run(consumer: str, views_dir: Path = config.VIEWS_DIR,
        golden_dir: Path = config.PARITY_GOLDEN_DIR, metadata_dir: Path = config.METADATA_DIR,
        tol: float = 1e-3) -> dict[str, pandas.DataFrame]:
    """Compare one consumer's golden with the matching view."""
    golden_file, view_file = GOLDENS[consumer]
    golden = pandas.read_csv(golden_dir / golden_file, dtype=str).fillna("")
    golden["benchmark"] = golden["benchmark"].replace(name_map(metadata_dir))
    candidate = pandas.read_csv(views_dir / view_file, dtype=str).fillna("")
    table = pandas.read_csv(metadata_dir / config.BENCHMARKS_FILE, dtype=str).fillna("")
    status = dict(zip(table["name"], table["status"], strict=True))
    merges = pandas.read_csv(metadata_dir / config.SIBLING_MERGES_FILE, dtype=str)
    return compare(golden, candidate, status, set(merges["part"]), tol)


def report(consumer: str, res: dict[str, pandas.DataFrame], golden_rows: int,
           view_rows: int) -> str:
    """Markdown report: counts by cause, then the first rows of each bucket."""
    lines = [f"# Parity: {consumer}", "",
             f"Golden {golden_rows:,} rows, view {view_rows:,} rows, "
             "key (model_version, benchmark).", "",
             "| bucket | rows |", "|---|---|"]
    lines += [f"| {k} | {len(v):,} |" for k, v in res.items()]
    for k, v in res.items():
        if len(v):
            lines += ["", f"## {k} ({len(v):,})", "", "```",
                      v.head(40).to_string(index=False), "```"]
    return "\n".join(lines) + "\n"


def parity(reports_dir: Path = config.REPORTS_DIR) -> None:
    """Run both comparisons, log the counts, write the reports."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    for consumer, (golden_file, view_file) in GOLDENS.items():
        res = run(consumer)
        n_g = len(pandas.read_csv(config.PARITY_GOLDEN_DIR / golden_file))
        n_v = len(pandas.read_csv(config.VIEWS_DIR / view_file))
        log.info("%s: %s", consumer, ", ".join(f"{k} {len(v):,}" for k, v in res.items()))
        (reports_dir / f"parity_{consumer}.md").write_text(report(consumer, res, n_g, n_v))
