from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def save_analysis(data,outdir="outputs"):
    path=Path(outdir); path.mkdir(exist_ok=True,parents=True)
    safe="".join(x if x.isalnum() or x in "-_" else "_" for x in str(data.get("target","target")))[:60]
    (path/f"{safe}_analysis.json").write_text(json.dumps(data,indent=2,default=str),encoding="utf-8")
    pd.DataFrame(data.get("candidates",[])).to_csv(path/f"{safe}_candidates.csv",index=False)
    return path/f"{safe}_analysis.json"

def make_html_report(data):
    import html
    target=html.escape(str(data.get("target","Unknown")))
    rows="".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k,v in data.get("detection",{}).items() if k!="periodogram")
    return f"<!doctype html><meta charset='utf-8'><title>TRANSITIQ report</title><h1>TRANSITIQ Candidate Investigation</h1><p>Target: {target}</p><p>Unconfirmed candidate analysis; not a discovery claim.</p><table>{rows}</table><pre>{html.escape(json.dumps(data.get('vetting',{}),indent=2))}</pre>"
