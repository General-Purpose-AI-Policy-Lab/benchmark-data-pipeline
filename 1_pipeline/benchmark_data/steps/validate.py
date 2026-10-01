"""Database invariants, checked before writing."""

import pandas

from benchmark_data.identity import IDENT_COLS


class ValidationError(Exception):
    """A database invariant is violated."""


def validate(models: pandas.DataFrame, benchmarks: pandas.DataFrame,
             scores: pandas.DataFrame, human: pandas.DataFrame | None = None) -> None:
    """Unique keys, no orphan, scores in [0, 1].

    Raises:
        ValidationError: the first violated invariant.
    """
    checks = [
        (not models.duplicated(IDENT_COLS).any(), "duplicated identity tuple"),
        (not models.duplicated("model_version").any(), "duplicated model_version"),
        (not benchmarks.duplicated("name").any(), "duplicated benchmark name"),
        (not scores.duplicated(["model_id", "benchmark_id"]).any(), "duplicated score"),
        (set(scores["model_id"]) <= set(models["model_id"]), "orphan model_id"),
        (set(scores["benchmark_id"]) <= set(benchmarks["benchmark_id"]), "orphan benchmark_id"),
        (bool(scores["score"].between(0, 1).all()), "score outside [0, 1]"),
    ]
    if human is not None:
        checks += [
            (set(human["benchmark_id"]) <= set(benchmarks["benchmark_id"]),
             "orphan benchmark_id in human baselines"),
            (bool(human["score"].between(0, 1).all()), "human baseline outside [0, 1]"),
        ]
    for ok, message in checks:
        if not ok:
            raise ValidationError(message)
