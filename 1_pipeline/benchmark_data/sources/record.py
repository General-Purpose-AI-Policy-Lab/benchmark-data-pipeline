"""The common shape every source produces: one raw measurement, before name resolution."""

from typing import Any, NamedTuple


class Record(NamedTuple):
    """One measurement in the project's format, as published by the source.

    Attributes:
        raw_name: model name as the source writes it (resolved later by identity).
        benchmark: canonical benchmark name (set by the source's _SPEC dictionary).
        score: proportion in [0, 1].
        stderr: published standard error, '' when absent.
        effort: reasoning effort read outside the name (Epoch's `Name` column), '' otherwise.
        harness: scaffold / agent framework that produced the score, '' when unknown.
        meta: metadata gleaned for the second pass (publication_date, training_flop), {} otherwise.
        source_label: where the number was published (a leaderboard, a paper), as the feed says it.
        source_url: link to that publication, '' when the feed gives none.
    """

    raw_name: Any
    benchmark: str
    score: float
    stderr: Any = ""
    effort: str = ""
    harness: str = ""
    meta: dict = {}
    source_label: str = ""
    source_url: str = ""
