# Reproducibility Guide

- Python 3.12.5; dependency versions are pinned in requirements.txt and pyproject.toml.
- Run unit tests with pytest. Synthetic tests use fixed random seeds; real-data tests use committed MAST Kepler examples.
- Recreate the classifier benchmark and model with python scripts/benchmark.py. It fetches the live cumulative KOI table, applies a fixed random seed and groups the holdout by `kepid`. Metrics are timestamped in docs/benchmark_results.json.
- Recreate the cached Kepler-10 sample with python scripts/download_demo_data.py. It searches MAST through Lightkurve and chooses a public long-cadence product; archive products and quarter availability can evolve.
- Injection experiments record the seed, depth, period, duration, added noise, recovery thresholds and measured errors in downloadable CSV/JSON.
- The benchmark and injection experiments answer different questions: archive-disposition classification versus recovery of a known synthetic transit in measured noise.
