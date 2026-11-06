#!/usr/bin/env python3
"""Join archived energy equipment with NEW annual SOC/AC evidence; never infer passes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from audit_archived_campaign import sha256
from batch_archived_campaign import scenarios


def nondominated(data:pd.DataFrame):
    keep=[]
    for ix,row in data.iterrows():
        c=float(row.manufacturer_annual_cost_usd)
        ss=float(row.manufacturer_self_sufficiency_pct)
        dominated=((data.manufacturer_annual_cost_usd<=c+1e-6)&
           (data.manufacturer_self_sufficiency_pct>=ss-1e-6)&
           ((data.manufacturer_annual_cost_usd<c-1e-6)|
            (data.manufacturer_self_sufficiency_pct>ss+1e-6)))
        keep.append(not bool(dominated.any()))
    return keep


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan-dir',type=Path,required=True)
    p.add_argument('--energy-root',type=Path,required=True)
    p.add_argument('--ac-root',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--scenario-set',choices=['reference','nine'],default='nine')
    a=p.parse_args(argv)
    if a.outdir.exists():p.error('Output exists. Keep results immutable and use a new folder.')
    idx=pd.read_csv(a.plan_dir/'all_distinct_equipment_candidates.csv',keep_default_na=False)
    scored=[];scenario_rows=[];expected=scenarios(a.scenario_set)
    failure_log=a.plan_dir/'batch_energy_events.jsonl'
    attempted={}
    if failure_log.exists():
        for line in failure_log.read_text(encoding='utf8').splitlines():
            if line.strip():
                entry=json.loads(line); attempted[str(entry['candidate_id'])]=int(entry['returncode'])
    for r in idx.itertuples(index=False):
        item=r._asdict();eid=r.equipment_id
        item.update(manufacturer_annual_cost_usd=float('nan'),
             manufacturer_grid_import_kwh=float('nan'),manufacturer_self_sufficiency_pct=float('nan'),
             manufacturer_SOC_status='NOT_RUN',new_AC_reference_status='NOT_RUN',
             stress_AC_status='NOT_RUN',full_nine_scenario_robust=False)
        pilot=a.energy_root/eid/'pilot_manifest.json'
        if not pilot.is_file() and attempted.get(eid,0)!=0:
            item['manufacturer_SOC_status']='ATTEMPTED_FAILED_RETURN_CODE_'+str(attempted[eid])
        if pilot.is_file():
            m=json.loads(pilot.read_text(encoding='utf8'))
            traj=a.energy_root/eid/'fixed_hardware_manufacturer_soc_baseline.csv'
            if m.get('candidate_id')!=eid or sha256(traj)!=m.get('source_trajectory_sha256'):
                item['manufacturer_SOC_status']='CORRUPT_SOURCE_HASH'
            else:
                df=pd.read_csv(traj)
                if len(df)!=8760: item['manufacturer_SOC_status']='INCOMPLETE_HOURLY'
                else:
                    item['manufacturer_SOC_status']='FULL_YEAR_8760_SOC_VERIFIED_IN_SOURCE'
                    item['manufacturer_annual_cost_usd']=float(m['manufacturer_soc_baseline_annual_total_usd'])
                    item['manufacturer_grid_import_kwh']=float(m['manufacturer_soc_baseline_grid_import_kwh'])
                    demand=float(df.demand_kw.sum())
                    item['manufacturer_self_sufficiency_pct']=100*(demand-item['manufacturer_grid_import_kwh'])/demand if demand>0 else float('nan')
        passes=[];complete=[]
        for pf,service in expected:
            d=a.ac_root/eid/f'pf_{pf:.2f}_service_{service:.2f}'
            state=d/'ac_checkpoint.json';summ=d/'annual_ac_summary.json'
            o={'equipment_id':eid,'load_pf':pf,'service_factor':service,
               'annual_AC_state':'NOT_RUN','annual_AC_feasible':False,
               'min_v_pu':None,'max_trafo_pct':None,'source_AC_hours':0}
            if state.is_file() and not summ.is_file():
                o['annual_AC_state']='INCOMPLETE_OR_INTERRUPTED_ANNUAL_AC'
            if state.is_file() and summ.is_file():
                j=json.loads(state.read_text(encoding='utf8'))
                z=json.loads(summ.read_text(encoding='utf8'))
                valid=(j.get('status')=='COMPLETE' and z.get('candidate_id')==eid and
                       int(z.get('hours_checked',-1))==8760 and z.get('all_8760_evaluated') is True and
                       abs(float(z.get('load_pf',0))-pf)<1e-8 and
                       abs(float(z.get('service_factor',0))-service)<1e-8 and
                       z.get('source_trajectory_sha256')==(
                          json.loads(pilot.read_text()).get('source_trajectory_sha256') if pilot.is_file() else None))
                o['annual_AC_state']='COMPLETE_8760' if valid else 'INCONSISTENT_AC_PROVENANCE'
                o['annual_AC_feasible']=bool(valid and z.get('ac_feasible_full_year') is True)
                o['source_AC_hours']=int(z.get('hours_checked',0))
                o['min_v_pu']=z.get('min_voltage_pu')
                o['max_trafo_pct']=z.get('max_trafo_loading_pct')
            scenario_rows.append(o)
            passes.append(o['annual_AC_feasible']);complete.append(o['annual_AC_state']=='COMPLETE_8760')
        if item['manufacturer_SOC_status'].startswith('FULL_YEAR') and complete:
            item['new_AC_reference_status']='ANNUAL_PASS' if complete[0] and passes[0] else ('ANNUAL_FAIL' if complete[0] else 'NOT_RUN')
            item['stress_AC_status']=('ALL_NINE_ANNUAL_PASS' if len(expected)==9 and all(passes)
              else 'ALL_SCENARIOS_RUN_WITH_FAILURES' if len(expected)==9 and all(complete)
              else 'PARTIAL_AC_CAMPAIGN')
            item['full_nine_scenario_robust']=bool(len(expected)==9 and all(complete) and all(passes))
        scored.append(item)
    scored=pd.DataFrame(scored)
    scenarios_df=pd.DataFrame(scenario_rows)
    eligible=scored.loc[(scored.full_nine_scenario_robust if a.scenario_set=='nine' else
                scored.new_AC_reference_status.eq('ANNUAL_PASS')) &
                scored.manufacturer_annual_cost_usd.notna()].copy()
    eligible['nondominated_within_validated_subset']=False
    for (case,kva),sub in eligible.groupby(['case','assumed_transformer_kva']):
        eligible.loc[sub.index,'nondominated_within_validated_subset']=nondominated(sub)
    a.outdir.mkdir(parents=True)
    scored.to_csv(a.outdir/'all_equipment_with_new_validation_status.csv',index=False)
    scenarios_df.to_csv(a.outdir/'annual_AC_scenario_ledger.csv',index=False)
    eligible.to_csv(a.outdir/'validated_conditional_cost_self_sufficiency_comparison.csv',index=False)
    status={'archive_equipment_rows':len(scored),'annual_SOC_complete':int(scored.manufacturer_SOC_status.str.startswith('FULL_YEAR').sum()),
            'annual_AC_complete_scenario_rows':int((scenarios_df.annual_AC_state=='COMPLETE_8760').sum()),
            'new_AC_reference_pass_candidates':int((scored.new_AC_reference_status=='ANNUAL_PASS').sum()),
            'all_nine_annual_robust_candidates':int(scored.full_nine_scenario_robust.sum()),
            'conditional_nondominated_comparison_rows':len(eligible),
            'full_archive_revalidated':False,
            'interpretation':'Every original historical task-level outcome is kept in archived_task_registry.csv. Nondominance is among newly checked designs only; missing AC is NOT feasible.'}
    (a.outdir/'collation_manifest.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf8')
    print(json.dumps(status,indent=2))

if __name__=='__main__':main()
