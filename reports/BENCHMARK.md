# Distributed benchmark — 2026-10-19

Verified [GitHub Actions run 39220699456](https://github.com/mingyanc74/patternforge/actions/runs/39220699456), commit `30dc0535`.

The S3 and model endpoints were explicitly deterministic test fixtures. PostgreSQL, Redis, Celery, the isolated Spark driver, master and two workers were real. This is distributed pipeline evidence, not real AWS authorization or genuine-model latency.

- Generated CSV: **3,000,000 rows × 10 columns**, **413,666,734 bytes**.
- Linux x86-64 hosted runner, 2 logical CPUs, Python 3.11.17, Spark 3.5.8, Java 17.
- Two active executors, each 1 core and 1 GB; driver 1 GB; 8 transformation partitions.
- Host RAM was not recorded by this run; no RAM value is inferred from runner branding.

| Operation | Exact output rows | Spark read/transform/write seconds | Active executors |
|---|---:|---:|---:|
| Regex replacement | 3,000,000 | 102.584 | 2 |
| Regex field extraction | 3,000,000 | 105.357 | 2 |
| Text normalization | 3,000,000 | 107.473 | 2 |

The harness verified expected changed-cell counts and deterministic samples, nonoverlapping result pages, Excel worksheet discovery plus transformation, an actual Redis plan-cache hit and cross-session isolation. Cancellation was requested only after the application appeared in the Spark master's active applications; it disappeared in **1.17 seconds** and the persistent job was cancelled.

The entire harness took **455.52 seconds**. That includes dataset creation/upload to the local fixture, inspection, the three large transformations, Excel, cache and cancellation checks. It excludes container build/start and does not isolate real-cloud network/LLM time. `spark_seconds` includes driver startup, reading, processing and writing; it is not an HTTP response-time measurement.

All row counts and timings are observations from one run, not service guarantees. CSV multiline correctness can make one input object unsplittable during ingestion; transformations still ran across 8 partitions and 2 executors. Parquet publication writes bounded files for cursor pagination; large outputs require adequate disk and eventual retention cleanup.

Reproduce with the test overlay and `python scripts/smoke_e2e.py --rows 3000000`. See the workflow artifact `distributed-e2e-report` for the original machine-readable JSON.
