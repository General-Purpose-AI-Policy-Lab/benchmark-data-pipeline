"""Regenerate docs/release_dates_consistency.csv: every model whose date sources disagree.

Sources compared, per model of the database: the modal Epoch `Release date` of the score files,
Epoch's `model_metadata.csv`, `0_input/metadata/release_dates.csv` (researched dates),
benchmark-forecasting's manual maps and Multiaxis_ECI's `config.RELEASE_DATES` (both read from
the sibling repositories when present), and the date the build finally kept. Run from the
repository root: `.venv/bin/python 1_pipeline/scripts/release_dates_consistency.py`.
"""

import re
import sys

import pandas

from benchmark_data import config
from benchmark_data.identity import IDENT_COLS, load_aliases, model_id, resolve_model
from benchmark_data.steps.enrich import load_epoch_model_metadata
from benchmark_data.steps.ingest import ingest

OUT = config.ROOT / "docs" / "release_dates_consistency.csv"
MBF = config.ROOT.parent / "Model_Benchmark_forecasting" / "tmp" / "0_read.py"
MX = config.ROOT.parent / "Multiaxis_ECI" / "multiaxis_eci" / "config.py"


def _dict_block(text: str, name: str) -> str:
    m = re.search(name + r"\s*=\s*\{", text)
    if not m:
        return ""
    depth, i = 0, m.end() - 1
    while i < len(text):
        depth += text[i] == "{"
        depth -= text[i] == "}"
        if depth == 0:
            return text[m.end():i]
        i += 1
    return ""


def consumer_dates() -> tuple[dict[str, str], dict[str, str]]:
    """{raw name: date} from benchmark-forecasting's maps and Multiaxis_ECI's config."""
    mbf, mx = {}, {}
    if MBF.exists():
        text = MBF.read_text()
        for block in ("MANUAL_DATE_MAP", "DATE_OVERRIDES"):
            for k, y, mo, d in re.findall(r'"([^"]+)":\s*date\((\d+),\s*(\d+),\s*(\d+)\)',
                                          _dict_block(text, block)):
                mbf[k] = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    if MX.exists():
        for k, v in re.findall(r'"([^"]+)":\s*"(\d{4}-\d{2}-\d{2})"',
                               _dict_block(MX.read_text(), "RELEASE_DATES")):
            mx[k] = v
    return mbf, mx


def resolve_any(raw: str, aliases: dict[str, dict]) -> str | None:
    """model_id of a consumer's raw name, through every feed's aliases then the grammar."""
    for feed in config.SOURCE_ORDER:
        status, ident, _ = resolve_model(raw, aliases[feed], config.SPLITTABLE[feed])
        if status == "ok":
            return model_id(ident)
    return None


def main() -> int:
    result = ingest()
    models = pandas.DataFrame(result.models.values())
    obs = pandas.DataFrame(result.meta_obs)
    obs = obs[obs["publication_date"].fillna("").astype(str).str.strip() != ""]
    epoch_col = (obs.value_counts(["model_id", "publication_date"]).reset_index(name="n")
                    .sort_values(["n", "publication_date"], ascending=[False, True])
                    .drop_duplicates("model_id").set_index("model_id")["publication_date"])
    epoch_meta = load_epoch_model_metadata().set_index("model_id")["date"]
    manual = pandas.read_csv(config.METADATA_DIR / config.RELEASE_DATES_FILE, dtype=str).fillna("")
    manual_by = {(r.base_model, r.snapshot, r.variant): r.publication_date
                 for r in manual.itertuples()}
    aliases = {s: load_aliases(config.FEED_DIR / s / "aliases.csv") for s in config.SOURCE_ORDER}
    mbf_raw, mx_raw = consumer_dates()
    mbf, mx = {}, {}
    for raw, d in mbf_raw.items():
        if (mid := resolve_any(raw, aliases)):
            mbf.setdefault(mid, set()).add(d)
    for raw, d in mx_raw.items():
        if (mid := resolve_any(raw, aliases)):
            mx.setdefault(mid, set()).add(d)
    final = pandas.read_csv(config.DATABASE_DIR / "models.csv", dtype=str).fillna("")
    final = final.set_index("model_id")["publication_date"]

    rows = []
    for r in models.itertuples():
        mid = r.model_id
        key_variant = r.variant if r.variant not in config.RUN_VARIANTS else ""
        srcs = {
            "epoch_release_date": epoch_col.get(mid, ""),
            "epoch_model_metadata": epoch_meta.get(mid, ""),
            "release_dates_csv": manual_by.get((r.base_model, r.snapshot, key_variant), ""),
            "mbf_manual": "|".join(sorted(mbf.get(mid, set()))),
            "mx_config": "|".join(sorted(mx.get(mid, set()))),
        }
        distinct = {d for v in srcs.values() for d in v.split("|") if d}
        if len(distinct) < 2:
            continue
        rows.append({**{c: getattr(r, c) for c in IDENT_COLS}, **srcs, "kept": final.get(mid, ""),
                     "n_distinct": len(distinct)})
    out = pandas.DataFrame(rows).sort_values(IDENT_COLS)
    out.to_csv(OUT, index=False)
    print(f"{len(out)} model(s) with disagreeing date sources -> {OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
