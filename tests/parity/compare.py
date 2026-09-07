"""Parité entre une vue plate produite ici et la sortie gelée d'un consommateur.

Les deux fichiers sont joints sur (model_version, benchmark). On liste les paires perdues,
les paires nouvelles, les scores qui bougent de plus de `tol` et les dates qui changent.
Usage :
    python tests/parity/compare.py <golden.csv> <candidate.csv> [--tol 0.001]
"""

import argparse
import sys
from pathlib import Path

import pandas

KEY = ["model_version", "benchmark"]


def compare(golden: pandas.DataFrame, candidate: pandas.DataFrame, tol: float = 1e-3) -> dict:
    """-> {'lost', 'new', 'score_changed', 'date_changed'} : quatre DataFrames."""
    g = golden.drop_duplicates(KEY).set_index(KEY)
    c = candidate.drop_duplicates(KEY).set_index(KEY)
    lost = g.loc[g.index.difference(c.index)].reset_index()
    new = c.loc[c.index.difference(g.index)].reset_index()
    both = g.join(c, how="inner", lsuffix="_golden", rsuffix="_candidate")
    delta = (both["score_candidate"] - both["score_golden"]).abs()
    moved = delta > tol
    score_changed = both.loc[moved, ["score_golden", "score_candidate"]].assign(delta=delta[moved])
    out = {"lost": lost, "new": new, "score_changed": score_changed.reset_index()}
    if "release_date_golden" in both.columns:
        gd = both["release_date_golden"].fillna("").astype(str).str[:10]
        cd = both["release_date_candidate"].fillna("").astype(str).str[:10]
        changed = gd != cd
        out["date_changed"] = (both.loc[changed, []]
                               .assign(golden=gd[changed], candidate=cd[changed]).reset_index())
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("golden", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--tol", type=float, default=1e-3)
    a = p.parse_args(argv)
    res = compare(pandas.read_csv(a.golden), pandas.read_csv(a.candidate), a.tol)
    for name, df in res.items():
        print(f"\n== {name}: {len(df)}")
        if len(df):
            print(df.head(25).to_string(index=False))
    return 0 if all(len(df) == 0 for df in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
