"""Conservative hourly per-house AC injections for later pandapower validation.

Produces INPUTS only, never simulates or claims electrical validity.
- All household placements are provisional and power series are synthetic.
- DER is modelled at an assumed transformer LV bus, not a new transformer.
- Real house-to-node conductor paths are not supplied and MUST NOT be inferred.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from run_integrated_dispatch import SOURCE_REL


def make_nodal_handoff(root, hourly, manifest, outpath):
    path=Path(outpath)
    path.parent.mkdir(parents=True,exist_ok=True)
    src=pd.read_csv(Path(root)/SOURCE_REL,parse_dates=['timestamp']).set_index('timestamp')
    houses=manifest['houses']
    stamps=hourly.index
    x=src[[f'house_{i}_kw' for i in range(1,len(houses)+1)]].loc[stamps]
    requested=x.sum(axis=1).to_numpy(float)
    served=hourly['demand_served_kw'].to_numpy(float)
    frac=np.divide(served,requested,out=np.zeros_like(served),where=requested>1e-12)
    qfac=np.sqrt(1./manifest['load_pf']**2-1.)
    frames=[]
    for i,h in enumerate(houses):
        active=x.iloc[:,i].to_numpy(float)*frac
        frames.append(pd.DataFrame(dict(timestamp_lst=stamps,scenario_id=hourly.scenario_id.iloc[0],
                    transformer_node=manifest['territory_node'],asset_id=h,role='synthetic_house_load_provisional',
                    p_mw=active/1000,q_mvar=active*qfac/1000)))
    injection=hourly['pv_ac_kw'].to_numpy(float)+hourly['battery_discharge_dc_kw'].to_numpy(float)*manifest['inverter_efficiency']
    frames.append(pd.DataFrame(dict(timestamp_lst=stamps,scenario_id=hourly.scenario_id.iloc[0],
                transformer_node=manifest['territory_node'],asset_id='EXISTING_TRANSFORMER_LV_BUS_ASSUMED',
                role='shared_pv_bess_at_existing_lv_bus',p_mw=-injection/1000,
                q_mvar=0.)))
    df=pd.concat(frames,ignore_index=True)
    pcc_p=df.groupby('timestamp_lst').p_mw.sum().to_numpy()*1000
    pcc_q=df.groupby('timestamp_lst').q_mvar.sum().to_numpy()*1000
    if not np.allclose(pcc_p,hourly.pcc_p_kw.to_numpy(),atol=1e-7):
        raise AssertionError('Handoff active PCC aggregation differs from canonical dispatch')
    if not np.allclose(pcc_q,hourly.pcc_q_kvar.to_numpy(),atol=1e-7):
        raise AssertionError('Handoff reactive PCC aggregation differs from canonical dispatch')
    df.to_csv(path,index=False,float_format='%.8f')
    return dict(handoff_path=str(path),rows=len(df),
                voltage_status='NOT_SIMULATED',line_loading_status='NOT_SIMULATED',
                exact_lv_routes='UNKNOWN',location_confidence='PROVISIONAL')
