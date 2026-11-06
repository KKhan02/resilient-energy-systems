#!/usr/bin/env python3
"""Index every archived SEEDExchange 6840-task MILP result; NO solver is called.

Exactly identical fixed hardware may recur across cost, self-sufficiency and
budget objectives. Deduplicate hardware for *new* annual AC work while keeping
all original task rows and objective provenance. No energy-only solution is
promoted to AC-feasible by this script.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
import numpy as np

SOURCE = Path('case1/studies/pypsa_joint_optimization_v1/outputs/full_study/complete_study_results.csv')
MANIFEST = SOURCE.with_name('study_manifest.json')
RUN_PLAN = SOURCE.with_name('run_plan.json')
CASE_TO_GIS = {'7_homes': ('seven', '94022'), '9_homes': ('nine', '94022'),
               '12_homes': ('twelve', '106039')}
CURRENT_PER_MODULE_KW = 44.8 * 50 / 1000  # Conservative SE-G5.1 screen, not a certified bank rating.
KEY_COLUMNS = ('case', 'kva', 'panels_round', 'modules_round', 'battery_kw_round', 'inverter_kva_round')
NUMERIC = ['kva','panels_equivalent','battery_modules_equivalent','battery_power_dc_kw',
           'inverter_ac_kva_assumed_unity_pf','annual_total_usd','annual_equipment_usd',
           'unserved_kwh','grid_import_kwh','self_sufficiency_of_demand_pct','annual_hours']


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equipment_key(row: dict) -> tuple:
    def num(s):
        value = float(row[s])
        if not np.isfinite(value): raise ValueError('Non-finite hardware '+s)
        return value
    panels, modules = num('panels_equivalent'), num('battery_modules_equivalent')
    if any(abs(v-round(v)) > 1e-5 for v in (panels, modules)):
        raise ValueError('Archived solution is not integer-buildable')
    power, inverter = num('battery_power_dc_kw'), num('inverter_ac_kva_assumed_unity_pf')
    if min(panels, modules, power, inverter) < -1e-5:
        raise ValueError('Negative hardware')
    return (str(row['case']), round(num('kva'),3), int(round(panels)), int(round(modules)),
            round(power, 6), round(inverter, 4))


def equipment_id(key: tuple) -> str:
    # Stable across CSV ordering; first 20 SHA256 chars avoid positional IDs.
    return 'EC-' + hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()[:20]


def geography_gate(case: str, kva: float) -> tuple[str, str, str]:
    if case not in CASE_TO_GIS:
        return 'GIS_MAPPING_REQUIRED', '', ''
    scenario, trafo=CASE_TO_GIS[case]
    return ('GIS_MAPPED_CONDITIONAL' if abs(kva-5)<1e-6 else 'GIS_MAPPED_HYPOTHETICAL_TRAFO_KVA',
            scenario,trafo)


def archive_to_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    required={'case','task','task_key','status','kva',*NUMERIC}
    missing=required-set(df.columns)
    if missing: raise ValueError('Incomplete saved campaign schema: '+str(sorted(missing)))
    if df.task_key.isna().any() or df.task_key.duplicated().any():
        raise ValueError('Missing or duplicated archived solver task key')
    registry=df.copy()
    registry['archived_status']=registry.status.astype(str)
    registry['equipment_id']=''
    registry['new_evidence_gate']='ARCHIVED_INFEASIBLE_OR_FAILED'
    by_key={}
    for idx,row in registry.iterrows():
        if row['status']!='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER':
            continue
        if not np.isclose(float(row['annual_hours']),8760,atol=0.1):
            raise ValueError('Archived optimal task is not full-year: '+str(row.task_key))
        if float(row['unserved_kwh'])>1e-5:
            registry.at[idx,'new_evidence_gate']='REVIEW_NONZERO_ENS'
            continue
        try:
            key=equipment_key(row)
        except (ValueError,TypeError):
            registry.at[idx,'new_evidence_gate']='REVIEW_NON_BUILDABLE_EQUIPMENT'
            continue
        eid=equipment_id(key)
        registry.at[idx,'equipment_id']=eid
        registry.at[idx,'new_evidence_gate']='ARCHIVED_ENERGY_ONLY_NEW_AC_NOT_RUN'
        by_key.setdefault(key,[]).append(idx)
    rows=[]
    for key,indices in by_key.items():
        sub=registry.loc[indices]
        primary=sub.loc[pd.to_numeric(sub.annual_total_usd).idxmin()]
        case,kva,panels,modules,power,inv=key
        gate,case_alias,trafo=geography_gate(case,kva)
        current_ok=(power<=modules*CURRENT_PER_MODULE_KW+1e-5)
        source_indices=sorted(str(x) for x in sub.task_key)
        reasons=[]
        if not current_ok: reasons.append('SE_G5_1_CONSERVATIVE_DC_CURRENT_SCREEN_FAILED')
        if inv<=1e-6: reasons.append('ZERO_INVERTER_REQUIRES_GRID_ONLY_AC_PATH')
        if not case_alias: reasons.append('NO_GIS_CUSTOMER_MAPPING_FOR_SYNTHETIC_HOUSE_COUNT')
        if kva!=5. and case_alias: reasons.append('TRANSFORMER_RATING_HYPOTHETICAL')
        rows.append(dict(equipment_id=equipment_id(key),case=case,case_alias=case_alias,
             transformer=trafo,assumed_transformer_kva=kva,transformer_evidence=gate,
             pv_panels=panels,pv_kwp=panels*0.435,battery_modules=modules,
             battery_nominal_kwh=modules*5.12,battery_reference_usable_kwh=modules*(17.3/4),
             battery_power_dc_kw=power,inverter_kva=inv,
             manufacturer_current_proxy_pass=bool(current_ok),
             existing_fixed_hardware_runner_eligible=bool(case_alias and current_ok and inv>0),
             candidate_gate='READY_FOR_NEW_MANUFACTURER_SOC_SOLVE' if (case_alias and current_ok and inv>0)
                 else 'REVIEW_BEFORE_ANNUAL_AC',
             historical_occurrences=len(indices),historical_tasks=';'.join(sorted(set(sub.task))),
             original_task_keys_json=json.dumps(source_indices,separators=(',',':')),
             representative_task_key=str(primary.task_key),
             historical_min_annual_total_usd=float(pd.to_numeric(sub.annual_total_usd).min()),
             historical_min_annual_grid_import_kwh=float(pd.to_numeric(sub.grid_import_kwh).min()),
             historical_max_self_sufficiency_pct=float(pd.to_numeric(sub.self_sufficiency_of_demand_pct).max()),
             historical_equipment_annual_usd=float(primary.annual_equipment_usd),
             historical_annual_total_usd_for_primary=float(primary.annual_total_usd),
             archived_dispatch_horizon_h=8760, archived_AC_validated=False,
             new_manufacturer_SOC_reoptimized=False,new_full_year_AC_validated=False,
             evidence_caveats=';'.join(reasons)))
    eq=pd.DataFrame(rows).sort_values(['case','assumed_transformer_kva','historical_min_annual_total_usd','equipment_id']).reset_index(drop=True)
    group=registry.groupby(['case','kva'],dropna=False).agg(task_count=('task_key','size'),
       optimal_tasks=('status',lambda v:int((v=='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER').sum())),
       archived_infeasible=('status',lambda v:int((v=='INFEASIBLE_MODEL').sum()))).reset_index()
    counts=eq.groupby(['case','assumed_transformer_kva'],dropna=False).agg(
       distinct_hardware=('equipment_id','size'),
       eligible_for_fixed_hardware_runner=('existing_fixed_hardware_runner_eligible','sum'),
       needs_review=('candidate_gate',lambda x:int((x!='READY_FOR_NEW_MANUFACTURER_SOC_SOLVE').sum()))).reset_index()
    group=group.merge(counts,left_on=['case','kva'],right_on=['case','assumed_transformer_kva'],how='left').drop(columns=['assumed_transformer_kva'])
    summary={'archived_tasks':len(registry),'status_counts':registry.status.value_counts().to_dict(),
        'archived_optimal_tasks':int((registry.status=='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER').sum()),
        'distinct_fixed_hardware_across_12_cases_and_5_ratings':len(eq),
        'GIS_mapped_energy_only_designs':int(eq.case_alias.astype(bool).sum()),
        'ready_for_new_SOC_and_AC_work':int(eq.existing_fixed_hardware_runner_eligible.sum()),
        'unmapped_or_hardware_review_designs':int((~eq.existing_fixed_hardware_runner_eligible).sum()),
        'historical_infeasible_preserved':int((registry.status=='INFEASIBLE_MODEL').sum()),
        'hours_per_archived_energy_solve':8760,
        'notes':['Original annual MILP results are READ ONLY and are never rerun by the indexer.',
                 'Different original objective tasks may yield the same hardware; their task-level results remain intact.',
                 'Economic fixed-hardware redispatch is a NEW study under manufacturer SOC constraints.',
                 'No archival energy-only row is labelled AC-feasible. GIS is provisional.',
                 'Unmapped household cases and transformer nameplate sensitivities require separate evidence.']}
    return registry,eq,group,summary


def resume_rows(csv_path: Path) -> int:
    """Count a contiguous completed annual AC CSV prefix before resuming."""
    if not csv_path.exists():return 0
    df=pd.read_csv(csv_path)
    if len(df)>8760 or 'hour_index' not in df.columns:
        raise ValueError('Partial AC CSV is not an indexed hourly stream')
    if df.hour_index.tolist()!=list(range(len(df))):
        raise ValueError('Cannot resume a corrupt/nonsequential partial annual stream')
    return len(df)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--outdir',type=Path,required=True)
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve();src=repo/SOURCE;out=args.outdir.resolve()
    if out.exists():ap.error('Choose a new output directory. No overwriting archived analyses.')
    if not src.is_file():ap.error('Missing GitLab campaign: '+str(src))
    archived=pd.read_csv(src,low_memory=False)
    if not (repo/MANIFEST).is_file() or not (repo/RUN_PLAN).is_file():
        ap.error('Expected canonical run_plan.json and study_manifest.json beside the source')
    old=json.loads((repo/MANIFEST).read_text(encoding='utf8'))
    plan=json.loads((repo/RUN_PLAN).read_text(encoding='utf8'))
    if len(archived)!=int(old['results']) or len(archived)!=int(plan['total_distinct_solver_tasks']):
        raise ValueError('Canonical campaign size differs from source manifests')
    observed=archived.status.value_counts().to_dict()
    if observed!={str(k):int(v) for k,v in old['status_counts'].items()}:
        raise ValueError('Archived status counts disagree with the study manifest')
    registry,equipment,groups,summary=archive_to_tables(archived)
    out.mkdir(parents=True)
    registry.to_csv(out/'archived_task_registry.csv',index=False)
    equipment.to_csv(out/'all_distinct_equipment_candidates.csv',index=False)
    groups.to_csv(out/'original_campaign_by_case_and_rating.csv',index=False)
    summary.update({'source':str(SOURCE),'source_sha256':sha256(src),
                    'source_manifest_sha256':sha256(repo/MANIFEST),
                    'source_run_plan_sha256':sha256(repo/RUN_PLAN),
                    'old_results_preserved':True,'new_solver_runs':0,'new_AC_runs':0})
    (out/'campaign_reuse_manifest.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,indent=2))
    print('Audit/index written:',out)

if __name__=='__main__': main()
