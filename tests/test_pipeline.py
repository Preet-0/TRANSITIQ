from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import numpy as np
import pytest
from transitiq.data import LightCurve
from transitiq.preprocess import detrend, transit_preservation
from transitiq.detection import search_bls
from transitiq.vetting import vet_candidate
from transitiq.experiments import simulate_transit, run_injection
from transitiq.tls import verify_tls
from transitiq.reports import make_pdf_report


def synthetic(period=3.2, depth=0.01, duration=3.0, seed=4):
    rng = np.random.default_rng(seed)
    t = np.arange(0, 60, 0.02)
    phase = np.abs(((t - 0.7 + period / 2) % period) - period / 2)
    y = 1 + 0.0003 * np.sin(t / 12) + rng.normal(0, 0.001, len(t))
    y[phase < duration / 48] -= depth
    return t, y


def test_validation_deduplicates_and_sorts():
    c = LightCurve(np.array([2, 1, 1, *range(3, 34)], float), np.ones(34)).validate()
    assert np.all(np.diff(c.time) > 0) and len(c.time) == 33


def test_invalid_too_few():
    with pytest.raises(ValueError):
        LightCurve(np.arange(10), np.ones(10)).validate()


def test_bls_recovers_period_and_depth():
    t, y = synthetic()
    c = LightCurve(t, y).validate()
    clean, _, _ = detrend(c, window_days=1.2)
    r = search_bls(t, clean, 0.5, 8)
    assert abs(r["period_days"] - 3.2) < 0.03
    assert abs(r["depth_fraction"] - 0.01) < 0.004
    assert r["duration_hours"] > 0 and r["event_count"] >= 10


def test_preservation_metric():
    m = np.arange(10) < 4
    r = transit_preservation(
        np.r_[np.repeat(0.99, 4), np.ones(6)], np.r_[np.repeat(0.99, 4), np.ones(6)], m
    )
    assert abs(r["attenuation_fraction"]) < 1e-8


def test_simulator():
    t = np.arange(0, 15, 0.02)
    f = simulate_transit(t, 3, 3, 0.01, 0.2)
    assert np.min(f) < 1 and np.sum(f < 1) > 0


def test_injection_experiment_executes():
    t, y = synthetic()
    result = run_injection(t, y, 3.2, 3, 0.008, epoch=0.7)
    assert result["matching_tolerances"]["period_fraction"] == 0.02
    assert result["period_error_fraction"] < 0.02


def test_vetting_returns_caveat():
    t, y = synthetic()
    c = LightCurve(t, y)
    clean, _, _ = detrend(c, 1.2)
    r = search_bls(t, clean, 0.5, 8)
    v = vet_candidate(t, clean, r)
    assert "not external confirmation" in v["caveat"]


def test_cached_real_kepler_demo_recovers_known_period():
    root = Path(__file__).resolve().parents[1] / "data" / "demo"
    frame = pd.read_csv(root / "kepler10_q17_longcadence.csv")
    provenance = json.loads((root / "kepler10_q17_longcadence.json").read_text())
    curve = LightCurve.from_frame(frame, "time", "flux", "flux_err", "quality", provenance)
    clean, _, _ = detrend(curve)
    result = search_bls(curve.time, clean, min_period=0.5, max_period=15.0)
    assert (
        provenance["catalogue_disposition"]
        == "CONFIRMED in NASA Exoplanet Archive cumulative table retrieved 2026-11-24"
    )
    assert (
        abs(result["period_days"] - provenance["catalogue_period_days"])
        / provenance["catalogue_period_days"]
        < 0.01
    )


def test_tls_independently_verifies_cached_kepler_demo():
    root = Path(__file__).resolve().parents[1] / "data" / "demo"
    frame = pd.read_csv(root / "kepler10_q17_longcadence.csv")
    curve = LightCurve.from_frame(frame, "time", "flux", "flux_err", "quality")
    clean, _, _ = detrend(curve)
    result = verify_tls(curve.time, clean, 0.5, 15.0)
    assert result["available"]
    assert abs(result["period_days"] - 0.837491) / 0.837491 < 0.01


def test_pdf_report_contains_pdf_document():
    report = make_pdf_report(
        {
            "target": "Test Star",
            "detection": {
                "period_days": 2.0,
                "epoch_days": 0.5,
                "duration_hours": 2.0,
                "depth_ppm": 1000,
                "depth_fraction": 0.001,
                "bls_power": 0.4,
                "snr_approx": 12,
            },
            "vetting": {"label": "Uncertain", "flags": {"few_events": True}},
            "time": [0, 1, 2],
            "raw_flux": [1.0, 0.999, 1.0],
            "cleaned_flux": [1.0, 0.999, 1.0],
        }
    )
    assert report.startswith(b"%PDF")


def test_cached_real_false_positive_example_reproduces_archived_period():
    root = Path(__file__).resolve().parents[1] / "data" / "demo"
    frame = pd.read_csv(root / "kepler_fp_koi6139.csv")
    provenance = json.loads((root / "kepler_fp_koi6139.json").read_text())
    curve = LightCurve.from_frame(frame, "time", "flux", "flux_err", "quality", provenance)
    clean, _, _ = detrend(curve)
    result = search_bls(curve.time, clean, min_period=0.5, max_period=15.0)
    assert "FALSE POSITIVE" in provenance["catalogue_disposition"]
    assert (
        abs(result["period_days"] - provenance["catalogue_period_days"])
        / provenance["catalogue_period_days"]
        < 0.01
    )
