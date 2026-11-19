#!/usr/bin/env python3
"""Signed 2025 MC_REF vs MC_P33 PV curtailment and causal PV-first diagnostic.

Read-only on original sources. This is NOT an AC-feasible controller:
the chronological replay does not constrain transformer/grid imports,
but explicitly counts hourly violations of the signed 5 kVA PF=0.98
energy-model proxy. No cost optimization or simulation source mutation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ETA_INV = .95
ETA_BAT = math.sqrt(.95)
GRID_KVA_ASSUMED = 5.
GRID_PF_ASSUMED = .98
COLS = ('demand_kw','pv_dc_generated_kw','pv_dc_available_kw',
        'battery_charge_dc_kw','battery_discharge_dc_kw','inverter_ac_kw',
        'battery_soc_usable_kwh','grid_import_kw','grid_export_kw',
        'unserved_kw','curtailed_pv_dc_kw')
SOURCES = {
    'MC_REF': ('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01/'
               'energy_A1_106039_min_cost_ref'),
    'MC_P33': 'StudyA_A1_106039_Utilization_v1/energy_MC_P33',
}
SIGNED_CSV = {
    'MC_REF': '8b1e20b218fe4edab51dea2e2e81566077321ca6cb4929746ff84c6043e45e65',
    'MC_P33': 'e1faf60587b248923f05d08b4979c92c7e64fa23ba5306a0390a68af32079123',
}
SIGNED_INPUT = '2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69'
HOUSES = ('H11','H16','H17','H18','H19','H20','H21','H22','H23','H24','H25')


def signature_mode(path, expected):
    """Accept literal original bytes or *exact* LF->CRLF signed byte recovery."""
    raw = Path(path).read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got == expected:
        return 'SIGNED_BYTES'
    if b'\r' not in raw and b'\n' in raw:
        if hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest() == expected:
            return 'EXACT_GIT_NEWLINE_NORMALIZATION'
    raise ValueError('Signed dispatch file differs from original: '+str(path))


def read_signed(repo, case):
    root = repo / SOURCES[case]
    manifest_path = root / 'energy_manifest.json'
    info = json.loads(manifest_path.read_text(encoding='utf-8'))
    if info.get('energy_csv_sha256') != SIGNED_CSV[case]:
        raise ValueError('Original energy manifest SHA mismatch: '+case)
    if info.get('input_manifest_sha256') != SIGNED_INPUT:
        raise ValueError('Unexpected signed 35-home demand source: '+case)
    if tuple(info.get('selected_house_ids', ())) != HOUSES:
        raise ValueError('Household identity changed: '+case)
    if info.get('transformer') != '106039' or info.get('scenario') != 'A1':
        raise ValueError('Wrong physical cohort: '+case)
    hw = info['hardware']
    n = int(hw['battery_modules'])
    if (int(hw['pv_panels']) != (41 if case == 'MC_REF' else 33) or
            n != 8 or abs(float(hw['battery_power_dc_kw'])-12.)>1e-8 or
            abs(float(hw['inverter_kva'])-12.)>1e-8):
        raise ValueError('Not the matched eight-battery 12 kVA hardware: '+case)
    cpath = root / 'energy_hourly_2025.csv'
    mode = signature_mode(cpath, SIGNED_CSV[case])
    df = pd.read_csv(cpath, parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    idx = pd.date_range('2025-01-01', periods=8760, freq='h')
    if len(df)!=8760 or not df.index.equals(idx) or not set(COLS).issubset(df.columns):
        raise ValueError('2025 hourly source chronology or fields missing: '+case)
    if not np.isfinite(df[list(COLS)].to_numpy(float)).all():
        raise ValueError('Nonfinite original dispatch: '+case)
    if (df.grid_export_kw.abs().max()>1e-6 or df.unserved_kw.abs().max()>1e-6 or
        (df.inverter_ac_kw+df.grid_import_kw-df.demand_kw).abs().max()>1e-5 or
        (df.pv_dc_generated_kw+df.battery_discharge_dc_kw-
          df.battery_charge_dc_kw-df.inverter_ac_kw/ETA_INV).abs().max()>1e-5):
        raise ValueError('Source energy balance, zero-export or ENS mismatch: '+case)
    floor = .229*n
    maxsoc = 4.325*n
    if df.battery_soc_usable_kwh.min()<floor-1e-5 or df.battery_soc_usable_kwh.max()>maxsoc+1e-5:
        raise ValueError('Source battery SOC bounds differ: '+case)
    difference = (df.battery_soc_usable_kwh - df.battery_soc_usable_kwh.shift(fill_value=df.battery_soc_usable_kwh.iloc[-1]) -
                  ETA_BAT*df.battery_charge_dc_kw + df.battery_discharge_dc_kw/ETA_BAT).abs().max()
    if difference>1e-4:
        raise ValueError(f'Signed battery recurrence mismatch: {case}: {difference}')
    return df, hw, {'case':case,'signed_csv_SHA256':SIGNED_CSV[case],
                     'read_mode':mode,'source_manifest_path':str(manifest_path.relative_to(repo))}


def grid_bound(demand):
    q=np.asarray(demand,dtype=float)*math.sqrt(1/GRID_PF_ASSUMED**2-1)
    return np.sqrt(np.maximum(0.,GRID_KVA_ASSUMED**2-q**2))


def causal_pv_first(frame, hardware, initial_soc):
    """Greedy PV->direct load->surplus charge; battery for deficits, then grid.

    No forecast, no export, no grid charging, no simultaneous charge/discharge.
    Does not enforce the grid transformer P/Q bound: every exceedance is logged.
    Source e_cyclic and source-year final SOC are checked by the caller.
    """
    n=int(hardware['battery_modules'])
    floor=.229*n
    maximum=4.325*n
    max_power=float(hardware['battery_power_dc_kw'])
    max_inv=float(hardware['inverter_kva'])
    if not floor-1e-8 <= initial_soc <= maximum+1e-8:
        raise ValueError('Invalid initial state for replay')
    soc=float(initial_soc)
    records=[]
    for timestamp,row in frame.iterrows():
        demand=float(row.demand_kw)
        pv=float(row.pv_dc_available_kw)
        direct=min(pv,demand/ETA_INV,max_inv/ETA_INV)
        needed=max(0.,demand/ETA_INV-direct)
        surplus=max(0.,pv-direct)
        charge=min(surplus,max_power,max(0.,(maximum-soc)/ETA_BAT))
        discharge=min(needed,max_power,max(0.,(soc-floor)*ETA_BAT),
                      max(0.,max_inv/ETA_INV-direct))
        inv_ac=ETA_INV*(direct+discharge)
        imported=max(0.,demand-inv_ac)
        curtail=max(0.,pv-direct-charge)
        soc=min(maximum,max(floor,soc+ETA_BAT*charge-discharge/ETA_BAT))
        bound=float(grid_bound([demand])[0])
        records.append({'timestamp_lst':timestamp,'pv_dc_generated_kw':direct+charge,
                        'battery_charge_dc_kw':charge,'battery_discharge_dc_kw':discharge,
                        'inverter_ac_kw':inv_ac,'battery_soc_usable_kwh':soc,
                        'grid_import_kw':imported,'curtailed_pv_dc_kw':curtail,
                        'grid_import_limit_proxy_kw':bound,
                        'grid_import_proxy_excess_kw':max(0.,imported-bound)})
    replay=pd.DataFrame.from_records(records).set_index('timestamp_lst')
    if not replay.index.equals(frame.index):
        raise ValueError('Replay timestamp index changed')
    return replay


def describe_original(frame,hw,case):
    cur=frame.curtailed_pv_dc_kw>1e-6
    floor=.229*int(hw['battery_modules'])
    empty=frame.battery_soc_usable_kwh<=floor+1e-4
    idle=frame.battery_charge_dc_kw<1e-6
    imp=frame.grid_import_kw>1e-6
    return {
        'case':case,'hours':len(frame),'annual_demand_kwh':float(frame.demand_kw.sum()),
        'annual_available_pv_dc_kwh':float(frame.pv_dc_available_kw.sum()),
        'annual_generated_pv_dc_kwh':float(frame.pv_dc_generated_kw.sum()),
        'annual_curtailed_pv_dc_kwh':float(frame.curtailed_pv_dc_kw.sum()),
        'annual_grid_import_ac_kwh':float(frame.grid_import_kw.sum()),
        'annual_battery_discharge_dc_kwh':float(frame.battery_discharge_dc_kw.sum()),
        'curtailed_hours':int(cur.sum()),'grid_import_hours':int(imp.sum()),
        'hours_both_curtail_and_import':int((cur&imp).sum()),
        'curtailment_while_SOC_at_floor_kwh':float(frame.loc[cur&empty,'curtailed_pv_dc_kw'].sum()),
        'curtailment_while_not_charging_kwh':float(frame.loc[cur&idle,'curtailed_pv_dc_kw'].sum()),
        'curtailment_while_SOC_at_ceiling_kwh':float(frame.loc[cur&(frame.battery_soc_usable_kwh >=
                                               4.325*int(hw['battery_modules'])-1e-4),'curtailed_pv_dc_kw'].sum()),
        'soc_min_usable_kwh':float(frame.battery_soc_usable_kwh.min()),
        'soc_year_end_usable_kwh':float(frame.battery_soc_usable_kwh.iloc[-1]),
    }


def compare_source_and_causal(source, causal, case):
    for key in ('grid_import_kw','curtailed_pv_dc_kw','battery_charge_dc_kw','battery_discharge_dc_kw'):
        if not np.isfinite(causal[key].to_numpy()).all():
            raise ValueError('Nonfinite causal energy flow')
    original_bound=grid_bound(source.demand_kw)
    if np.any(source.grid_import_kw.to_numpy()>original_bound+1e-4):
        raise ValueError('The signed source violates its own economic P/Q envelope')
    violations=causal[causal.grid_import_proxy_excess_kw>1e-6]
    changed_curt=(causal.curtailed_pv_dc_kw-source.curtailed_pv_dc_kw).abs()>1e-5
    changed_charge=(causal.battery_charge_dc_kw-source.battery_charge_dc_kw).abs()>1e-5
    original_soc_end=float(source.battery_soc_usable_kwh.iloc[-1])
    replay_soc_end=float(causal.battery_soc_usable_kwh.iloc[-1])
    return {
        'case':case,
        'source_grid_import_kwh':float(source.grid_import_kw.sum()),
        'pv_first_grid_import_kwh':float(causal.grid_import_kw.sum()),
        'source_curtailment_kwh':float(source.curtailed_pv_dc_kw.sum()),
        'pv_first_curtailment_kwh':float(causal.curtailed_pv_dc_kw.sum()),
        'difference_grid_import_kwh':float((causal.grid_import_kw-source.grid_import_kw).sum()),
        'difference_curtailment_kwh':float((causal.curtailed_pv_dc_kw-source.curtailed_pv_dc_kw).sum()),
        'curtailment_timing_changed_hours':int(changed_curt.sum()),
        'charging_timing_changed_hours':int(changed_charge.sum()),
        'original_year_end_SOC_kwh':original_soc_end,
        'pv_first_year_end_SOC_kwh':replay_soc_end,
        'cyclic_match_to_source':abs(original_soc_end-replay_soc_end)<1e-5,
        'grid_proxy_failure_hours':int(len(violations)),
        'grid_proxy_max_excess_kw':float(causal.grid_import_proxy_excess_kw.max()),
        'grid_proxy_failure_events':[{'timestamp':str(i),
             'grid_import_kw':float(row.grid_import_kw),
             'grid_import_bound_kw':float(row.grid_import_limit_proxy_kw),
             'excess_kw':float(row.grid_import_proxy_excess_kw)} for i,row in violations.iterrows()],
        'no_AC_feasibility_claim':True,
    }


def monthly_record(case, source, causal):
    items=[]
    for month in range(1,13):
        a=source[source.index.month==month]
        b=causal[causal.index.month==month]
        items.append({
            'case_id':case,'month':month,'pv_available_dc_kwh':float(a.pv_dc_available_kw.sum()),
            'source_curtail_dc_kwh':float(a.curtailed_pv_dc_kw.sum()),
            'pv_first_curtail_dc_kwh':float(b.curtailed_pv_dc_kw.sum()),
            'source_grid_import_ac_kwh':float(a.grid_import_kw.sum()),
            'pv_first_grid_import_ac_kwh':float(b.grid_import_kw.sum()),
            'source_battery_charge_dc_kwh':float(a.battery_charge_dc_kw.sum()),
            'pv_first_battery_charge_dc_kwh':float(b.battery_charge_dc_kw.sum()),
        })
    return items


def run(repo,out=None):
    root=repo.resolve()
    source={}
    hardware={}
    provenance={}
    for case in SOURCES:
        source[case],hardware[case],provenance[case]=read_signed(root,case)
    if not np.allclose(source['MC_REF'].demand_kw,source['MC_P33'].demand_kw,rtol=0,atol=1e-8):
        raise ValueError('Reference and reduced-PV case do not have identical 11-house demand')
    original={case:describe_original(source[case],hardware[case],case) for case in SOURCES}
    derived={}
    replay={}
    months=[]
    for case in SOURCES:
        replay[case]=causal_pv_first(source[case],hardware[case],
                                     float(source[case].battery_soc_usable_kwh.iloc[-1]))
        derived[case]=compare_source_and_causal(source[case],replay[case],case)
        months.extend(monthly_record(case,source[case],replay[case]))
    old,new=original['MC_REF'],original['MC_P33']
    decomposition={
        'PV_removed_panels':8,'lost_PV_available_dc_kwh':old['annual_available_pv_dc_kwh']-new['annual_available_pv_dc_kwh'],
        'curtailment_reduction_dc_kwh':old['annual_curtailed_pv_dc_kwh']-new['annual_curtailed_pv_dc_kwh'],
        'lost_PV_used_dc_kwh':old['annual_generated_pv_dc_kwh']-new['annual_generated_pv_dc_kwh'],
        'grid_import_increase_ac_kwh':new['annual_grid_import_ac_kwh']-old['annual_grid_import_ac_kwh'],
        'battery_discharge_reduction_dc_kwh':old['annual_battery_discharge_dc_kwh']-new['annual_battery_discharge_dc_kwh'],
        'assessment':'SIGNED_PV_RESOURCE_LOSS_PLUS_TIMING_AND_OPTIMAL_CHARGE_DEGENERACY',
    }
    document={'status':'SIGNED_SOURCE_PV_FIRST_CAUSAL_DIAGNOSTIC_ONLY',
              'case_ids':list(SOURCES),'input_sha256':SIGNED_INPUT,
              'source_provenance':provenance,'annual_source':original,
              'replay_comparison':derived,'energy_decomposition':decomposition,
              'interpretation':'PV-first affects hourly charge/curtailment timing without changing annual energy in these cases; naive greedy violates import P/Q bound for MC_P33. Never claim AC certification.'}
    if out is not None:
        out=out.resolve()
        if out.exists():raise FileExistsError(f'Refusing to overwrite diagnostic directory: {out}')
        out.mkdir(parents=True,exist_ok=False)
        (out/'DIAGNOSTIC_MANIFEST.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        pd.DataFrame(months).to_csv(out/'MONTHLY_ORIGINAL_VS_PV_FIRST.csv',index=False,float_format='%.10f')
        for case in SOURCES:
            replay[case].to_csv(out/(case+'_CAUSAL_PV_FIRST_8760.csv'),float_format='%.10f',index_label='timestamp_lst')
    return {'status':document['status'],'MC_REF':derived['MC_REF'],
            'MC_P33':derived['MC_P33'],'decomposition':decomposition,'output':str(out) if out else None}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--out',type=Path,help='New result directory, no overwrite')
    args=ap.parse_args()
    print(json.dumps(run(args.repo_root,args.out),indent=2))


if __name__=='__main__':
    main()
