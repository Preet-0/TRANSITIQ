from __future__ import annotations
from pathlib import Path
import pandas as pd\nimport numpy as np
import requests
KOI_URL="https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+*+from+cumulative&format=csv"
def fetch_koi_table(out="data/koi_cumulative.csv"):
    r=requests.get(KOI_URL,timeout=120); r.raise_for_status(); Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_bytes(r.content); return pd.read_csv(out)
def prepare_training_data(frame):
    # Only catalog-measured, pre-disposition physical/photometric properties; excludes verdict/leakage.
    f=frame.copy(); disposition=f["koi_disposition"].astype(str).str.upper()
    f["label"]=(disposition.isin(["CONFIRMED","CANDIDATE"])).astype(int)
    f=f[disposition.isin(["CONFIRMED","CANDIDATE","FALSE POSITIVE"])].copy()
    cols=[c for c in ["koi_period","koi_depth","koi_duration","koi_snr","koi_model_snr","koi_impact","koi_prad","koi_insol","koi_steff","koi_slogg"] if c in f]
    if "koi_period" not in cols or "koi_depth" not in cols: raise ValueError("Archive schema lacks required KOI period/depth features.")
    X=f[cols].apply(pd.to_numeric,errors="coerce").replace([float("inf"),-float("inf")],np.nan)
    return X, f.label.astype(int), f["kepid"], cols

