#!/usr/bin/env python3
"""Read-only independent audit of uploaded A1 106039 AC-aware trial files.
No model runs, source edits or network access. Run from any directory with --input.
"""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ETA_INV=.95
ETA_BAT=math.sqrt(.95)
FLOOR=8*(4.325-0.8*5.12)


def audit(path):
    path=Path(path)
    manifest=json.loads((path/'trial_manifest.json').read_text(encoding='utf-8'))
    checks={}
    energy=[]
    for tier in ('min_cost_ref','ss90_ref'):
        ref=manifest['candidate_annual_files'][tier]
        f=path/ref['path']
        checks[f'{tier}_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()==ref['sha256']
        df=pd.read_csv(f)
        t=pd.to_datetime(df.timestamp_lst)
        checks[f'{tier}_2025_hourly']=len(df)==8760 and t.equals(pd.Series(pd.date_range('2025-01-01',periods=8760,freq='h')))
        num=df.select_dtypes(include='number')
        checks[f'{tier}_finite']=bool(np.isfinite(num.to_numpy()).all())
        checks[f'{tier}_dc_balance']=bool((df.pv_dc_generated_kw+df.battery_discharge_dc_kw-df.battery_charge_dc_kw-df.inverter_ac_kw/ETA_INV).abs().max()<5e-6)
        checks[f'{tier}_ac_balance']=bool((df.inverter_ac_kw+df.grid_import_kw-df.grid_export_kw+df.unserved_kw-df.demand_kw).abs().max()<5e-6)
        checks[f'{tier}_curtailment_balance']=bool((df.pv_dc_available_kw-df.pv_dc_generated_kw-df.curtailed_pv_dc_kw).abs().max()<5e-6)
        checks[f'{tier}_soc_floor_ceiling']=bool(df.battery_soc_usable_kwh.min()>=FLOOR-1e-6 and df.battery_soc_usable_kwh.max()<=8*4.325+1e-6)
        bpower=float(manifest['device_reference'][tier]['battery_power_dc_kw'])
        checks[f'{tier}_power_and_no_simultaneous_charge_discharge']=bool((df.battery_charge_dc_kw>=-1e-7).all() and (df.battery_discharge_dc_kw>=-1e-7).all() and df.battery_charge_dc_kw.max()<=bpower+1e-6 and df.battery_discharge_dc_kw.max()<=bpower+1e-6 and not ((df.battery_charge_dc_kw>1e-7)&(df.battery_discharge_dc_kw>1e-7)).any())
        checks[f'{tier}_zero_export_unserved']=bool((df.grid_export_kw.abs()<1e-6).all() and (df.unserved_kw.abs()<1e-6).all())
        soc=df.battery_soc_usable_kwh.to_numpy();step=(ETA_BAT*df.battery_charge_dc_kw-df.battery_discharge_dc_kw/ETA_BAT).to_numpy()
        checks[f'{tier}_soc_hourly_and_cyclic']=bool((np.abs(np.diff(soc)-step[1:])<1e-6).all() and abs(soc[0]-soc[-1]-step[0])<1e-6)
        checks[f'{tier}_annual_import_matches_manifest']=bool(abs(df.grid_import_kw.sum()-next(x['candidate']['grid_import_kwh'] for x in manifest['energy_comparison'] if x['tier']==tier))<1e-5)
        checks[f'{tier}_yearend_soc_matches_manifest']=bool(abs(soc[-1]-next(x['candidate']['soc_end_kwh'] for x in manifest['energy_comparison'] if x['tier']==tier))<1e-5)
        energy.append({'tier':tier,'annual_demand_kwh':round(df.demand_kw.sum(),6),'grid_import_kwh':round(df.grid_import_kw.sum(),6),
            'self_sufficiency_pct':round(100*(1-df.grid_import_kw.sum()/df.demand_kw.sum()),5),
            'pv_available_dc_kwh':round(df.pv_dc_available_kw.sum(),6),'pv_curtailed_dc_kwh':round(df.curtailed_pv_dc_kw.sum(),6),
            'pv_curtailment_pct':round(100*df.curtailed_pv_dc_kw.sum()/df.pv_dc_available_kw.sum(),4),
            'min_soc_kwh':df.battery_soc_usable_kwh.min(),'end_soc_kwh':soc[-1]})
    ac=pd.read_csv(path/'changed_hour_ac_checks.csv');screen=pd.read_csv(path/'nine_factor_annual_reuse_comparisons.csv');shifts=pd.read_csv(path/'candidate_shifts.csv')
    checks['three_planned_shifts']=len(shifts)==3 and shifts.tier.value_counts().to_dict()=={'min_cost_ref':2,'ss90_ref':1}
    checks['18_pf_length_results']=len(screen)==18 and not screen.duplicated(['tier','pf','length_factor']).any() and set(screen.pf)=={.95,.98,1.0} and set(screen.length_factor)=={1.0,1.3,1.6}
    checks['108_changed_hour_records']=len(ac)==108 and len(ac[ac.change=='candidate'])==54 and len(ac[ac.change=='original'])==54
    checks['all_changed_ac_converged']=bool((ac.status=='CONVERGED').all())
    checks['candidate_changed_ac_feasible']=bool(ac.loc[ac.change=='candidate','ac_feasible'].all())
    checks['all_18_candidate_annual_feasible']=bool((screen.candidate_bad_hours==0).all() and screen.all_8760_hours_accounted_for.all())
    checks['baseline_positive_violations']=bool((screen.baseline_bad_hours>0).all())
    checks['candidate_voltage_and_trafo_limits']=bool((screen.min_v_pu>=.95-1e-7).all() and (screen.candidate_max_trafo_pct<=100+1e-7).all())
    # Match per-scenario changed-hour AC feasibility against the reported baseline and candidate statuses.
    ac_bad=ac.assign(bad=~ac.ac_feasible.astype(bool)).groupby(['tier','pf','length_factor','change'])['bad'].sum().unstack(fill_value=0).reset_index()
    joined=screen.merge(ac_bad,on=['tier','pf','length_factor'],validate='one_to_one')
    checks['changed_original_bad_hours_match_annual']=bool((joined['original']==joined.baseline_bad_hours).all())
    checks['changed_candidate_bad_hours_match_annual']=bool((joined['candidate']==joined.candidate_bad_hours).all())
    if not all(checks.values()):raise AssertionError('Independent checks failed: '+str({k:v for k,v in checks.items() if not v}))
    return checks,energy,screen


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,default=Path('/mnt/data'))
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    checks,energy,screen=audit(args.input)
    print('CHECKS PASSED',len(checks), 'CASES',len(screen))
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'INDEPENDENT_QA.json').write_text(json.dumps({'status':'PASS','checks':checks,'energy':energy,'status_summary':{'all_18_annual_sensitivity_cases_pass':True,'model_context':'changed-hour re-solve plus verified unchanged-hour reuse'}},indent=2)+'\n')
        screen.to_csv(args.out/'TRIAL_18_AC_RESULTS.csv',index=False)

if __name__=='__main__':main()
