from __future__ import annotations
import json
from pathlib import Path
import lightkurve as lk

def search_observations(target, mission="Kepler"):
    res=lk.search_lightcurve(target, mission=mission)
    rows=[]
    for i,row in enumerate(res.table):
        rows.append({"index":i,"mission":str(row["mission"]),"author":str(row["author"]),
                     "exposure":str(row["exptime"]),"sector":str(row["sector"]),"quarter":str(row["quarter"]),
                     "product":str(row["productFilename"]),"target":str(row["target_name"])})
    return res,rows

def download_observation(results,index):
    lc=results[int(index)].download()
    if lc is None: raise RuntimeError("MAST returned no downloadable light curve for the selected product.")
    time=lc.time.value; flux=lc.flux.value
    err=lc.flux_err.value if getattr(lc,"flux_err",None) is not None else None
    quality=lc.quality
    return time,flux,err,quality
