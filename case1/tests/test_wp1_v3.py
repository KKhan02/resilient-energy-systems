from pathlib import Path
import numpy as np
import pandas as pd
from wp1_v3 import model as m
from wp1_v3.plots import frontier
ROOT=Path(__file__).resolve().parents[1]

def trial(hours=72,load_kw=1.,pv_kw=2.,modules=4,inverter=5.,pf=.98,**kwargs):
    idx=pd.date_range('2025-01-01',periods=hours,freq='h')
    d=pd.Series(np.full(hours,load_kw),index=idx)
    p=pd.Series(np.full(hours,pv_kw),index=idx)
    return m.dispatch(d,p,modules,inverter,pf=pf,**kwargs),d,p

def test_transformer_apparent_constraint():
    r,_,_=trial(load_kw=9,pv_kw=0,modules=0)
    assert (r.pcc_kva<=4.5000001).all()
    assert r.ens.sum()>0
    assert np.isclose(r.grid_import.max()**2+r.pcc_q_kvar.iloc[0]**2,4.5**2,atol=1e-6)

def test_charge_before_export_and_no_grid_charge():
    r,_,_=trial(load_kw=.4,pv_kw=4,modules=4)
    assert r.pv_charge_dc.iloc[0]>0
    assert r.grid_export.iloc[0]<1e-8
    assert (r.pv_charge_dc>=0).all()

def test_pv_dc_energy_balance_and_ac_balance():
    r,d,p=trial(load_kw=1.2,pv_kw=3,modules=4)
    used=r.pv_direct_ac/m.ETA_INV+r.pv_charge_dc+r.grid_export/m.ETA_INV+r.curtailed_dc
    assert np.allclose(used,p,atol=1e-6)
    assert np.allclose(r.pv_direct_ac + r.battery_discharge_dc*m.ETA_INV + r.grid_import,r.load_served,atol=1e-6)

def test_quote_cost_and_credit():
    r,d,p=trial(modules=4)
    x=m.score(r,d,p,4,12,5,4,.9,.98)
    assert np.isclose(x['capex_ex_vat_usd'],11974.79,atol=.001)
    assert np.isclose(x['capex_incl_19pct_vat_usd'],14250.,atol=.01)
    assert np.isclose(x['annual_total_no_credit_usd']-x['annual_total_homer_credit_usd'],x['grid_export_kwh']*.275)

def test_adaptive_history_causal():
    idx=pd.date_range('2025-01-01',periods=24*18,freq='h')
    pv=pd.Series(np.ones(len(idx)),index=idx)
    alt=pv.copy();alt.iloc[24*15:]=0.
    a=m.get_reserve(pv,'adaptive');b=m.get_reserve(alt,'adaptive')
    assert np.array_equal(a[:24*15],b[:24*15])

def test_hardware_limits():
    assert m.INVERTERS[5][0]==7.5
    assert m.INVERTERS[12][0]==18.0
    assert np.isclose(80*m.PANEL_KWP,34.8)

def test_nondominated_frontier():
    x=pd.DataFrame(dict(self_sufficiency_pct=[70,80,79,90],cost=[100,120,140,180]))
    f=frontier(x,'cost')
    assert len(f)==3
    assert 79 not in set(f.self_sufficiency_pct)

def test_legacy_independent_source_is_in_package():
    assert (ROOT/'legacy/independent_case1_original/sanrafael_case1/rule_dispatch.py').is_file()
    assert (ROOT/'legacy/independent_case1_original/sanrafael_case1/grid_check.py').is_file()

def test_g1a_high_generation_ac_dc_conservation():
    # B01/B11: local inverter generation exceeds demand that the PCC can serve
    # once reactive-power loading is enforced.
    for requested_kw, available_pv_kw in [(23.0, 25.0), (26.0, 30.0)]:
        out, demand, pv = trial(hours=1, load_kw=requested_kw,
                                pv_kw=available_pv_kw, modules=8,
                                inverter=24.0, pf=.98, cap_pu=.9)
        pv_accounted=(out.pv_direct_ac/m.ETA_INV + out.pv_charge_dc
                      +out.grid_export/m.ETA_INV+out.curtailed_dc)
        load_supplied=(out.pv_direct_ac+out.battery_discharge_dc*m.ETA_INV
                       +out.grid_import)
        assert np.allclose(pv_accounted,pv,atol=1e-6)
        assert np.allclose(load_supplied,out.load_served,atol=1e-6)
        assert (out.pcc_kva<=4.5+1e-6).all()
        assert np.allclose(
            np.hypot(out.pcc_p_kw,out.pcc_q_kvar),out.pcc_kva,atol=1e-6)
