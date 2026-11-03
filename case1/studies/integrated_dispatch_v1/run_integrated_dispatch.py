#!/usr/bin/env python3
"""Reproducible Case 1 hourly dispatch bridge to EXISTING canonical wp1_v3.model.

Does NOT reimplement PV/BESS dispatch, network AC power flow, or claim utility validation.
Run only from a checkout of resilient-energy-systems containing the existing inputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE_REL = Path('Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv')
NASA_REL = Path('case1/data/NASA_POWER_SanRafael_hourly_2025.csv')
MODEL_REL = Path('case1/wp1_v3/model.py')
HOUSES_REL = Path('case1/studies/community_georef/field_review_2026_10_27/houses_field_review.csv')
TERRITORIES = {
    '931076': ['H03','H06','H26','H27','H28','H34','H35'],
    '923494': ['H11','H13','H16','H17','H18','H19','H20','H21','H22','H23','H24','H25'],
}
ARCHIVED_RATINGS = {'931076': 5.0, '923848': 5.0}
YEAR_INDEX = pd.date_range('2025-01-01 00:00', periods=8760, freq='h')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locate_repo(path=None):
    if path is not None:
        root = Path(path).resolve()
        if not (root/MODEL_REL).is_file():
            raise FileNotFoundError(f'Not the expected repository root: {root}')
        return root
    for parent in Path(__file__).resolve().parents:
        if (parent/MODEL_REL).is_file():
            return parent
    raise FileNotFoundError('Provide --repo-root pointing at the full GitLab checkout')


def source_data(root):
    source = root/SOURCE_REL
    raw = pd.read_csv(source, parse_dates=['timestamp']).set_index('timestamp')
    if not raw.index.equals(YEAR_INDEX):
        raise ValueError('Original v5 NASA/PyPSA source must contain all 8760 contiguous 2025 LST hours')
    needed = ['nasa_pv_dc_kw']+[f'house_{i}_kw' for i in range(1, 13)]
    missing = set(needed)-set(raw.columns)
    if missing:
        raise ValueError('Source missing '+', '.join(sorted(missing)))
    for key in needed:
        if not np.isfinite(raw[key].to_numpy(float)).all() or (raw[key]<-1e-10).any():
            raise ValueError(f'Invalid input {key}')
    if not np.isclose(raw['house_1_kw'].sum(), 1898, atol=0.25):
        raise ValueError('Unexpected stochastic load energy. Check original reference source.')
    nasa = pd.read_csv(root/NASA_REL, parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if not nasa.index.equals(YEAR_INDEX):
        raise ValueError('NASA 2025 hourly LST timestamps do not match canonical annual source')
    if not np.allclose(raw['ALLSKY_SFC_SW_DWN'].to_numpy(float), nasa['ALLSKY_SFC_SW_DWN'].to_numpy(float), atol=0.01, rtol=0):
        raise ValueError('Solar irradiation discrepancy between weather sources')
    return raw, nasa


def household_selection(territory, include):
    if territory not in TERRITORIES:
        raise ValueError('Unknown territory. Supported initial cases: 931076 and 923494')
    extra = sorted(set(include))
    if any(x not in ('H01','H02') for x in extra):
        raise ValueError('Only H01/H02 alternative-to-94022 sensitivities supported here')
    if extra and territory != '931076':
        raise ValueError('H01/H02 are only tested as conditional additions to 931076')
    houses = list(TERRITORIES[territory])+extra
    if len(set(houses)) != len(houses):
        raise ValueError('Duplicate house id')
    return houses


def dispatch_case(root, territory='931076', include=(), panels=24, modules=4,
                  battery_power_kw=5., inverter_kva=10., pf=.98, cap_pu=.9,
                  soc_mode='cyclic', initial_soc=.55, export_mode='permitted',
                  source_override=None, model_override=None):
    """Returns hourly frame + audit manifest. No actual feeder/network claim."""
    if export_mode != 'permitted':
        raise ValueError('Canonical core currently has no zero-export dispatch interface; reject rather than post-hoc clipping.')
    if panels<0 or panels!=int(panels) or modules<0 or modules!=int(modules):
        raise ValueError('Invalid hardware module count')
    if not 0<cap_pu<=1. or not 0<pf<=1.:
        raise ValueError('Invalid PF/transformer loading assumption')
    if not 0<=battery_power_kw or (modules==0 and battery_power_kw!=0):
        raise ValueError('Battery power must be zero when battery absent')
    houses=household_selection(territory,include)
    raw,nasa=source_override if source_override is not None else source_data(root)
    if model_override is not None:
        m=model_override
    else:
        sys.path.insert(0,str(root))
        from case1.wp1_v3 import model as m
    if inverter_kva not in m.INVERTERS:
        raise ValueError('Inverter must match canonical model.INVERTERS')
    if panels*m.PANEL_KWP > m.INVERTERS[inverter_kva][0]+1e-9:
        raise ValueError('PV DC exceeds canonical inverter maximum PV input')
    physical_battery_kw=min(48*m.INVERTERS[inverter_kva][1]/1000,4.8*modules)
    if battery_power_kw>physical_battery_kw+1e-9:
        raise ValueError(f'Battery power {battery_power_kw} kW exceeds canonical hardware limit {physical_battery_kw:.3f} kW')
    # Ordinal synthetic references, held constant while expanding 7->8->9 homes.
    load=raw[[f'house_{i}_kw' for i in range(1,len(houses)+1)]].sum(axis=1)
    pv=raw['nasa_pv_dc_kw']*(panels*m.PANEL_KWP/5.22)
    kwargs=dict(cap_pu=cap_pu,pf=pf,policy='conventional',charge_discharge_kw=battery_power_kw)
    if soc_mode=='cyclic':
        frame, boundary=m.dispatch_cyclic(load,pv,modules,inverter_kva,**kwargs)
    elif soc_mode=='fixed':
        frame=m.dispatch(load,pv,modules,inverter_kva,initial_soc_pu=initial_soc,**kwargs)
        boundary=m.soc_boundary_diagnostics(frame,modules,initial_soc)
        boundary['method']='fixed_initial_soc'
    else:
        raise ValueError('soc_mode must be cyclic or fixed')
    # Core explicitly accounts for DC-coupled PV generation, charging and export.
    solar_ac=frame['pv_direct_ac']+frame['grid_export']
    out=pd.DataFrame(index=YEAR_INDEX)
    out.index.name='timestamp_lst'
    out['scenario_id']=f'{territory}_{len(houses)}h_{panels}p_{modules}b_{battery_power_kw:g}kW_{inverter_kva:g}kVA'
    out['transformer_node']=territory
    out['house_ids']='|'.join(houses)
    out['demand_requested_kw']=load.to_numpy(float)
    out['demand_served_kw']=frame['load_served'].to_numpy(float)
    out['ens_kw']=frame['ens'].to_numpy(float)
    out['ghi_wh_m2']=nasa['ALLSKY_SFC_SW_DWN'].to_numpy(float)
    out['poa_wh_m2_if_computed']=raw['poa_global_wm2'].to_numpy(float) if 'poa_global_wm2' in raw else np.nan
    out['pv_dc_available_kw']=pv.to_numpy(float)
    out['pv_ac_kw']=solar_ac.to_numpy(float)
    out['battery_charge_dc_kw']=frame['pv_charge_dc'].to_numpy(float)
    out['battery_discharge_dc_kw']=frame['battery_discharge_dc'].to_numpy(float)
    out['soc_usable_kwh']=frame['soc_usable_kwh'].to_numpy(float)
    out['soc_pct']=100*(.1+.9*out['soc_usable_kwh']/(modules*m.USABLE_KWH_MODULE)) if modules else np.nan
    out['grid_import_kw']=frame['grid_import'].to_numpy(float)
    out['grid_export_kw']=frame['grid_export'].to_numpy(float)
    out['curtailment_kw']=frame['curtailed_dc'].to_numpy(float)
    out['pcc_p_kw']=frame['pcc_p_kw'].to_numpy(float)
    out['pcc_q_kvar']=frame['pcc_q_kvar'].to_numpy(float)
    out['pcc_s_kva']=frame['pcc_kva'].to_numpy(float)
    # Distinguish algebraic PCC check from UNRUN AC feeder voltage/thermal assessment.
    out['network_validation_status']='NOT_SIMULATED'
    qa=verify_dispatch(out,m,modules,cap_pu)
    cost=m.score(frame,load,pv,modules,panels,inverter_kva,len(houses),cap_pu,pf,
                 initial_soc_pu=float(boundary['initial_soc_pu']))
    # Canonical dispatch API requires a supported inverter rating even for the
    # no-DER counterfactual. Do NOT charge for a nonexistent no-DER inverter.
    if panels==0 and modules==0:
        cost['annual_total_no_credit_usd']=float(frame.grid_import.sum())*m.PRICE_IMPORT
        cost['annual_total_homer_credit_usd']=cost['annual_total_no_credit_usd']
        cost['annualized_equipment_usd']=0.
        cost['capex_ex_vat_usd']=0.
        cost['capex_incl_19pct_vat_usd']=0.
    rating=ARCHIVED_RATINGS.get(territory)
    manifest={
        'model':'case1.wp1_v3.model.dispatch',
        'dispatch_implementation':'canonical DC-coupled _core, no reimplementation',
        'load_profiles':'Original 2025 v18/v5 synthetic profiles, ordinal assignment to candidate houses, NOT metered demand',
        'household_assignment':'Provisional user map/EPM-viewer candidate associations; not certified EPM LV circuits',
        'territory_node':territory,'houses':houses,'house_count':len(houses),
        'transformer_archived_rating_kva':rating,
        'assumed_transformer_kva':5.,
        'nameplate_basis':'archived EPM 5 kVA' if rating else 'HYPOTHETICAL 5 kVA; portal reported kW not confirmed kVA',
        'cap_pu':cap_pu,'max_pcc_apparent_kva':5*cap_pu,'load_pf':pf,
        'pv_panels':panels,'pv_kwp':panels*m.PANEL_KWP,
        'no_der_reference_inverter_is_api_placeholder_only': bool(panels==0 and modules==0),
        'battery_modules':modules,'battery_usable_kwh':modules*m.USABLE_KWH_MODULE,
        'battery_power_kw':battery_power_kw,'inverter_kva':inverter_kva,
        'inverter_efficiency':float(m.ETA_INV),
        'battery_soc_boundary':boundary,'export_policy':'permitted with canonical PCC kVA bound',
        'network_validation_status':'NOT_SIMULATED',
        'input_sha256':{str(x):sha256(root/x) for x in (SOURCE_REL,NASA_REL,MODEL_REL) if (root/x).is_file()},
        'qa':qa,
        'annual_score':{k:(v.item() if isinstance(v,np.generic) else v) for k,v in cost.items()},
    }
    return out,manifest


def verify_dispatch(hourly,m,modules,cap_pu,tol=5e-5):
    def maxerr(arr):return float(np.max(np.abs(arr)))
    ac=hourly.demand_served_kw-(hourly.pv_ac_kw-hourly.grid_export_kw+hourly.battery_discharge_dc_kw*m.ETA_INV+hourly.grid_import_kw)
    dc=hourly.pv_dc_available_kw-((hourly.pv_ac_kw)/m.ETA_INV+hourly.battery_charge_dc_kw+hourly.curtailment_kw)
    pcc=hourly.pcc_p_kw-(hourly.grid_import_kw-hourly.grid_export_kw)
    s=hourly.pcc_s_kva-np.hypot(hourly.pcc_p_kw, hourly.pcc_q_kvar)
    ens=hourly.demand_requested_kw-hourly.demand_served_kw-hourly.ens_kw
    errors={'ac_balance_kw':maxerr(ac),'pv_dc_balance_kw':maxerr(dc),'pcc_p_kw':maxerr(pcc),
            'pcc_s_kva':maxerr(s),'demand_balance_kw':maxerr(ens)}
    if any(x>tol for x in errors.values()):
        raise AssertionError('Canonical dispatch energy balance mismatch: '+str(errors))
    if hourly.pcc_s_kva.max()>5*cap_pu+tol:
        raise AssertionError('PCC apparent power exceeds assumed transformer screening ceiling')
    if ((hourly.battery_charge_dc_kw>tol)&(hourly.battery_discharge_dc_kw>tol)).any():
        raise AssertionError('Battery charge and discharge simultaneously')
    if hourly.soc_usable_kwh.min() < -tol or hourly.soc_usable_kwh.max() > modules*m.USABLE_KWH_MODULE+tol:
        raise AssertionError('Battery SOC outside usable range')
    if (hourly[ ['demand_requested_kw','demand_served_kw','ens_kw','grid_import_kw','grid_export_kw','pv_ac_kw'] ] < -tol).any().any():
        raise AssertionError('Unexpected negative physical power')
    return {'maximum_residuals':errors,'max_pcc_kva':float(hourly.pcc_s_kva.max()),
            'ens_kwh':float(hourly.ens_kw.sum()),'hours_with_unserved_load':int((hourly.ens_kw>tol).sum()),
            'peak_grid_import_kw':float(hourly.grid_import_kw.max()),'max_usable_soc_kwh':float(hourly.soc_usable_kwh.max())}


def write_case(root,outdir,**kwargs):
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    hourly,manifest=dispatch_case(root,**kwargs)
    hourly.to_csv(outdir/'annual_dispatch_8760.csv',float_format='%.8f',index_label='timestamp_lst')
    from report_timeseries import run as report
    monthly,yearly=report(outdir/'annual_dispatch_8760.csv',outdir/'figures')
    manifest['monthly_self_sufficiency_pct']={str(t.date()):float(v) for t,v in monthly.self_sufficiency_pct.items()}
    manifest['months_zero_grid_import_and_zero_ens']=[str(t.date()) for t in monthly.index[monthly.fully_grid_independent_and_served]]
    (outdir/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False,default=str),encoding='utf-8')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=None)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--territory',choices=list(TERRITORIES),default='931076')
    p.add_argument('--include-house',choices=['H01','H02'],action='append',default=[])
    p.add_argument('--panels',type=int,default=24)
    p.add_argument('--battery-modules',type=int,default=4)
    p.add_argument('--battery-power-kw',type=float,default=5.)
    p.add_argument('--inverter-kva',type=float,default=10.)
    p.add_argument('--pf',type=float,default=.98)
    p.add_argument('--cap-pu',type=float,default=.9)
    p.add_argument('--soc-mode',choices=['cyclic','fixed'],default='cyclic')
    p.add_argument('--initial-soc',type=float,default=.55)
    a=p.parse_args()
    args=dict(territory=a.territory,include=a.include_house,panels=a.panels,modules=a.battery_modules,
              battery_power_kw=a.battery_power_kw,inverter_kva=a.inverter_kva,pf=a.pf,cap_pu=a.cap_pu,
              soc_mode=a.soc_mode,initial_soc=a.initial_soc)
    manifest=write_case(locate_repo(a.repo_root),a.outdir,**args)
    print(json.dumps({'outdir':str(a.outdir),'house_count':manifest['house_count'],
                      'network_validation_status':manifest['network_validation_status'],
                      'qa':manifest['qa'],'monthly_self_sufficiency_pct':manifest['monthly_self_sufficiency_pct']},indent=2))

if __name__=='__main__':
    main()
