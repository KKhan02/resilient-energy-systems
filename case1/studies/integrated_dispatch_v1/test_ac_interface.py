import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import pytest
from validate_ac_snapshots import selected_timestamps


def test_event_selector_deterministic():
    idx=pd.date_range('2025-01-01',periods=8760,freq='h')
    d=pd.DataFrame({'timestamp_lst':idx,
        'demand_requested_kw':1+np.arange(8760)/8760,
        'pv_ac_kw':np.zeros(8760),
        'grid_import_kw':np.ones(8760),
        'grid_export_kw':np.zeros(8760),
        'pcc_s_kva':np.ones(8760),
        'soc_usable_kwh':np.zeros(8760)})
    d.loc[150,'pv_ac_kw']=5
    ids=selected_timestamps(d)
    assert 0 in ids and 8759 in ids and 150 in ids
    assert len(ids)==len(set(ids)) and len(ids)<35


def test_event_selector_fails_on_empty():
    with pytest.raises(ValueError):selected_timestamps(pd.DataFrame())


def test_handoff_p_and_q_conservation(tmp_path):
    from pandapower_handoff import make_nodal_handoff
    from run_integrated_dispatch import SOURCE_REL
    base=tmp_path/SOURCE_REL
    base.parent.mkdir(parents=True)
    ix=pd.date_range('2025-01-01',periods=24,freq='h')
    source=pd.DataFrame({'timestamp':ix,**{f'house_{i}_kw':np.full(24,.13) for i in range(1,8)}})
    source.to_csv(base,index=False)
    demand=.13*7;injection=.2+.1*.95
    qfac=np.sqrt(1/.98**2-1)
    h=pd.DataFrame({'scenario_id':['toy']*24,
        'demand_served_kw':[demand]*24,
        'pv_ac_kw':[.2]*24,
        'battery_discharge_dc_kw':[.1]*24,
        'pcc_p_kw':[demand-injection]*24,
        'pcc_q_kvar':[demand*qfac]*24},index=ix)
    meta={'houses':['H03','H06','H26','H27','H28','H34','H35'],
          'load_pf':.98,'territory_node':'931076','inverter_efficiency':.95}
    r=make_nodal_handoff(tmp_path,h,meta,tmp_path/'nodal.csv')
    assert r['rows']==8*24
    d=pd.read_csv(tmp_path/'nodal.csv')
    assert np.isclose(d.p_mw.sum()*1000,24*(demand-injection),atol=1e-4)
