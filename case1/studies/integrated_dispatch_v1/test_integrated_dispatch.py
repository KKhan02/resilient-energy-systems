"""Adapter invariants. Synthetic toy arrays never constitute Case 1 simulation results."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import pytest
from run_integrated_dispatch import household_selection, verify_dispatch, dispatch_case, YEAR_INDEX
from report_timeseries import aggregates,load

class FakeCoreConstants:
    ETA_INV=.95
    USABLE_KWH_MODULE=4.325


def toy_hourly():
    out=pd.DataFrame(index=YEAR_INDEX)
    out.index.name='timestamp_lst'
    out['demand_requested_kw']=1.25
    out['demand_served_kw']=1.25
    out['ens_kw']=0.
    out['pv_dc_available_kw']=0.
    out['ghi_wh_m2']=0.
    out['pv_ac_kw']=0.
    out['battery_charge_dc_kw']=0.
    out['battery_discharge_dc_kw']=0.
    out['soc_usable_kwh']=0.
    out['grid_import_kw']=1.25
    out['grid_export_kw']=0.
    out['curtailment_kw']=0.
    out['pcc_p_kw']=1.25
    out['pcc_q_kvar']=0.
    out['pcc_s_kva']=1.25
    return out


def test_household_territories():
    assert len(household_selection('931076',()))==7
    assert len(household_selection('931076',('H01',)))==8
    assert len(household_selection('931076',('H02',)))==8
    assert len(household_selection('931076',('H01','H02')))==9
    assert len(household_selection('923494',()))==12
    with pytest.raises(ValueError):household_selection('923494',('H01',))


def test_conservation_and_monthly():
    hourly=toy_hourly()
    qa=verify_dispatch(hourly,FakeCoreConstants(),modules=0,cap_pu=.9)
    assert qa['ens_kwh']==0
    monthly=aggregates(hourly,'MS')
    assert len(monthly)==12
    assert np.isclose(monthly.grid_import_kwh.sum(),8760*1.25)
    assert (monthly.self_sufficiency_pct==0).all()
    assert (monthly.demand_adequacy_pct==100).all()
    assert not monthly.fully_grid_independent_and_served.any()


def test_detects_physics_errors():
    x=toy_hourly()
    x.loc[x.index[50],'pcc_s_kva']=5.1
    with pytest.raises(AssertionError):verify_dispatch(x,FakeCoreConstants(),modules=0,cap_pu=.9)
    x=toy_hourly()
    x.loc[x.index[50],'grid_import_kw']=0.5
    with pytest.raises(AssertionError):verify_dispatch(x,FakeCoreConstants(),modules=0,cap_pu=.9)


def test_reporting_input_and_import_fraction(tmp_path):
    x=toy_hourly()
    x.to_csv(tmp_path/'test.csv',index_label='timestamp_lst')
    df=load(tmp_path/'test.csv')
    assert len(df)==8760
    x.iloc[2,x.columns.get_loc('ens_kw')]=0.1
    x.to_csv(tmp_path/'bad.csv',index_label='timestamp_lst')
    with pytest.raises(ValueError):load(tmp_path/'bad.csv')


def test_never_claim_zero_export_posthoc():
    with pytest.raises(ValueError,match='zero-export'):
        dispatch_case(Path('/no-such-repo'),export_mode='zero-export')

class NoDerToyModel:
    """Test double for the wiring only, NEVER a production dispatch engine."""
    ETA_INV=.95
    PANEL_KWP=.435
    PRICE_IMPORT=.29
    USABLE_KWH_MODULE=4.325
    INVERTERS={5.:(7.5,120),10.:(15.,220)}
    @staticmethod
    def dispatch_cyclic(load,pv,modules,inverter_kva,**kw):
        out=pd.DataFrame(index=load.index)
        for c in ['pv_direct_ac','pv_charge_dc','battery_discharge_dc','grid_export','curtailed_dc','soc_usable_kwh','ens','pcc_q_kvar']:
            out[c]=0.
        out['grid_import']=load
        out['load_served']=load
        out['pcc_p_kw']=load
        out['pcc_kva']=load
        return out,dict(initial_soc_pu=.55,initial_stored_kwh=0.,end_stored_kwh=0.,
                        soc_boundary_drift_kwh=0.,soc_boundary_closed=True)
    @staticmethod
    def score(frame,load,pv,modules,panels,inv,houses,cap_pu,pf,initial_soc_pu=.55):
        imports=float(frame.grid_import.sum());demand=float(load.sum())
        return dict(demand_kwh=demand,grid_import_kwh=imports,grid_export_kwh=0.,grid_ens_kwh=0.,
                    one_minus_import_fraction_of_demand_pct=0.,locally_supplied_fraction_of_demand_pct=0.,
                    annual_total_no_credit_usd=imports*.29,capex_ex_vat_usd=0.,max_trafo_kva=float(load.max()))


def test_complete_adapter_toy_no_der():
    from run_integrated_dispatch import dispatch_case
    idx=YEAR_INDEX
    raw=pd.DataFrame(index=idx)
    for i in range(1,13): raw[f'house_{i}_kw']=.13
    raw['nasa_pv_dc_kw']=0.
    raw['poa_global_wm2']=0.
    nasa=pd.DataFrame({'ALLSKY_SFC_SW_DWN':np.zeros(len(idx))},index=idx)
    hourly,m=dispatch_case(Path('/no-such-repo'),territory='931076',panels=0,modules=0,
        battery_power_kw=0.,inverter_kva=5.,source_override=(raw,nasa),model_override=NoDerToyModel())
    assert len(hourly)==8760
    assert abs(hourly.demand_requested_kw.sum()-7*.13*8760)<1e-6
    assert m['qa']['ens_kwh']==0
    assert m['network_validation_status']=='NOT_SIMULATED'
