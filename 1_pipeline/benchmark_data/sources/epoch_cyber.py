"""Epoch's cyber ECI table: `epoch.ai/data/cyber/processed_data_for_eci.csv`.

Epoch fits a second, cyber-specific capabilities index on benchmarks that are not in its
benchmark ZIP nor on the hub (AISI CTF suites and cyber ranges, CyberGym, CTI-REALM, SCONE-Bench,
...). The long table behind it carries one row per (model, benchmark) with `performance` in
[0, 1], the model's display name and its release date. Display names say nothing about effort
or snapshot, so every name is resolved through `aliases.csv` (the feed is not splittable).
Epoch notes that several of these values were read off published plots: a weaker provenance
than the ZIP, recorded in the source label.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

FILE = "cyber_benchmarks.csv"
SOURCE_LABEL = "Epoch AI cyber ECI (values partly read off published plots)"
SOURCE_URL = "https://epoch.ai/data/cyber/processed_data_for_eci.csv"

# Benchmarks Epoch rescales: CyberGym is divided by 0.95, a cap for the ~5% of under-specified task
# descriptions (its post on Mythos's cyber capabilities, appendix). The project keeps the published
# pass@1 over the 1,507 tasks and declares no ceiling: one estimated by Epoch, it is left to the
# consumers to estimate (user, 2026-10-01).
EPOCH_RESCALED = {"CyberGym": 0.95}

# Benchmarks of the table, Epoch's name -> the project's name. Everything else is reported.
CYBER_SPEC = {
    'AISI CTF Suites - Apprentice':             'AISI CTF Suites - Apprentice',
    'AISI CTF Suites - Expert':                 'AISI CTF Suites - Expert',
    'AISI CTF Suites - Practitioner':           'AISI CTF Suites - Practitioner',
    'AISI CTF Suites - Technical Non-Expert':   'AISI CTF Suites - Technical Non-Expert',
    'AISI Cyber Ranges - Cooling Tower':        'AISI Cyber Ranges - Cooling Tower',
    'AISI Cyber Ranges - The Last Ones':        'AISI Cyber Ranges - The Last Ones',
    'CTI-REALM':                                'CTI-REALM',
    'CyScenarioBench':                          'CyScenarioBench',
    'Cybench':                                  'Cybench',        # also in the ZIP: dedup keeps the max
    'CyberGym':                                 'CyberGym',
    'ExploitBench':                             'ExploitBench',   # also in the ZIP: dedup keeps the max
    'ExploitGym':                               'ExploitGym',
    'InterCode-CTF':                            'InterCode-CTF',
    'NL2Bash':                                  'NL2Bash',
    'OpenAI CVE-Bench':                         'OpenAI CVE-Bench',
    'OpenAI Cyber Ranges':                      'OpenAI Cyber Ranges',
    'OpenAI NYU CTF Professional (Original)':   'OpenAI NYU CTF Professional (Original)',
    'OpenAI NYU CTF Professional (Refactored)': 'OpenAI NYU CTF Professional (Refactored)',
    'SCONE-Bench':                              'SCONE-Bench',
    'XBOW-Web':                                 'XBOW-Web',
}


def translate(feed_dir: Path) -> Iterator[Record]:
    """One row = one measurement; the release date travels as metadata."""
    table = pandas.read_csv(feed_dir / "epoch_cyber" / FILE, dtype={"date": str})
    unknown = sorted(set(table["benchmark"]) - set(CYBER_SPEC))
    for name in unknown:
        log.warning("epoch_cyber: ? benchmark %r: not in CYBER_SPEC", name)
    score = pandas.to_numeric(table["performance"], errors="coerce")
    for i, raw in table["Model"].items():
        bench = CYBER_SPEC.get(table["benchmark"][i])
        if bench is None or pandas.isna(raw) or pandas.isna(score[i]):
            continue
        value = score[i] * EPOCH_RESCALED.get(bench, 1.0)
        yield Record(raw, bench, value, "", "", "",
                     {"publication_date": table["date"][i]}, SOURCE_LABEL, SOURCE_URL)
