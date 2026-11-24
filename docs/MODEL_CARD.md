# Model Card: KOI Disposition Benchmark

## Intended use
Research benchmark comparing catalog feature classifiers on held-out Kepler Objects of Interest. Not a live-transit model, planet confirmation system, or calibrated probability of existence.

## Data
NASA Exoplanet Archive cumulative KOI table fetched by `scripts/benchmark.py`. CONFIRMED and CANDIDATE are grouped as positive; FALSE POSITIVE as negative; other dispositions excluded. Features are catalog period, depth, duration, SNR, impact, radius, insolation, and stellar temperature/surface gravity where present. Disposition and verdict fields are excluded from features.

## Evaluation
A seeded 75/25 `GroupShuffleSplit` holds out `kepid` groups. Reports accuracy, precision, recall, F1, PR-AUC, ROC-AUC, Brier score and confusion matrix. A separate subset of training stars calibrates the RF using sigmoid calibration. Results are not supplied until benchmark runs; current catalogs and sample selection change over time.

## Limitations and risks
Archive KOIs are selected candidates, not a random survey sample. Disposition categories are not independent of catalog features, and candidates include unconfirmed objects. The archive feature distributions do not match arbitrary uploaded light curves. Do not use this output for follow-up prioritization without domain validation. SHAP values are not included in this release; tree feature importance is not a per-candidate causal explanation.
