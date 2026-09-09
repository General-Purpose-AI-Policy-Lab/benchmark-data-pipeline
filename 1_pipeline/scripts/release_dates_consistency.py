"""Regenerate docs/release_dates_consistency.csv: every model whose date sources disagree.

Sources compared, per model of the database: the modal Epoch `Release date` of the score files,
Epoch's `model_metadata.csv`, `0_input/metadata/release_dates.csv` (researched dates), and the
date the build finally kept. The consumers' own date maps (benchmark-forecasting's manual maps,
Multiaxis_ECI's `config.RELEASE_DATES`) were compared here until 2026-09-08 and then absorbed
into `release_dates.csv`; both repositories now read the dates from the views. Run from the
repository root: `.venv/bin/python 1_pipeline/scripts/release_dates_consistency.py`.
"""

import sys

import pandas

from benchmark_data import config
from benchmark_data.identity import IDENT_COLS
from benchmark_data.steps.enrich import load_epoch_model_metadata
from benchmark_data.steps.ingest import ingest

OUT = config.ROOT / "docs" / "release_dates_consistency.csv"




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
