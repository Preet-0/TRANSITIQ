from __future__ import annotations
import numpy as np
from .detection import event_depths


def vet_candidate(time, flux, detection):
    period, epoch, dur = (detection[k] for k in ("period_days", "epoch_days", "duration_hours"))
    depths = event_depths(time, flux, period, epoch, dur)
    odd, even = depths[::2], depths[1::2]
    odd_depth = float(np.median(odd)) if len(odd) else None
    even_depth = float(np.median(even)) if len(even) else None
    oe = (
        None
        if odd_depth is None or even_depth is None
        else abs(odd_depth - even_depth) / max(abs(np.median(depths)), 1e-10)
    )
    # Secondary eclipse proxy at phase 0.5; diagnostic only, not a verdict.
    t, y = np.asarray(time), np.asarray(flux)
    phase = ((t - epoch) / period) % 1
    secondary = np.abs(((phase - 0.5 + 0.5) % 1) - 0.5) < (dur / period / 2)
    sec_depth = float(1 - np.median(y[secondary])) if secondary.sum() >= 3 else None
    ratio = (
        abs(sec_depth) / max(abs(float(detection["depth_fraction"])), 1e-10)
        if sec_depth is not None
        else None
    )
    scatter = float(1.4826 * np.median(np.abs(y - np.median(y))))
    sn = float(detection.get("snr_approx", 0))
    flags = {
        "odd_even_depth_fractional_difference": oe,
        "secondary_to_primary_depth_ratio": ratio,
        "weak_signal": sn < 7,
        "few_events": int(detection.get("event_count", 0)) < 3,
        "short_event_train": len(depths) < 3,
        "high_stellar_scatter": scatter > max(float(detection["depth_fraction"]) * 2, 0.005),
    }
    reasons = []
    if oe is not None and oe > 0.5:
        reasons.append("Odd/even transit depths differ substantially")
    if ratio is not None and ratio > 0.3:
        reasons.append("Possible secondary eclipse")
    if sn < 7:
        reasons.append("Low approximate transit S/N")
    if len(depths) < 3:
        reasons.append("Fewer than three individual events measured")
    score = sum(
        [oe is not None and oe > 0.5, ratio is not None and ratio > 0.3, sn < 7, len(depths) < 3]
    )
    label = (
        "Likely false positive"
        if score >= 2
        else ("Uncertain" if score or sn < 10 else "Planet-like")
    )
    return {
        "label": label,
        "flags": flags,
        "reasons": reasons,
        "event_depths": depths.tolist(),
        "caveat": "Photometric triage only; this is not external confirmation.",
    }
