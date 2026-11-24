from __future__ import annotations
import numpy as np
from .preprocess import detrend
from .detection import search_bls

def simulate_transit(time, period, duration_hours, depth, epoch):
    t=np.asarray(time,float); phase=np.abs(((t-epoch+period/2)%period)-period/2)
    return np.where(phase<duration_hours/48,1-depth,1.0)

def run_injection(time, flux, period=5., duration_hours=3., depth=.002, epoch=None, noise_scale=1., seed=123):
    t,y=np.asarray(time,float),np.asarray(flux,float)
    epoch=float(epoch if epoch is not None else t.min()+.37*period)
    transit=simulate_transit(t,period,duration_hours,depth,epoch)
    rng=np.random.default_rng(seed); scatter=1.4826*np.median(np.abs(y-np.median(y)))
    injected=y*transit+rng.normal(0,scatter*(noise_scale-1),len(y))
    from .data import LightCurve
    cleaned,base,params=detrend(LightCurve(t,injected))
    result=search_bls(t,cleaned,min_period=max(.3,period*.5),max_period=min(np.ptp(t)/2,period*1.5))
    perr=abs(result["period_days"]-period)/period
    derr=abs(result["depth_fraction"]-depth)/depth
    mask=transit<1
    preserved=float(1-(1-np.median(cleaned[mask]))/depth) if mask.any() else None
    recovered=perr<=.02 and derr<=.5
    return {"recovered":bool(recovered),"injected_period_days":period,"recovered_period_days":result["period_days"],
            "period_error_fraction":perr,"injected_depth":depth,"recovered_depth":result["depth_fraction"],
            "depth_error_fraction":derr,"duration_hours":duration_hours,"transit_preservation_attenuation":preserved,
            "matching_tolerances":{"period_fraction":.02,"depth_fraction":.5},"detection":result,
            "cleaned_flux":cleaned.tolist(),"injected_flux":injected.tolist(),"processing":params}

def injection_grid(time,flux,depths=(.0005,.001,.002,.004),periods=(3.,5.),repeats=2):
    rows=[]
    for p in periods:
        for d in depths:
            for seed in range(repeats):
                try: rows.append(run_injection(time,flux,p,3.,d,seed=seed+31))
                except Exception as exc: rows.append({"recovered":False,"injected_period_days":p,"injected_depth":d,"error":str(exc)})
    return rows
