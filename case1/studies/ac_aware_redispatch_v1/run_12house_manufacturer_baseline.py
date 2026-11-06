#!/usr/bin/env python3
"""Reoptimize saved 12-home 106039 hardware under manufacturer SOC constraints.

No investment sizing, AC feasibility or field certification is claimed.
Requires full local project checkout with PyPSA, HiGHS, and pandapower installed.
Writes a distinct output folder, never modifies archived reference results.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from run_pilot import imported, filter_territory, CASE_FOLDERS, CASE_HOUSE_IDS
from fixed_hardware import Hardware, solve_fixed, physical_soc_floor_usable_kwh
from validate_annual_ac import sha256, validate_trajectory

CASE='twelve'
TRAFO='106039'
EXPECTED_NODE='923494'


def verify_source_manifest(m: dict):
    if str(m['summary'].get('candidate_epm_node')) != EXPECTED_NODE:
        raise ValueError('Saved case is not the 106039/923494 territory')
    if m['summary'].get('profile_indices') != list(range(1,13)):
        raise ValueError('Saved twelve-house profile selection has changed')
    hw=Hardware.from_manifest(m)
    if hw.export_policy!='zero' or abs(hw.transformer_kva-5.)>1e-6:
        raise ValueError('The reference must be the saved 5 kVA zero-export sensitivity')
    return hw


def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--repo-root',type=Path,default=Path('.'))
    pa.add_argument('--outdir',type=Path,required=True)
    pa.add_argument('--manufacturer-min-soc',type=float,default=0.20)
    pa.add_argument('--daylight-q-ratio',type=float,default=0.25)
    pa.add_argument('--service-factor',type=float,default=1.0)
    args=pa.parse_args()
    if not .0<=args.manufacturer_min_soc<1 or not 0<=args.daylight_q_ratio<=1 or args.service_factor<1:
        pa.error('Invalid min SOC, Q ratio or service factor')
    repo=args.repo_root.resolve();out=args.outdir.resolve()
    if not (repo/'.git').exists():pa.error('Provide a full local GitLab repository root')
    if out.exists():pa.error('Output directory already exists; choose a new path')
    transformer, folder = CASE_FOLDERS[CASE]
    if transformer != TRAFO:raise ValueError('Internal reference mapping changed')
    saved=repo/'case1/studies/pypsa_joint_optimization_v1/outputs/full_study/shortlisted_hourly'/folder
    reference_manifest_file=saved/'model_manifest.json'
    ref=json.loads(reference_manifest_file.read_text(encoding='utf8'))
    hw=verify_source_manifest(ref)
    (read_data,infer_assignments,build_territory,Territory,build_net,
     critical_indices,run_hour,load_source)=imported(repo)
    houses,trafos,lv=read_data()
    assignments=infer_assignments(houses,trafos,lv,'base')
    terr=build_territory(TRAFO,houses,trafos,lv,assignments,args.service_factor)
    if terr is None:raise ValueError('No EPM-mapped LV graph for reference transformer')
    terr,exclusions=filter_territory(CASE,terr,Territory)
    if len(terr.attachments)!=12 or exclusions:
        raise ValueError('Unexpected GIS household selection; no implicit reassignment allowed')
    demand,pv_pu,ghi,src=load_source(repo,CASE)
    original=pd.read_csv(saved/'hourly_dispatch.csv',parse_dates=['timestamp_lst'])
    if len(original)!=8760 or not np.allclose(original.demand_kw.to_numpy(float),demand.to_numpy(float),rtol=0,atol=1e-4):
        raise ValueError('Saved annual reference demand differs from source input')
    if abs(float(original.inverter_ac_kw.max()))>hw.inverter_kva+1e-5:
        raise ValueError('Original trajectory exceeds selected inverter rating')
    # Whole-year PyPSA optimization with exactly fixed hardware and manufacturer SOC.
    annual,summary=solve_fixed(repo,hw,demand,pv_pu,
                    min_physical_soc=args.manufacturer_min_soc)
    annual.index.name='timestamp_lst'
    validate_trajectory(annual.reset_index(),demand,hw,args.manufacturer_min_soc,'fresh fixed-hardware solve')
    out.mkdir(parents=True,exist_ok=False)
    path=out/'fixed_hardware_manufacturer_soc_baseline.csv'
    annual.to_csv(path,float_format='%.9f')
    # Recheck serialized file because all subsequent validation uses CSV bytes.
    validate_trajectory(pd.read_csv(path),demand,hw,args.manufacturer_min_soc,path.name)
    metadata={
        'label':'CASE_12_MANUFACTURER_SOC_REOPTIMIZED_NOT_AC_CERTIFIED',
        'scenario':CASE,'transformer':TRAFO,'households':12,
        'reference_folder':str(saved.relative_to(repo)),
        'reference_manifest_sha256':sha256(reference_manifest_file),
        'source_input':str(src.relative_to(repo)),
        'source_input_sha256':sha256(src),
        'selected_candidate_houses':list(CASE_HOUSE_IDS[CASE]),
        'excluded_gis_candidate_houses':exclusions,
        'unresolved_alternative_houses':[],
        'gis_total_provisional_associations':len(terr.attachments),
        'household_specific_loads':'UNAVAILABLE; fixed-seed synthetic reference demand, equal allocation in AC network',
        'hardware':vars(hw),'manufacturer_battery_model':'Deye SE-G5.1 from saved HOMER inputs',
        'manufacturer_min_soc_fraction':float(args.manufacturer_min_soc),
        'battery_DOD_basis':'80 percent recommended DoD scenario, manufacturer evidence subject to hardware confirmation',
        'minimum_store_energy_kwh':physical_soc_floor_usable_kwh(hw.battery_modules,args.manufacturer_min_soc),
        'assumed_nameplate_kva':hw.transformer_kva,
        'nighttime_q_policy':'off','daylight_q_ratio':float(args.daylight_q_ratio),
        'service_factor':float(args.service_factor),'siting':'head','load_allocation':'equal',
        'gis_balanced_three_phase_proxy':True,'service_assignments':'PROVISIONAL',
        'perfect_foresight':True,'bat_soc_model':'existing PyPSA Store e_cyclic, 8760-hour fixed-hardware solve',
        'full_year_pypsa_energy_and_soc_reoptimized':True,
        'pv_bess_inverter_sizing_reoptimized':False,
        'reactive_device_losses_and_dc_link_drain':'NOT_MODELLED',
        'ac_losses_included_in_energy_objective':False,
        'ac_verified_full_year':False,
        'reference_saved_annual_total_usd':hw.annual_total_usd,
        'manufacturer_soc_baseline_annual_total_usd':float(summary['annual_total_usd']),
        'manufacturer_soc_increment_vs_saved_usd_per_year':float(summary['annual_total_usd']-hw.annual_total_usd),
        'manufacturer_soc_baseline_grid_import_kwh':float(summary['grid_import_kwh']),
        'manufacturer_soc_baseline_unserved_kwh':float(summary['unserved_kwh']),
        'source_trajectory_sha256':sha256(path),
        'source_git_revision':subprocess.run(['git','rev-parse','HEAD'],cwd=repo,
              capture_output=True,text=True).stdout.strip(),
        'interpretation':'PCC/energy-only optimization; no AC validation; 5 kVA is a research rating assumption'
    }
    (out/'pilot_manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    (out/'manufacturer_baseline_summary.json').write_text(json.dumps(summary,indent=2,default=str)+'\n',encoding='utf8')
    print('12-house manufacturer SOC reoptimization completed. AC FEASIBILITY NOT YET CHECKED.')
    print('Saved',path,'\n',json.dumps({k:metadata[k] for k in [
        'households','manufacturer_soc_baseline_annual_total_usd',
        'manufacturer_soc_baseline_grid_import_kwh','manufacturer_soc_baseline_unserved_kwh']},indent=2))


if __name__=='__main__':main()
