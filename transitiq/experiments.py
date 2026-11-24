from __future__ import annotations
import numpy as np
from .preprocess import detrend
from .detection import search_bls


def simulate_transit(time, period, duration_hours, depth, epoch):
    t = np.asarray(time, float)
    phase = np.abs(((t - epoch + period / 2) % period) - period / 2)
    return np.where(phase < duration_hours / 48, 1 - depth, 1.0)


def run_injection(
    time, flux, period=5.0, duration_hours=3.0, depth=0.002, epoch=None, noise_scale=0.0, seed=123
):
    t, y = np.asarray(time, float), np.asarray(flux, float)
    epoch = float(epoch if epoch is not None else t.min() + 0.37 * period)
    transit = simulate_transit(t, period, duration_hours, depth, epoch)
    rng = np.random.default_rng(seed)
    scatter = 1.4826 * np.median(np.abs(y - np.median(y)))
    noise_sigma = max(float(noise_scale), 0.0)
    injected = y * transit + rng.normal(0, scatter * noise_sigma, len(y))
    from .data import LightCurve

    cleaned, base, params = detrend(LightCurve(t, injected))
    result = search_bls(
        t, cleaned, min_period=max(0.3, period * 0.5), max_period=min(np.ptp(t) / 2, period * 1.5)
    )
    perr = abs(result["period_days"] - period) / period
    derr = abs(result["depth_fraction"] - depth) / depth
    mask = transit < 1
    preserved = float(1 - (1 - np.median(cleaned[mask])) / depth) if mask.any() else None
    recovered = perr <= 0.02 and derr <= 0.5
    return {
        "recovered": bool(recovered),
        "injected_period_days": period,
        "recovered_period_days": result["period_days"],
        "period_error_fraction": perr,
        "injected_depth": depth,
        "recovered_depth": result["depth_fraction"],
        "depth_error_fraction": derr,
        "duration_hours": duration_hours,
        "added_noise_sigma_scatter": noise_sigma,
        "transit_preservation_attenuation": preserved,
        "matching_tolerances": {"period_fraction": 0.02, "depth_fraction": 0.5},
        "detection": result,
        "cleaned_flux": cleaned.tolist(),
        "injected_flux": injected.tolist(),
        "processing": params,
    }


def injection_grid(
    time,
    flux,
    depths=(0.0005, 0.001, 0.002, 0.004),
    periods=(3.0, 5.0),
    noise_levels=(0.0, 0.5, 1.0),
    repeats=1,
):
    rows = []
    for period in periods:
        for depth in depths:
            for noise in noise_levels:
                for seed in range(repeats):
                    try:
                        rows.append(
                            run_injection(
                                time, flux, period, 3.0, depth, noise_scale=noise, seed=seed + 31
                            )
                        )
                    except Exception as exc:
                        rows.append(
                            {
                                "recovered": False,
                                "injected_period_days": period,
                                "injected_depth": depth,
                                "added_noise_sigma_scatter": noise,
                                "error": str(exc),
                            }
                        )
    return rows
