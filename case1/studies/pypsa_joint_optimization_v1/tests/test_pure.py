"""Pure model validation only. True PyPSA integration requires installed PyPSA+HiGHS."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model import (Settings,crf,annualized_rate,discounted_replacement_factor,
                   transformer_active_bound_kw,PV_USD_KWP,ETA_INV)
from run import monthly_table,PROFILE_ASSIGNMENTS

def test_equipment_cost_and_replacement():
    assert .07 < crf() < .09
    assert discounted_replacement_factor(15)>1
    assert annualized_rate(PV_USD_KWP,25)>0

def test_distinct_H01_H02_profiles():
    assert PROFILE_ASSIGNMENTS['eight_H01'] != PROFILE_ASSIGNMENTS['eight_H02']
    assert set(PROFILE_ASSIGNMENTS['nine'])==set(PROFILE_ASSIGNMENTS['eight_H01']+PROFILE_ASSIGNMENTS['eight_H02'])

def test_reactive_pcc_envelope():
    p,ok=transformer_active_bound_kw([0,2,3],5,.9,.98)
    assert ok
    assert p[0]==pytest.approx(4.5)
    assert np.all(p[1:]<4.5)
    _,ok=transformer_active_bound_kw([30],5,.9,.98)
    assert not ok

def test_set_config_validation():
    with pytest.raises(ValueError):Settings(objective='energy')
    with pytest.raises(ValueError):Settings(export_policy='invented')
    assert Settings(capex_budget_usd=10000,objective='energy').objective=='energy'

def test_monthly_import_definition():
    idx=pd.date_range('2025-01-01',periods=48,freq='h')
    t=pd.DataFrame(index=idx)
    t['demand_kw']=1.;t['pv_dc_generated_kw']=.5;t['pv_dc_available_kw']=.6
    t['battery_charge_dc_kw']=0.;t['battery_discharge_dc_kw']=0.
    t['grid_import_kw']=.25;t['grid_export_kw']=0.
    t['curtailed_pv_dc_kw']=.1;t['unserved_kw']=0.
    t['ghi_wh_m2']=100.
    m=monthly_table(t)
    assert m.self_sufficiency_pct.iloc[0]==pytest.approx(75)
    assert m.grid_import_kwh.iloc[0]==pytest.approx(12)

def test_normalized_reference_loads_if_available():
    f=Path('/mnt/data/_tmp_regenerated_v18_hourly.csv')
    if not f.exists():pytest.skip('Private fixture not mounted')
    df=pd.read_csv(f,usecols=[f'house_{i}_kw' for i in range(1,21)])
    assert np.allclose(df.sum(axis=0),1898.,atol=1e-6)
    assert not np.allclose(df.house_8_kw,df.house_9_kw)

@pytest.mark.skipif(__import__('importlib').util.find_spec('pypsa') is None,reason='PyPSA solver dependencies not in sandbox')
def test_pypsa_short_multivariable_solve():
    from model import make_network,solve,extract
    idx=pd.date_range('2025-01-01',periods=48,freq='h')
    load=pd.Series(.1,index=idx)
    profile=pd.Series(np.where((idx.hour>=7)&(idx.hour<=17),.6,0.),index=idx)
    st=Settings(max_panels=20,max_battery_modules=4,max_inverter_kva=10,discrete=True)
    n=solve(load,profile,st)
    assert float(n.generators.at['PV_DC','p_nom_opt'])>=0
    d=extract(n,st,load)
    assert len(d)==48 and d.unserved_kw.sum()==0
