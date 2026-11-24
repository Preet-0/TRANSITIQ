# Reproducible demonstration

1. Open Analyze Star and search `Kepler-10` in mission Kepler, then inspect the returned MAST products and select a public long-cadence product. Network access is required.
2. Run BLS and inspect original, cleaned, folded, and periodogram views.
3. Record all displayed period/depth/duration and photometric vetting warnings. These are candidates, not confirmed discoveries.
4. In Validation Lab inject a 1,000 ppm, 5-day signal into the observed flux and review whether period/depth fall within the stated tolerances.
5. Repeat with lower depth/noise settings and compare recovery, clearly labeled as a synthetic injected-signal experiment.
6. For classifier metrics, run `python scripts/benchmark.py` and cite the generated held-out metrics and archive retrieval date.
