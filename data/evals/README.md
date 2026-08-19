# Local eval packages

One directory per eval run locally: `data/evals/<eval-name>/`.

Each package holds what makes the score reproducible: a README with
provenance (model, date, harness, settings), the grader prompt or config,
and the raw per-item results as produced by the harness (CSV or JSONL).

The pipeline never reads this directory. The aggregate score enters the
merged table through a `data/curated/row_adds_YYYY-MM-DD_<name>.csv` file
(merged 8-column schema plus a `reason` column) whose `reason` points back
here. Raw harness logs kept in a package are what an every_eval_ever
converter would consume if the data is ever exported (see
`docs/every_eval_ever.md`).
