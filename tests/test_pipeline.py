from __future__ import annotations
import numpy as np
import pytest
from transitiq.data import LightCurve
from transitiq.preprocess import detrend,transit_preservation
from transitiq.detection import search_bls
from transitiq.vetting import vet_candidate
from transitiq.experiments import simulate_transit,run_injection

def synthetic(period=3.2,depth=.01,duration=3.,seed=4):
    rng=np.random.default_rng(seed); t=np.arange(0,60,.02); phase=np.abs(((t-.7+period/2)%period)-period/2)
    y=1+.0003*np.sin(t/12)+rng.normal(0,.001,len(t)); y[phase<duration/48]-=depth
    return t,y

def test_validation_deduplicates_and_sorts():
    c=LightCurve(np.array([2,1,1,*range(3,34)],float),np.ones(34)).validate()
    assert np.all(np.diff(c.time)>0) and len(c.time)==33

def test_invalid_too_few():
    with pytest.raises(ValueError): LightCurve(np.arange(10),np.ones(10)).validate()

def test_bls_recovers_period_and_depth():
    t,y=synthetic(); c=LightCurve(t,y).validate(); clean,_,_=detrend(c,window_days=1.2)
    r=search_bls(t,clean,.5,8)
    assert abs(r["period_days"]-3.2)<.03
    assert abs(r["depth_fraction"]-.01)<.004
    assert r["duration_hours"]>0 and r["event_count"]>=10

def test_preservation_metric():
    m=np.arange(10)<4; r=transit_preservation(np.r_[np.repeat(.99,4),np.ones(6)],np.r_[np.repeat(.99,4),np.ones(6)],m)
    assert abs(r["attenuation_fraction"])<1e-8

def test_simulator():
    t=np.arange(0,15,.02); f=simulate_transit(t,3,3,.01,.2)
    assert np.min(f)<1 and np.sum(f<1)>0

def test_injection_experiment_executes():
    t,y=synthetic(); result=run_injection(t,y,3.2,3,.008,epoch=.7)
    assert result["matching_tolerances"]["period_fraction"]==.02
    assert result["period_error_fraction"]<.02

def test_vetting_returns_caveat():
    t,y=synthetic(); c=LightCurve(t,y); clean,_,_=detrend(c,1.2); r=search_bls(t,clean,.5,8)
    v=vet_candidate(t,clean,r); assert "not external confirmation" in v["caveat"]
