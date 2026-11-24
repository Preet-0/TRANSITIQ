from __future__ import annotations
import numpy as np
from scipy.ndimage import median_filter
from .data import LightCurve


def detrend(curve: LightCurve, window_days: float = 1.5, sigma_clip: float = 6.0):
    """Conservative transit-aware median baseline; low excursions are masked and interpolated."""
    c = curve.validate()
    t, f = c.time.copy(), c.flux.copy()
    cadence = np.median(np.diff(t))
    width = max(11, int(round(window_days / cadence)))
    if width % 2 == 0:
        width += 1
    width = min(width, len(f) - (1 - len(f) % 2))
    if width < 3:
        raise ValueError("Not enough points for detrending.")
    # Iteratively mask negative excursions so transit points do not pull the baseline down.
    working = f.copy()
    mask = np.zeros(len(f), dtype=bool)
    for _ in range(3):
        baseline = median_filter(working, size=width, mode="nearest")
        resid = f / np.maximum(baseline, np.finfo(float).eps) - 1.0
        scatter = 1.4826 * np.nanmedian(np.abs(resid - np.nanmedian(resid)))
        newly = resid < -max(sigma_clip * scatter, 0.00005)
        mask |= newly
        working = f.copy()
        if mask.any():
            working[mask] = np.interp(t[mask], t[~mask], f[~mask])
    baseline = median_filter(working, size=width, mode="nearest")
    norm = f / baseline
    return (
        norm,
        baseline,
        {
            "window_days": float(window_days),
            "window_points": int(width),
            "masked_low_points": int(mask.sum()),
            "robust_scatter": float(1.4826 * np.median(np.abs(norm - 1 - np.median(norm - 1)))),
        },
    )


def transit_preservation(injected_flux, cleaned_flux, transit_mask):
    m = np.asarray(transit_mask, bool)
    if m.sum() < 2:
        return {"attenuation_fraction": None, "injected_depth": None, "recovered_depth": None}
    raw, clean = np.asarray(injected_flux), np.asarray(cleaned_flux)
    raw_depth = float(1 - np.median(raw[m]))
    clean_depth = float(1 - np.median(clean[m]))
    return {
        "injected_depth": raw_depth,
        "recovered_depth": clean_depth,
        "attenuation_fraction": float(1 - clean_depth / raw_depth) if raw_depth > 0 else None,
    }
