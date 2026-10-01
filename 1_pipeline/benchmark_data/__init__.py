"""Benchmark data pipeline: raw feeds -> 2_database/{models,benchmarks,scores}.csv.

The build is offline and deterministic (it only reads `0_input/feed/` and `0_input/metadata/`);
only `refresh` touches the network. Entry point: `python -m benchmark_data build`.
"""

SCHEMA_VERSION = "2.2"
