"""Feed `epoch`: the CSV files of `epoch.ai/data/benchmark_data.zip`, one file = one benchmark.

Benchmark names follow the `benchmark` column of Epoch's own `benchmark_metadata.csv` (decision
B1, 2026-09-04), with the version number appended where a benchmark has several.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pandas

from benchmark_data.config import CLAUDE_HYBRID_BASES
from benchmark_data.identity import hybrid_mode
from benchmark_data.sources.record import Record

log = logging.getLogger(__name__)

# Dictionary: ZIP file -> (benchmark, score column, divisor).
FILE_SPEC = {
    'adversarial_nli_external.csv':       ('ANLI', 'Score', 1.0),
    'aider_polyglot_external.csv':        ('Aider Polyglot', 'Percent correct', 100.0),
    'apex_agents_external.csv':           ('APEX-Agents', 'Pass@1 score', 1.0),
    'arc_agi_2_external.csv':             ('ARC-AGI-2', 'Score', 1.0),
    'arc_agi_external.csv':               ('ARC-AGI', 'Score', 1.0),
    'arc_ai2_external.csv':               ('ARC AI2', 'Challenge score', 1.0),
    'balrog_external.csv':                ('Balrog', 'Average progress', 1.0),
    'bbh_external.csv':                   ('BBH', 'Average', 1.0),
    'blueprint_bench_2_external.csv':     ('BlueprintBench 2', 'Score', 1.0),
    'bool_q_external.csv':                ('BoolQ', 'Score', 1.0),
    'cad_eval_external.csv':              ('CadEval', 'Overall pass (%)', 1.0),
    'cl_bench_external.csv':              ('CL-bench', 'Overall', 1.0),
    'cl_bench_life_external.csv':         ('CL-bench Life', 'Overall', 1.0),
    'common_sense_qa_2_external.csv':     ('CSQA2', 'Score', 1.0),
    'critpt_external.csv':                ('CritPt', 'Accuracy', 1.0),
    'cursorbench_external.csv':           ('CursorBench', 'Score', 1.0),
    'cybench_external.csv':               ('Cybench', 'Unguided % Solved', 1.0),
    'deepresearchbench_external.csv':     ('DeepResearch Bench', 'Average score', 1.0),
    'deepswe_external.csv':               ('DeepSWE', 'Pass@1', 1.0),
    'dtbench_external.csv':               ('DTBench', 'Accuracy', 1.0),
    'enigma_eval_external.csv':           ('EnigmaEval', 'Accuracy', 1.0),
    'exploitbench_external.csv':          ('ExploitBench', 'Mean capability', 1.0),
    'fictionlivebench_external.csv':      ('Fiction.LiveBench', '120k token score', 1.0),
    'forecastbench_external.csv':         ('ForecastBench', 'Overall score', 100.0),
    'frontiercode_external.csv':          ('FrontierCode', 'Main score', 1.0),
    'frontierswe_external.csv':           ('FrontierSWE v2', 'Score', 1.0),
    'gbaeval_external.csv':               ('GBAEval', 'Overall score', 1.0),
    'gdp_pdf_external.csv':               ('GDP.pdf', 'GDP.pdf score', 1.0),
    'gdpval_external.csv':                ('GDPval', 'Win + tie rate (%)', 1.0),
    'geobench_external.csv':              ('GeoBench', 'ACW Country %', 1.0),
    'gsm8k_external.csv':                 ('GSM8K', 'EM', 1.0),
    'gso_external.csv':                   ('GSO-Bench', 'Score OPT@1', 1.0),
    'hella_swag_external.csv':            ('HellaSwag', 'Overall accuracy', 1.0),
    'hle_external.csv':                   ('HLE', 'Accuracy', 1.0),
    'lambada_external.csv':               ('LAMBADA', 'Score', 1.0),
    'lech_mazur_writing_external.csv':    ('Lech Mazur Writing', 'Mean score', 10.0),
    'live_bench_external.csv':            ('LiveBench', 'Global average', 100.0),
    'lmca_external.csv':                  ('LMCA', 'Score', 100.0),
    'metr_time_horizons_external.csv':    ('METR Time Horizons', 'average_score', 1.0),
    'mindcube_external.csv':              ('MindCube', 'Overall score', 1.0),
    'mmlu_external.csv':                  ('MMLU', 'EM', 1.0),
    'open_book_qa_external.csv':          ('OpenBookQA', 'Accuracy', 1.0),
    'os_world_external.csv':              ('OSWorld', 'Score', 100.0),
    'osworld_2_external.csv':             ('OSWorld 2.0', 'Binary accuracy', 1.0),
    'piqa_external.csv':                  ('PIQA', 'Score', 1.0),
    'posttrainbench_external.csv':        ('PostTrainBench v1.1', 'Average (%)', 1.0),
    'proofbench_external.csv':            ('ProofBench', 'Accuracy', 1.0),
    'rli_external.csv':                   ('Remote Labor Index', 'Score', 1.0),
    'scicode_external.csv':               ('SciCode', 'Score', 1.0),
    'science_qa_external.csv':            ('ScienceQA', 'Score', 1.0),
    'simplebench_external.csv':           ('SimpleBench', 'Score (AVG@5)', 1.0),
    'spatialviz_bench_external.csv':      ('SpatialViz-Bench', 'Overall score', 1.0),
    'superglue_external.csv':             ('SuperGLUE', 'Score', 1.0),
    'surface_evolver_bench_external.csv': ('Surface Evolver Bench', 'Mean score', 1.0),
    'terminalbench_external.csv':         ('Terminal Bench 2.0', 'Accuracy mean', 1.0),
    'the_agent_company_external.csv':     ('The Agent Company', '% Score', 1.0),
    'trivia_qa_external.csv':             ('TriviaQA', 'EM', 1.0),
    'video_mme_external.csv':             ('VideoMME', 'Overall (no subtitles)', 1.0),
    'vpct_external.csv':                  ('VPCT', 'Correct', 1.0),
    'weirdml_external.csv':               ('WeirdML v2', 'Accuracy', 1.0),
    'weirdml_v3_external.csv':            ('WeirdML v3', 'Score', 1.0),
    'wino_grande_external.csv':           ('WinoGrande', 'Accuracy', 1.0),
}

# Files set aside, with the reason. Files that are not scores, or whose score is not a
# proportion in [0, 1] (criterion 1), never get a score; the benchmarks among them also carry an
# `excluded` row in 0_input/metadata/benchmarks.csv, where the judgement-based exclusions
# (criteria 2-4) live, so excluded_benchmarks.csv is complete. Files listed here that the current
# ZIP no longer ships would be reported again if they came back.
FILE_SKIP = {
    'ale_bench_external.csv':                    'competition points (~138-2041), not a proportion in [0, 1]',
    'algotune_external.csv':                     'harmonic-mean speedup >= 1x against a reference implementation; a 1 - 1/speedup rescaling puts it on a scale no other benchmark shares (criterion 1)',
    'benchmark_metadata.csv':                    "Epoch's benchmark metadata table (random_baseline, score_ceiling, superseded_by), not scores; read by the metadata pass",
    'eci_scores.csv':                            "Epoch Capabilities Index per model (eci, confidence interval), an aggregate over benchmarks, not a benchmark score",
    'edi_scores.csv':                            "Epoch Difficulty Index per benchmark, a derived quantity, not a score",
    'processed_data_for_eci.csv':                "Epoch's own long table of the scores feeding the ECI: the same numbers as the per-benchmark files, kept once",
    'btf3_external.csv':                         'pooled Brier/RPS loss with no published chance baseline: the floor cannot be derived',
    'chess_puzzles.csv':                         'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'ebr_bench.csv':                             'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'eci_benchmark_difficulties_and_slopes.csv': 'IRT parameters fitted by Epoch, downstream of this pipeline',
    'epoch_capabilities_index.csv':              "Epoch's ECI: an output downstream of this pipeline, not a benchmark",
    'furniture_assembly.csv':                    'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'frontiermath.csv':                          'FrontierMath Tiers 1-3 v1; ingested from the live feed (epoch_live), which pins the problem-set version',
    'frontiermath_erdos.csv':                    'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'frontiermath_tier_4.csv':                   'FrontierMath Tier 4 v1; ingested from the live feed (epoch_live)',
    'frontiermath_tier_4_v2.csv':                'FrontierMath Tier 4 v2; ingested from the live feed (epoch_live)',
    'frontiermath_tiers_1_3_v2.csv':             'FrontierMath Tiers 1-3 v2; ingested from the live feed (epoch_live)',
    'gpqa_diamond.csv':                          'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'math_level_5.csv':                          'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'mirrorcode.csv':                            'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'model_metadata.csv':                        "Epoch's model metadata table (date, organization, country, accessibility), not scores; read by the metadata pass",
    'mystery_game_puzzles.csv':                  'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'otis_mock_aime_2024_2025.csv':              'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'simpleqa_verified.csv':                     'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'swe_bench_verified.csv':                    'Epoch internal evaluation; ingested from the live feed (epoch_live)',
    'vending_bench_2_external.csv':              'end-of-year balance in dollars, not a proportion in [0, 1]',
    'webdev_arena_external.csv':                 'arena Elo score, not a proportion in [0, 1]',
}

# Column naming the harness / scaffold / agent framework, where Epoch publishes one. `Agent` is
# only taken where it names a framework; on OSWorld it labels the model run itself.
FILE_HARNESS_COLUMN = {
    'deepswe_external.csv':        'Harness',
    'exploitbench_external.csv':   'Harness',
    'frontiercode_external.csv':   'Harness',
    'frontierswe_external.csv':    'Harness',
    'gso_external.csv':            'Scaffold',
    'posttrainbench_external.csv': 'Scaffold',
    'terminalbench_external.csv':  'Agent',
}

# Refusal-rate column of the files whose score counts a refused item as wrong, and the rate from
# which a run is left out (user, 2026-10-05): GeoBench's country accuracy treats a refused image as
# a miss, and its average score is taken over the answered images only, so neither measures the
# model on the full set. o3 at high effort refuses 18% of the images (country accuracy 0.60, against
# 0.74 at medium with no refusal), o4-mini 9-10%, Llama 3.2 90B Vision 7%; every other run 0%.
FILE_REFUSAL = {'geobench_external.csv': ('ACW Refusal', 0.05)}

# Effort sometimes hidden in the displayed `Name`: "Gemini 3 Flash Preview (High)".
EFFORT_RE = r"(?i)\((?:thinking,\s*)?(minimal|low|medium|high|x-high|xhigh|max|none)\)\s*$"

_both = sorted(set(FILE_SPEC) & set(FILE_SKIP))
if _both:
    raise ValueError(f"in both FILE_SPEC and FILE_SKIP: {_both}")


# Label when a file carries no `Source` column (Epoch's own aggregation).
SOURCE_LABEL = "EpochAI"


def translate(feed_dir: Path) -> Iterator[Record]:
    """One file = one benchmark; every row with a score and a `Model version` becomes a Record.

    Files in neither FILE_SPEC nor FILE_SKIP are reported and never ingested.
    """
    unrecognized, blank, skipped, refused = [], 0, 0, 0
    for path in sorted((feed_dir / "epoch").glob("*.csv")):
        if path.name == "aliases.csv":  # the dictionary is not data
            continue
        if path.name in FILE_SKIP:
            skipped += 1
            continue
        if path.name not in FILE_SPEC:
            unrecognized.append(path.name)
            continue
        bench, score_col, divisor = FILE_SPEC[path.name]
        df = pandas.read_csv(path, low_memory=False)
        score = pandas.to_numeric(df[score_col], errors="coerce") / divisor
        se = next((df[c] for c in (f"{score_col} Standard Error", "stderr") if c in df.columns), None)
        if "Name" in df.columns:
            effort = (df["Name"].astype(str).str.extract(EFFORT_RE, expand=False).str.lower()
                      .str.replace("x-high", "xhigh", regex=False).fillna(""))
        else:
            effort = pandas.Series("", index=df.index)
        harness_col = FILE_HARNESS_COLUMN.get(path.name)
        harness = (df[harness_col].fillna("").astype(str).str.strip()
                   if harness_col and harness_col in df.columns else pandas.Series("", index=df.index))
        meta_cols = {k: df[c] for k, c in (("publication_date", "Release date"),
                                           ("training_flop", "Training compute (FLOP)"))
                     if c in df.columns}
        label = (df["Source"].fillna("").astype(str).str.strip() if "Source" in df.columns
                 else pandas.Series("", index=df.index))
        url = (df["Source link"].fillna("").astype(str).str.strip() if "Source link" in df.columns
               else pandas.Series("", index=df.index))
        notes = (df["Notes"].fillna("").astype(str) if "Notes" in df.columns
                 else pandas.Series("", index=df.index))
        if path.name in FILE_REFUSAL:
            col, cap = FILE_REFUSAL[path.name]
            out = pandas.to_numeric(df[col], errors="coerce").fillna(0.0) >= cap
            refused += int((out & score.notna()).sum())
            score = score.where(~out)
        for i, raw in df["Model version"].items():
            if pandas.isna(score[i]):
                continue
            if pandas.isna(raw):  # a score without a model name: set aside and counted
                blank += 1
                continue
            yield Record(raw, bench, score[i], se[i] if se is not None else "",
                         effort[i], harness[i], {k: v[i] for k, v in meta_cols.items()},
                         label[i] or SOURCE_LABEL, url[i],
                         hybrid_mode(raw, CLAUDE_HYBRID_BASES, notes[i]))
    log.info("epoch: %d row(s) dropped for a blank `Model version`, %d file(s) skipped, "
             "%d run(s) left out for refusing too many items (FILE_REFUSAL)", blank, skipped, refused)
    for name in unrecognized:
        log.warning("epoch: ? %s: in neither FILE_SPEC nor FILE_SKIP", name)
