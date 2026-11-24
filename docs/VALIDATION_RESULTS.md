# Validation Results

**NASA Exoplanet Archive KOI table retrieved 2026-11-24 16:46 UTC.** The reproducible run used 9,564 labeled KOIs (4,839 false positives; 4,725 confirmed or candidate positives). A seeded `GroupShuffleSplit` held out 25% by `kepid`: 2,417 test records (1,227 negatives; 1,190 positives). Random seed: 2026.

| Model | Accuracy | Precision | Recall | F1 | PR-AUC | ROC-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic baseline | 0.699 | 0.644 | 0.866 | 0.739 | 0.722 | 0.774 | 0.190 |
| Random Forest | 0.835 | 0.829 | 0.839 | 0.834 | 0.911 | 0.917 | 0.117 |

The calibrated Random Forest obtained test Brier score 0.117 and PR-AUC 0.910. Its probability calibration used a held-out subset of training-star groups; the independent test remained untouched. The trained model is produced at `models/artifacts/koi_classifier.joblib` but is excluded from Git; rerun `python scripts/benchmark.py` to regenerate the model and update the metrics JSON.

The Random Forest confusion matrix in `[TN, FP, FN, TP]` order is `[1021, 206, 192, 998]`. `docs/benchmark_results.json` contains the full timestamped result and is loaded by the Validation Lab.

These are catalogue-disposition classification metrics, **not** transit-search accuracy for arbitrary light curves. KOIs are a selected population, candidate labels are not confirmations, and catalog features/dispositions carry survey-selection effects. The test grouping prevents stars from crossing the train/test boundary but cannot remove all catalog-level bias. This is a one-time seeded holdout, not repeated cross-validation.

Unit tests use seeded synthetic box transits and verify period/depth recovery. Their result validates implementation behavior on controlled data, not astronomical survey performance. Injection-recovery on a user's observed curve remains a separate experiment; no recovery rate is claimed until that experiment is run.
