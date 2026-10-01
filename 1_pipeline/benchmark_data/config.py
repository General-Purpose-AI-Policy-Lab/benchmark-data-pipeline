"""Paths, source order and output table columns."""

from pathlib import Path

# Repository layout, numbered in processing order: 0_input -> 1_pipeline -> 2_database -> 3_views.
ROOT = Path(__file__).resolve().parent.parent.parent
FEED_DIR = ROOT / "0_input" / "feed"
METADATA_DIR = ROOT / "0_input" / "metadata"
DATABASE_DIR = ROOT / "2_database"
EXPECTED_DIR = ROOT / "tests" / "expected_database"

# Ingestion order of the feeds. It matters: exact duplicates keep the first occurrence, so
# the first feed seen supplies the kept row.
SOURCE_ORDER = ("epoch", "epoch_live", "epoch_cyber", "cybench_site", "kaggle", "rand", "seal")

# feed -> do its model names follow the machine-name grammar (identity.split_name)? Otherwise
# only aliases.csv is trusted ("enumeration").
SPLITTABLE = {"epoch": True, "epoch_live": True, "epoch_cyber": False, "cybench_site": False,
              "kaggle": True, "rand": False, "seal": False}

MODEL_COLS = [
    "model_id", "base_model", "reasoning_level", "reasoning_tokens", "snapshot", "variant",
    "model_version", "organization", "country", "publication_date", "training_flop",
]
BENCH_COLS = ["benchmark_id", "name", "category", "floor", "ceiling", "access"]
SCORE_COLS = ["model_id", "benchmark_id", "score", "stderr", "harness", "feed", "source_label",
              "source_url"]
HUMAN_COLS = ["benchmark_id", "name", "group", "score", "note", "source"]

MODEL_NAMES_COLS = ["model_id", "feed", "raw_name", "n_records"]
EXCLUDED_COLS = ["name", "status", "exclusion_criterion", "records_dropped", "note"]
TABLE_FILES = ("models.csv", "benchmarks.csv", "scores.csv", "human_baselines.csv",
               "model_names.csv", "excluded_benchmarks.csv")
MANIFEST_FILE = "build_manifest.json"  # written next to the tables, not part of the golden

# Consumer views (3_views/): flat files in the schemas Multiaxis_ECI and benchmark-forecasting read.
VIEWS_DIR = ROOT / "3_views"
EXPECTED_VIEWS_DIR = ROOT / "tests" / "expected_views"
VIEW_FILES = ("all_scores_flat.csv", "dated_scores_flat.csv", "human_baselines.csv")
# Both score views carry the benchmark's floor (`lower_bound`) and known ceiling (`ceiling`).
ALL_SCORES_COLS = ["model_version", "score", "release_date", "organization", "benchmark", "stderr",
                   "source", "source_url", "feed", "category", "lower_bound", "ceiling"]
DATED_SCORES_COLS = ALL_SCORES_COLS
VIEW_HUMAN_COLS = ["benchmark", "group", "score", "note", "source"]
# feed -> coarse label, used when a row has no `source_label` of its own (a defensive fallback:
# every translator labels its rows today, so the views never show these).
FEED_LABEL = {
    "epoch": "EpochAI", "epoch_live": "EpochAI (live feed)", "epoch_cyber": "EpochAI (cyber ECI)",
    "cybench_site": "Cybench leaderboard", "kaggle": "Kaggle Open Benchmarks",
    "rand": "RAND (Dev et al. 2025) — RR-A3797-1", "seal": "Scale SEAL",
}
PARITY_GOLDEN_DIR = ROOT / "tests" / "parity" / "golden"
REPORTS_DIR = ROOT / "reports"

# Metadata files (0_input/metadata/).
BENCHMARKS_FILE = "benchmarks.csv"          # one row per benchmark: status, category, floor, access
ORGANIZATIONS_FILE = "organizations.csv"    # base_model -> organization, country (ISO alpha-2)
SIBLING_MERGES_FILE = "sibling_merges.csv"  # merged_name, part: boards averaged into one series
RELEASE_DATES_FILE = "release_dates.csv"    # (base_model, snapshot) -> researched publication_date
HUMAN_BASELINES_FILE = "human_baselines.csv"  # benchmark, group, score, note, source

# Human reference groups, from the least to the most demanding along each branch (Multiaxis_ECI's
# HUMAN_ORDER): value = the group it dominates, None = a root.
HUMAN_GROUPS = {
    "Average Human": None,
    "Skilled Generalist": "Average Human",
    "Domain Expert": "Skilled Generalist",
    "Committee of Domain Experts": "Domain Expert",
    "Top Performer": "Domain Expert",
    "Committee of Average Humans": "Average Human",
    "Committee of Skilled Generalists": "Skilled Generalist",
    "High School Qualifier": None,
    "High School Top Performer": "High School Qualifier",
}

# Epoch's model table, shipped in the ZIP: fallback source of publication_date, organization and
# country for models the score files and organizations.csv leave blank (see enrich).
EPOCH_MODEL_METADATA = FEED_DIR / "epoch" / "model_metadata.csv"
# Country names Epoch uses -> ISO 3166-1 alpha-2. An unknown name stops the build (add it here).
EPOCH_COUNTRY_ISO = {
    "United States of America": "US", "China": "CN", "France": "FR", "United Arab Emirates": "AE",
    "Canada": "CA", "United Kingdom": "GB", "Korea (Republic of)": "KR", "South Korea": "KR",
    "Germany": "DE",
    "Hong Kong": "HK", "Israel": "IL", "Japan": "JP", "Singapore": "SG", "India": "IN",
    "Switzerland": "CH", "Netherlands": "NL", "Taiwan": "TW", "Russia": "RU", "Australia": "AU",
}
# Epoch's spellings of one organization -> the project's canonical name.
EPOCH_ORGANIZATION_CANON = {
    "Google": "Google DeepMind", "DeepMind": "Google DeepMind",
    "Google DeepMind,Google": "Google DeepMind", "Google,Google DeepMind": "Google DeepMind",
}

# Variants that only describe how a model was run; a date found on one sibling applies to all.
RUN_VARIANTS = frozenset({"", "thinking"})

# Claude families that run with or without extended thinking (user decision 2026-10-01). Epoch,
# its live feed and Kaggle write a thinking run with a budget, an effort or `_unknown` ("unknown
# thinking": thinking on, budget not recorded) and a run without thinking with the bare name
# ("Claude Opus 4.6 (no thinking)"), so for these bases `_unknown` is variant `thinking` and the
# bare name effort `none` (`sources.hybrid_mode`). Third-party rows of unknown mode (system cards,
# agent harnesses) keep the bare name.
CLAUDE_HYBRID_BASES = frozenset({
    "claude-3-7-sonnet", "claude-sonnet-4", "claude-opus-4", "claude-opus-4-1", "claude-sonnet-4-5",
    "claude-haiku-4-5", "claude-opus-4-5", "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8",
    "claude-sonnet-4-6", "claude-sonnet-5", "claude-opus-5", "claude-opus-5-5", "claude-fable-5",
    "claude-fable-5-1",
})

# `status` values in benchmarks.csv. Only `included` rows reach the database.
STATUS_INCLUDED = "included"

# `access` classes in benchmarks.csv: how exposed the scored items are to training data.
ACCESS_CLASSES = frozenset({
    "public",         # the scored set downloads without human review (automatic gate included)
    "semi_private",   # a public sample or training split; the scored set is held out
    "private",        # never released (results only, or on request, reviewed by a human)
    "dynamic",        # items regenerated or refreshed over time
    "open_problems",  # statements public but unsolved: nothing to memorise (Erdos, OEIS)
})
