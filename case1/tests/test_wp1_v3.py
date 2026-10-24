import pytest
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
    for requested_kw, available_pv_kw in [(23.0, 25.0), (26.0, 30.0),
                                          (30.0, 20.0)]:
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
        # Stored-energy recurrence also checks refunded battery discharge.
        usable_capacity=8*m.USABLE_KWH_MODULE
        initial_stored=usable_capacity*(.55-.1)/.9
        expected_stored=(initial_stored
                         +float(out.pv_charge_dc.iloc[0])*m.ETA_BAT
                         -float(out.battery_discharge_dc.iloc[0])/m.ETA_BAT)
        assert np.isclose(float(out.soc_usable_kwh.iloc[0]),
                          expected_stored,atol=1e-6)
        assert np.allclose(
            np.hypot(out.pcc_p_kw,out.pcc_q_kvar),out.pcc_kva,atol=1e-6)

def test_g1b_midnight_uses_real_window_hour():
    # Window begins at 18:00, so index position 5 (not 23) is 23:00.
    idx=pd.date_range('2025-06-15 18:00',periods=8,freq='h')
    demand=pd.Series(10.0,index=idx)
    pv=pd.Series(0.0,index=idx)
    result=m.dispatch(demand,pv,modules=0,inverter_kva=5.0,pf=1.0,
                      policy='adaptive_lm',reserve_override=np.full(8,.1))
    # At 23:00, all outstanding flexible requests become due.
    assert np.isclose(result.deferred_backlog_kwh.iloc[4],7.5)
    assert np.isclose(result.deferred_backlog_kwh.iloc[5],0.0)
    # Overdue demand is not made to vanish: unserved requests count as ENS.
    assert np.isclose(result.ens.iloc[5],13.0)
    # One-hour resolution: demand is either served, unserved, or deferred.
    assert np.isclose(demand.sum(),result.load_served.sum()
                      +result.ens.sum()+result.deferred_backlog_kwh.iloc[-1])


def test_g1b_import_projection_counts_deferred_backlog():
    # New demand alone is below the trigger; adding backlog exceeds it.
    # Controller must not silently recover backlog without evaluating it.
    idx=pd.date_range('2025-06-15 10:00',periods=2,freq='h')
    demand=pd.Series([6.0,2.7],index=idx)
    pv=pd.Series([0.0,0.0],index=idx)
    result=m.dispatch(demand,pv,modules=0,inverter_kva=5.0,pf=1.0,
                      policy='adaptive_lm',reserve_override=np.full(2,.1))
    assert np.isclose(result.deferred_backlog_kwh.iloc[0],0.9)
    assert np.isclose(result.deferred_backlog_kwh.iloc[1],1.305)
    assert np.isclose(demand.sum(),result.load_served.sum()
                      +result.ens.sum()+result.deferred_backlog_kwh.iloc[-1])

def test_g2_load_management_index_error_is_actionable():
    # Guard must run before pandas.resample, including with an adaptive reserve.
    index=pd.RangeIndex(3)
    demand=pd.Series([1.0]*3,index=index)
    pv=pd.Series([0.0]*3,index=index)
    with pytest.raises(ValueError,match="adaptive_lm requires a DatetimeIndex"):
        m.dispatch(demand,pv,modules=4,inverter_kva=5.,
                   policy="adaptive_lm")


def test_g2_solar_selection_is_explicit(monkeypatch):
    import run_case1_v3 as runner
    calls=[]
    def fail_pvlib(frame):
        calls.append("pvlib")
        raise ImportError("pvlib intentionally unavailable")
    def fake_approx(frame):
        calls.append("approximate")
        return "approx",{"method":"APPROX"}
    monkeypatch.setattr(runner.reference_v2,"pvlib_nasa_pv",fail_pvlib)
    monkeypatch.setattr(runner.reference_v2,"approximate_nasa_pv",fake_approx)

    with pytest.raises(RuntimeError,match="pvlib"):
        runner.select_solar_profile(None,solar_method="pvlib")
    assert calls==["pvlib"], "Strict pvlib must never fall back"
    result,metadata=runner.select_solar_profile(None,solar_method="approximate")
    assert result=="approx" and metadata["method"]=="APPROX"
    assert calls==["pvlib","approximate"]

def test_g2_battery_power_default_uses_hardware_limit():
    index=pd.date_range("2025-01-01",periods=1,freq="h")
    load=pd.Series([0.0],index=index)
    pv=pd.Series([40.0],index=index)
    hardware=m.dispatch(load,pv,modules=8,inverter_kva=24.0)
    explicit=m.dispatch(load,pv,modules=8,inverter_kva=24.0,
                        charge_discharge_kw=5.0)
    assert hardware.pv_charge_dc.iloc[0]>5.0
    assert np.isclose(explicit.pv_charge_dc.iloc[0],5.0)


def test_g2_frontier_is_robust_to_duplicate_index_labels():
    from wp1_v3.plots import frontier
    df=pd.DataFrame({"self_sufficiency_pct":[80,70,90],
                     "annual_total_no_credit_usd":[100,110,200]},
                     index=[0,0,1])
    found=frontier(df,"annual_total_no_credit_usd")
    assert len(found)==2
    assert set(found.self_sufficiency_pct)=={80,90}


def test_g2_single_feasibility_definition():
    from wp1_v3.plots import eligible_designs
    df=pd.DataFrame({
        "grid_ens_kwh":[0.0,1e-5,0.0],
        "max_trafo_kva":[4.5,4.0,4.7],
        "transformer_allow_kva":[4.5,4.5,4.5]})
    assert list(eligible_designs(df).index)==[0]


def test_g2_two_self_sufficiency_definitions_are_named():
    output,d,pv=trial(load_kw=9.0,pv_kw=0.0,modules=0)
    result=m.score(output,d,pv,0,12,5,4,.9,.98)
    assert "self_sufficiency_of_served_pct" in result
    assert "one_minus_import_fraction_of_demand_pct" in result
    assert np.isclose(result["self_sufficiency_of_served_pct"],
                      result["self_sufficiency_pct"])
    assert result["one_minus_import_fraction_of_demand_pct"] > result["self_sufficiency_pct"]
