from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd


@dataclass
class LightCurve:
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray | None = None
    quality: np.ndarray | None = None
    provenance: dict[str, Any] | None = None

    def validate(self) -> "LightCurve":
        t, f = np.asarray(self.time, float), np.asarray(self.flux, float)
        if t.ndim != 1 or f.ndim != 1 or len(t) != len(f) or len(t) < 30:
            raise ValueError("Time and flux must be matching 1D arrays with at least 30 rows.")
        e = np.full(len(t), np.nan) if self.flux_err is None else np.asarray(self.flux_err, float)
        q = np.zeros(len(t), dtype=int) if self.quality is None else np.asarray(self.quality)
        if e.shape != t.shape or q.shape != t.shape:
            raise ValueError("Uncertainty and quality columns must match time and flux lengths.")
        good = np.isfinite(t) & np.isfinite(f) & (f > 0) & (~np.isfinite(e) | (e >= 0))
        # Missing uncertainties are allowed; retain those rows.
        if self.flux_err is None:
            good = np.isfinite(t) & np.isfinite(f) & (f > 0)
        if self.quality is not None:
            good &= q == 0
        t, f, e = t[good], f[good], e[good]
        order = np.argsort(t, kind="stable")
        t, f, e = t[order], f[order], e[order]
        unique = np.r_[True, np.diff(t) > 0]
        t, f, e = t[unique], f[unique], e[unique]
        if len(t) < 30:
            raise ValueError(
                "Fewer than 30 valid, unique observations remain after quality filtering."
            )
        self.time, self.flux = t, f
        self.flux_err = e if self.flux_err is not None else None
        self.quality = None
        return self

    @classmethod
    def from_frame(
        cls,
        frame: pd.DataFrame,
        time_col: str,
        flux_col: str,
        error_col: str | None = None,
        quality_col: str | None = None,
        provenance: dict | None = None,
    ) -> "LightCurve":
        return cls(
            pd.to_numeric(frame[time_col], errors="coerce").to_numpy(),
            pd.to_numeric(frame[flux_col], errors="coerce").to_numpy(),
            pd.to_numeric(frame[error_col], errors="coerce").to_numpy() if error_col else None,
            pd.to_numeric(frame[quality_col], errors="coerce").fillna(1).to_numpy()
            if quality_col
            else None,
            provenance or {},
        ).validate()
