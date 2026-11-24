# Validation Results

No benchmark numbers are committed or asserted. Run `python scripts/benchmark.py` with internet access to fetch the current NASA KOI table and create a star-grouped holdout result. The output JSON records sample counts, class counts, random seeds, split strategy, and metrics. Preserve that file with any paper or demo and cite the retrieval date. Do not interpret injection recovery as benchmark classification accuracy.

Unit tests use seeded synthetic box transits and verify period/depth recovery. Their result validates implementation behavior on controlled data, not astronomical survey performance.
