#!/usr/bin/env python3
"""One *necessary* full-year manufacturer-SOC solve for an archived hardware tuple.

The 6,840 historical investment optimizations are NOT re-run. This invokes
existing fixed_hardware.solve_fixed, not full_study.py. Can import a previously
completed manufacturer-SOC run if hardware, inputs and full-year energy balance
match. Never silently changes the archived PV/BESS/inverter choice.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pandas as pd
from audit_archived_campaign import CASE_TO_GIS, SOURCE, sha256
from fixed_hardware import Hardware, solve_fixed, physical_soc_floor_usable_kwh
from run_pilot import imported, CASE_HOUSE_IDS
from validate_annual_ac import validate_trajectory


def require_candidate(plan_dir: Path, candidate_id: str) -> tuple[dict,dict]:
    catalog=pd.read_csv(plan_dir/'all_distinct_equipment_candidates.csv',keep_default_na=False)
    found=catalog.loc[catalog.equipment_id==candidate_id]
    if len(found)!=1:raise ValueError('Candidate ID missing or ambiguous in complete archive index: '+candidate_id)
    row=found.iloc[0].to_dict()
    if str(row['existing_fixed_hardware_runner_eligible']).lower() not in ('true','1'):
        raise ValueError('Candidate needs separate evidence/hardware review: '+str(row['evidence_caveats']))
    if row['case'] not in CASE_TO_GIS: raise ValueError('No mapped GIS case for this archived household study')
    registry=pd.read_csv(plan_dir/'archived_task_registry.csv',low_memory=False)
    source=registry.loc[registry.task_key==row['representative_task_key']]
    if len(source)!=1 or str(source.iloc[0].equipment_id)!=candidate_id:
        raise ValueError('Original solver-task provenance is inconsistent')
    return row,source.iloc[0].to_dict()


def hardware_from_candidate(row:dict, source:dict, load_pf:float|None=None) -> Hardware:
    if row['case']!=source['case'] or abs(float(row['assumed_transformer_kva'])-float(source['kva']))>1e-5:
        raise ValueError('Source hardware mismatch')
    if str(source['export_policy'])!='zero':
        raise ValueError('AC case convention currently requires saved zero-export design')
    return Hardware(panels=int(row['pv_panels']),battery_modules=int(row['battery_modules']),
      battery_power_dc_kw=float(row['battery_power_dc_kw']),inverter_kva=float(row['inverter_kva']),
      transformer_kva=float(row['assumed_transformer_kva']),
      loading_pu=float(source['transformer_loading_screen_pu']),
      load_pf=float(load_pf if load_pf is not None else source.get('load_pf',0.98) or .98),
      export_policy=str(source['export_policy']),
      annual_equipment_usd=float(row['historical_equipment_annual_usd']),
      annual_total_usd=float(row['historical_annual_total_usd_for_primary']))


def candidate_source_checks(repo:Path, plan_dir:Path,source:dict)->None:
    p=repo/SOURCE
    plan=json.loads((plan_dir/'campaign_reuse_manifest.json').read_text(encoding='utf8'))
    if sha256(p)!=plan['source_sha256']:
        raise ValueError('Canonical saved solver results have changed since indexing; re-index first')
    if str(source['status'])!='OPTIMAL_ENERGY_SCREEN_ONLY_NO_AC_FEEDER':
        raise ValueError('Cannot reuse nonoptimal source task')


def reuse_verified_trajectory(path:Path, hw:Hardware,case:str, min_soc:float, demand, expected_src_hash:str):
    meta_path=path/'pilot_manifest.json'
    meta=json.loads(meta_path.read_text(encoding='utf8'))
    if meta.get('scenario')!=case or str(meta.get('nighttime_q_policy'))!='off':
        raise ValueError('Existing baseline has different case or reactive policy')
    if (abs(float(meta.get('daylight_q_ratio',-1))-.25)>1e-8 or
        abs(float(meta.get('service_factor',1))-1)>1e-8 or
        meta.get('siting','head')!='head' or meta.get('load_allocation','equal')!='equal'):
        raise ValueError('Existing baseline has different daylight Q, siting or service assumptions')
    if abs(float(meta['manufacturer_min_soc_fraction'])-min_soc)>1e-8:
        raise ValueError('Existing SOC minimum is different')
    if meta.get('source_input_sha256') and meta['source_input_sha256']!=expected_src_hash:
        raise ValueError('Existing manufacturer baseline used another source input')
    for k,v in asdict(hw).items():
        if k not in meta['hardware'] or (isinstance(v,(int,float)) and abs(float(meta['hardware'][k])-float(v))>1e-5) or (isinstance(v,str) and str(meta['hardware'][k])!=v):
            raise ValueError('Existing baseline hardware/PF differs at '+k)
    fn=path/'fixed_hardware_manufacturer_soc_baseline.csv'
    if meta.get('source_trajectory_sha256') and sha256(fn)!=meta['source_trajectory_sha256']:
        raise ValueError('Existing baseline trajectory does not match its manifest')
    annual=pd.read_csv(fn)
    validate_trajectory(annual,demand,hw,min_soc,'reused existing manufacturer-SOC baseline')
    return fn,meta_path,annual


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--plan-dir',type=Path,required=True)
    ap.add_argument('--candidate-id',required=True)
    ap.add_argument('--out-root',type=Path,required=True)
    ap.add_argument('--min-soc',type=float,default=.20)
    ap.add_argument('--load-pf',type=float,default=None,
                    help='Default is the archived PF 0.98; a different PF is a NEW dispatch study')
    ap.add_argument('--reuse-existing-baseline',type=Path,
                    help='Optional previously completed manufacturer-SOC pilot; validates all 8760h before copying')
    args=ap.parse_args(argv)
    if not 0<=args.min_soc<1:ap.error('Invalid physical min SOC')
    repo=args.repo_root.resolve();plan=args.plan_dir.resolve();out_root=args.out_root.resolve()
    row,source=require_candidate(plan,args.candidate_id)
    candidate_source_checks(repo,plan,source)
    hw=hardware_from_candidate(row,source,args.load_pf)
    if not 0<hw.load_pf<=1:raise ValueError('PF must be in (0,1]')
    case=CASE_TO_GIS[row['case']][0]
    study_key=args.candidate_id if args.load_pf is None else f'{args.candidate_id}_pf{hw.load_pf:.3f}'
    out=out_root/study_key
    if out.exists():ap.error('Result directory already exists; check existing results first: '+str(out))
    if not (repo/'.git').exists():ap.error('Use a full local GitLab checkout')
    load_source=imported(repo)[-1]
    demand,pv_pu,ghi,source_input=load_source(repo,case)
    if len(demand)!=8760:raise ValueError('Full-year source input missing')
    archived_input_hash=str(source.get('source_sha256',''))
    input_hash=sha256(source_input)
    if archived_input_hash and archived_input_hash!='nan' and archived_input_hash!=input_hash:
        raise ValueError('Historical optimization input SHA differs from current repository input')
    if args.reuse_existing_baseline:
        old_file,old_meta,annual=reuse_verified_trajectory(args.reuse_existing_baseline.resolve(),hw,case,args.min_soc,demand,input_hash)
        summary={'status':'VERIFIED_REUSED_MANUFACTURER_SOC_TRAJECTORY',
                 'annual_total_usd':float(json.loads(old_meta.read_text()).get('manufacturer_soc_baseline_annual_total_usd',float('nan'))),
                 'grid_import_kwh':float(annual.grid_import_kw.sum()),
                 'unserved_kwh':float(annual.unserved_kw.sum())}
        if not np.isfinite(summary['annual_total_usd']):
            old_s=old_file.parent/'manufacturer_baseline_summary.json'
            if old_s.exists(): summary.update(json.loads(old_s.read_text()))
        if not np.isfinite(summary['annual_total_usd']):
            raise ValueError('Reused baseline lacks an audited annual cost; do not invent economics')
    else:
        annual,summary=solve_fixed(repo,hw,demand,pv_pu,min_physical_soc=args.min_soc)
        annual.index.name='timestamp_lst'
        validate_trajectory(annual.reset_index(),demand,hw,args.min_soc,'fresh manufacturer baseline')
    # Only after a verified full-year trajectory may a new study folder be created.
    out.mkdir(parents=True,exist_ok=False)
    dst=out/'fixed_hardware_manufacturer_soc_baseline.csv'
    if args.reuse_existing_baseline:
        shutil.copy2(old_file,dst)
    else:
        annual.to_csv(dst,float_format='%.9f')
    validate_trajectory(pd.read_csv(dst),demand,hw,args.min_soc,'stored manufacturer baseline')
    geo,trafo=CASE_TO_GIS[row['case']]
    meta={
      'label':'ARCHIVED_EQUIPMENT_REUSED_NEW_MANUFACTURER_SOC_BASELINE_NOT_AC_VALIDATED',
      'candidate_id':args.candidate_id,'scenario':geo,'original_archived_case':row['case'],
      'transformer':trafo,'households':len(CASE_HOUSE_IDS[geo]),
      'selected_candidate_houses':list(CASE_HOUSE_IDS[geo]),
      'hardware':asdict(hw),'assumed_nameplate_kva':hw.transformer_kva,
      'transformer_rating_evidence':str(row['transformer_evidence']),
      'manufacturer_min_soc_fraction':args.min_soc,
      'minimum_store_energy_kwh':physical_soc_floor_usable_kwh(hw.battery_modules,args.min_soc),
      'manufacturer_battery_model':'Deye SE-G5.1, historical model',
      'source_input':str(source_input.relative_to(repo)),
      'source_input_sha256':input_hash,
      'source_campaign_sha256':sha256(repo/SOURCE),
      'source_campaign_manifest_sha256':sha256(plan/'campaign_reuse_manifest.json'),
      'archived_solver_task_keys_json':str(row['original_task_keys_json']),
      'archived_representative_task_key':str(row['representative_task_key']),
      'historic_cost_is_energy_only':True,
      'manufacturer_soc_baseline_annual_total_usd':float(summary['annual_total_usd']),
      'manufacturer_soc_baseline_grid_import_kwh':float(summary['grid_import_kwh']),
      'manufacturer_soc_baseline_unserved_kwh':float(summary['unserved_kwh']),
      'nighttime_q_policy':'off','daylight_q_ratio':.25,'service_factor':1.,
      'siting':'head','load_allocation':'equal',
      'gis_balanced_three_phase_proxy':True,'service_assignments':'PROVISIONAL',
      'perfect_foresight':True,
      'full_year_pypsa_energy_and_soc_reoptimized':not bool(args.reuse_existing_baseline),
      'reused_verified_full_year_trajectory':bool(args.reuse_existing_baseline),
      'pv_bess_inverter_sizing_reoptimized':False,
      'ac_losses_included_in_energy_objective':False,
      'source_trajectory_sha256':sha256(dst),
      'source_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True).stdout.strip(),
      'ac_verified_full_year':False,
      'interpretation':'NEW fixed-hardware economic dispatch with manufacturer SOC, NOT original 6840 investment MILP rerun; no field AC certification.'}
    if args.reuse_existing_baseline:
        meta['reused_original_pilot_manifest_sha256']=sha256(old_meta)
    (out/'pilot_manifest.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n',encoding='utf8')
    (out/'manufacturer_baseline_summary.json').write_text(json.dumps(summary,indent=2,default=str,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({'candidate_id':args.candidate_id,'folder':str(out),'reused':bool(args.reuse_existing_baseline),
      'annual_total_usd':summary['annual_total_usd'],'grid_import_kwh':summary['grid_import_kwh'],
      'next_step':'FULL_YEAR_PANDAPOWER_AC_REQUIRED'},indent=2))

if __name__=='__main__': main()
