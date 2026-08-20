# data/raw/

## `eci_data.csv`

Original reference ECI dataset from Alexander Barry's *Epoch Capabilities
Index* (R + Stan implementation). Frozen historical snapshot — not refreshed.

**Schema:** `model,score,benchmark` (long format, scores in [0, 1]).

**Used by:**
- The modeling repo (`--eci-data-only`) fits against this
  CSV instead of the current Epoch pipeline output. Nothing in THIS repo reads
  it: the file is a frozen historical snapshot, kept for provenance. Sanity-check mode for
  comparing our PyMC recreation to the original Stan analysis. See
  `load_eci_data(eci_data_only=True)` in `data.py` in the modeling repo.
