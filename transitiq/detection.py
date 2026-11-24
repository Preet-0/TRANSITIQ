from __future__ import annotations
import numpy as np
from astropy.timeseries import BoxLeastSquares


def search_bls(
    time, flux, min_period=0.5, max_period=None, durations_hours=(1, 2, 3, 4, 6, 8, 10, 12)
):
    t, y = np.asarray(time, float), np.asarray(flux, float)
    if len(t) < 30 or np.ptp(t) < min_period * 2:
        raise ValueError("At least two cycles and 30 valid samples are needed for BLS.")
    yerr = np.full(len(y), max(np.std(y - 1), 1e-5))
    max_period = max_period or min(np.ptp(t) / 2, 30.0)
    if max_period <= min_period:
        raise ValueError("Maximum period must exceed minimum period.")
    durations = np.array(durations_hours) / 24
    durations = durations[durations < min_period * 0.2]
    if not len(durations):
        durations = np.array([min_period * 0.05])
    model = BoxLeastSquares(t, y, dy=yerr)
    result = model.autopower(
        durations,
        minimum_period=min_period,
        maximum_period=max_period,
        frequency_factor=1.0,
        oversample=8,
    )
    i = int(np.nanargmax(result.power))
    period, epoch, duration, depth, power = (
        float(result.period[i]),
        float(result.transit_time[i]),
        float(result.duration[i]),
        float(result.depth[i]),
        float(result.power[i]),
    )
    phase = ((t - epoch + period / 2) % period) - period / 2
    in_tr = np.abs(phase) < duration / 2
    n_events = max(
        0, int(np.floor((t.max() - epoch) / period) - np.ceil((t.min() - epoch) / period) + 1)
    )
    scatter = float(1.4826 * np.median(np.abs(y - np.median(y))))
    depth_sigma = float(depth * max(in_tr.sum(), 1) ** 0.5 / max(scatter, 1e-12))
    return {
        "period_days": period,
        "epoch_days": epoch,
        "duration_hours": duration * 24,
        "depth_fraction": depth,
        "depth_ppm": depth * 1e6,
        "bls_power": power,
        "snr_approx": depth_sigma,
        "event_count": n_events,
        "periodogram": {
            "period": np.asarray(result.period).tolist(),
            "power": np.asarray(result.power).tolist(),
        },
        "fold_phase": phase.tolist(),
        "fold_flux": y.tolist(),
    }


def event_depths(time, flux, period, epoch, duration_hours):
    t, y = np.asarray(time), np.asarray(flux)
    dur = duration_hours / 24
    cycle = np.round((t - epoch) / period).astype(int)
    depths = []
    for k in np.unique(cycle):
        sel = (cycle == k) & (np.abs(t - (epoch + k * period)) < dur / 2)
        if sel.sum() >= 2:
            depths.append(float(1 - np.median(y[sel])))
    return np.asarray(depths)
