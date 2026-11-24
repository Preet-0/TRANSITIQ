from __future__ import annotations
import sys
import warnings
import numpy as np


def verify_tls(time, flux, min_period, max_period, oversampling_factor=1):
    """Run TLS independently; isolate batman/distutils compatibility for Py3.12."""
    try:
        import setuptools._distutils as distutils
        import setuptools._distutils.ccompiler as ccompiler

        sys.modules.setdefault("distutils", distutils)
        sys.modules.setdefault("distutils.ccompiler", ccompiler)
        from transitleastsquares import transitleastsquares
    except Exception as exc:
        return {"available": False, "error": f"TLS dependency unavailable: {exc}"}
    t, y = np.asarray(time, float), np.asarray(flux, float)
    if len(t) < 100 or max_period <= min_period:
        return {
            "available": False,
            "error": "TLS needs at least 100 samples and valid period limits.",
        }
    model = transitleastsquares(t, y)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = model.power(
            period_min=float(min_period),
            period_max=float(max_period),
            oversampling_factor=int(oversampling_factor),
            use_threads=1,
            show_progress_bar=False,
            verbose=False,
        )
    depth = float(1.0 - result.depth) if np.isfinite(result.depth) else float("nan")
    return {
        "available": True,
        "period_days": float(result.period),
        "epoch_days": float(result.T0),
        "duration_hours": float(result.duration * 24),
        "depth_fraction": depth,
        "depth_ppm": depth * 1e6,
        "sde": float(result.SDE),
        "snr": float(result.snr),
        "rp_rs": float(result.rp_rs),
        "false_alarm_probability": float(result.FAP),
        "periodogram": {
            "period": np.asarray(result.periods).tolist(),
            "power": np.asarray(result.power).tolist(),
        },
        "warnings": [str(w.message) for w in captured],
    }
