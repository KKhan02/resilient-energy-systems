#!/usr/bin/env python3
"""Targeted A0 94022 sparse R-factor branch combinations, read-only source replay.

No changes to signed PyPSA/pandapower outputs. All branch R×0.5 edits are
mathematical sensitivities, NOT manufacturer-sized conductor upgrades.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'inputs'/'StudyA_94022_Branch_Isolation_v1_Results.zip'
EXPECTED_SOURCE_SHA='7b89a8c859cc26c661498d81882baa11fa839d75d4c4cca924014dc47385bad1'
ORIGINAL=Path('case1/studies/SEEDExchange_StudyA_94022_Branch_Isolation_v1/probe_94022_branch_isolation.py')
TRIAL=Path('StudyA_A0_94022_Sequenced_Trial_v1')

# SOURCE-DRIVEN CHOICES: indexes are exact line IDs in the audited 94022 register.
# 007 is a long assumed service branch; other selected IDs are mapped EPM LV edges.
# Group order is cumulative and may NOT be interpreted as a cable-cost ranking.
BRANCH_OPTIONS={
  'head_reference':[],
  'service_007_R050':[7],
  'gis_014_R050':[14],
  'gis_014_011_R050':[14,11],
  'svc007_gis014_R050':[7,14],
  'svc007_gis014_011_R050':[7,14,11],
  'svc007_gis014_011_016_R050':[7,14,11,16],
  'svc007_gis_top4_R050':[7,14,11,16,18],
  'svc007_gis_top5_R050':[7,14,11,16,18,21],
  'svc007_gis_top6_R050':[7,14,11,16,18,21,22],
  'svc007_gis_top9_R050':[7,14,11,16,18,21,22,17,15,19],
  'gis_top7_R050':[14,11,16,18,21,22,17],
  'GIS_only_R050':'ALL_GIS',
  'service_only_R050':'ALL_SERVICE',
  'all_LV_R050':'ALL_LV',
}


def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()

def source_data(path:Path=INPUT):
    if not path.is_file():raise FileNotFoundError(path)
    if sha(path.read_bytes())!=EXPECTED_SOURCE_SHA:
        raise ValueError('Uploaded branch-isolation source checksum mismatch')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Branch-isolation source corrupt')
        manifest=json.loads(z.read('BRANCH_SCREEN_MANIFEST.json'))
        rows=pd.read_csv(io.BytesIO(z.read('BRANCH_SCREEN_AC_HOURLY.csv')))
        reg=pd.read_csv(io.BytesIO(z.read('94022_LV_BRANCH_REGISTER.csv')))
    if not(manifest.get('status')=='BRANCH_ISOLATION_TARGETED_ONLY' and
           manifest.get('rows')==2160 and len(rows)==2160 and len(reg)==26):
        raise ValueError('Unexpected branch-screen dimensions/status')
    if len(set(reg.line_index))!=26:raise ValueError('Duplicate branch indices')
    if rows.status.ne('CONVERGED').any():raise ValueError('Source has unconverged AC')
    opts=rows.option.unique()
    if len(opts)!=30:raise ValueError('Expected 30 original branch options')
    key=['case','dispatch','pf','length_factor','timestamp_lst','option']
    if rows.duplicated(key).any():raise ValueError('Duplicate source AC key')
    # H01 is limiting for the reference network, but alternative networks may
    # legitimately move the limiting household elsewhere.
    if set(rows.loc[rows.option.eq('head_reference'),'limiting_house'])!={'H01'}:
        raise ValueError('Unexpected reference limiting house; review model')
    return manifest,rows,reg


def proposed_options(reg:pd.DataFrame):
    indexes=set(reg.line_index.astype(int))
    groups={}
    for label,selected in BRANCH_OPTIONS.items():
        if selected=='ALL_GIS':selected=reg.loc[reg.kind.eq('EPM_GIS_LV'),'line_index'].astype(int).tolist()
        elif selected=='ALL_SERVICE':selected=reg.loc[reg.kind.eq('ASSUMED_SERVICE'),'line_index'].astype(int).tolist()
        elif selected=='ALL_LV':selected=sorted(indexes)
        selected=list(selected)
        if not selected or label=='head_reference':
            if label!='head_reference' or selected:raise ValueError('Invalid empty option')
        if len(selected)!=len(set(selected)) or not set(selected)<=indexes:
            raise ValueError('Invalid option branch indexes: '+label)
        groups[label]=selected
    return groups


def verify_lines(expected:pd.DataFrame,actual:pd.DataFrame):
    x=expected.sort_values('line_index').reset_index(drop=True)
    y=actual.sort_values('line_index').reset_index(drop=True)
    if not x[['line_index','line_name','kind']].equals(y[['line_index','line_name','kind']]):
        raise ValueError('Model line index/name/type no longer matches uploaded signed sensitivity')
    # x can have reference service lengths, whereas actual service lengths change by factor.
    if not np.allclose(x[['r_ohm_per_km','x_ohm_per_km','max_i_ka']],
                       y[['r_ohm_per_km','x_ohm_per_km','max_i_ka']],rtol=1e-9,atol=1e-10):
        raise ValueError('Model conductor parameters differ from earlier network screening')


def audited_comparison(current:pd.DataFrame,original:pd.DataFrame):
    key=['case','dispatch','pf','length_factor','timestamp_lst','option']
    common=set(current.option).intersection(set(original.option))
    a=current.loc[current.option.isin(common)].sort_values(key).reset_index(drop=True)
    b=original.loc[original.option.isin(common)].sort_values(key).reset_index(drop=True)
    if len(a)!=len(b) or not a[key].equals(b[key]):
        raise ValueError('Earlier branch option keys do not match re-solved cases')
    columns=['minimum_voltage_pu','maximum_voltage_pu','transformer_loading_pct','line_loading_pct']
    if not np.allclose(a[columns],b[columns],rtol=0,atol=2e-4):
        raise ValueError('Re-solved baseline/controls differ materially from uploaded branch sensitivity')
    if not a.ac_feasible.equals(b.ac_feasible):
        raise ValueError('Re-solved original option feasibility changed')
    return int(len(a)),sorted(common)


def run(repo:Path,trial:Path,out:Path):
    if out.exists():raise FileExistsError('Refusing to overwrite '+str(out))
    manifest,original,reg=source_data()
    script=repo/ORIGINAL
    if not script.is_file():raise FileNotFoundError('Please extract original Branch Isolation v1 package under case1/studies: '+str(script))
    if not trial.is_dir():raise FileNotFoundError('Prior A0 94022 trial not found: '+str(trial))
    spec=importlib.util.spec_from_file_location('studyA_94022_branch_original',script)
    base=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=base
    spec.loader.exec_module(base)
    bundles=proposed_options(reg)
    original_line_metadata=base.line_metadata
    def audit_line_metadata(net,meta):
        actual=original_line_metadata(net,meta)
        verify_lines(reg,actual)
        actual=actual.copy()
        actual['from_model_bus']=actual.line_index.map(
            lambda i:str(net.bus.at[int(net.line.at[int(i),'from_bus']),'name']))
        actual['to_model_bus']=actual.line_index.map(
            lambda i:str(net.bus.at[int(net.line.at[int(i),'to_bus']),'name']))
        return actual
    base.line_metadata=audit_line_metadata
    base.options=lambda actual:proposed_options(actual)
    source_probe=base.PROBE_DEFAULT
    if not source_probe.is_file():
        raise FileNotFoundError('Original source probe missing: '+str(source_probe))
    with tempfile.TemporaryDirectory(prefix='studyA_94022_bundle_',dir=out.parent) as d:
        temp=Path(d)/'branch_bundle_tmp.zip'
        base.run(repo,trial,source_probe,temp)
        with zipfile.ZipFile(temp) as z:
            if z.testzip():raise ValueError('New source AC ZIP CRC failure')
            data=pd.read_csv(io.BytesIO(z.read('BRANCH_SCREEN_AC_HOURLY.csv')))
            base_manifest=json.loads(z.read('BRANCH_SCREEN_MANIFEST.json'))
            endpoint_catalog=pd.read_csv(io.BytesIO(z.read('94022_LV_BRANCH_REGISTER.csv')))
        n_common,common=audited_comparison(data,original)
        if 'from_model_bus' not in endpoint_catalog or 'to_model_bus' not in endpoint_catalog:
            raise ValueError('Model bus end-point mapping missing')
        expected=72*len(bundles)
        if len(data)!=expected or data.duplicated(['case','dispatch','pf','length_factor','timestamp_lst','option']).any():
            raise ValueError('New AC rows missing/duplicated')
        if data.status.ne('CONVERGED').any() or data[['minimum_voltage_pu','maximum_voltage_pu','transformer_loading_pct','line_loading_pct']].isna().any().any():
            raise ValueError('Invalid new AC calculation')
        group=[]; members=[]
        for label,ids in bundles.items():
            g=data[data.option.eq(label)]
            if len(g)!=72:raise ValueError('Incomplete option '+label)
            lengths=reg.set_index('line_index').loc[ids,'length_m'].sum() if ids else 0
            for idx in ids:
                r=reg.set_index('line_index').loc[idx]
                zrow=endpoint_catalog.set_index('line_index').loc[idx]
                members.append(dict(option=label,line_index=idx,kind=r.kind,line_name=r.line_name,
                                    from_model_bus=zrow.from_model_bus,to_model_bus=zrow.to_model_bus,
                                    original_length_m=r.length_m,original_r_ohm_per_km=r.r_ohm_per_km))
            group.append(dict(option=label,changed_branch_count=len(ids),affected_original_length_m=round(lengths,2),
                passing=int(g.ac_feasible.sum()),failing=int((~g.ac_feasible).sum()),
                minimum_voltage_pu=float(g.minimum_voltage_pu.min()),maximum_voltage_pu=float(g.maximum_voltage_pu.max()),
                peak_transformer_pct=float(g.transformer_loading_pct.max()),
                peak_line_pct=float(g.line_loading_pct.max())))
        result=pd.DataFrame(group)
        if int(result.loc[result.option.eq('head_reference'),'passing'].iloc[0])!=28:
            raise ValueError('Reference 28/72 unexpectedly changed')
        if int(result.loc[result.option.eq('all_LV_R050'),'passing'].iloc[0])!=72:
            raise ValueError('All-LV benchmark 72/72 unexpectedly changed')
        manifest_out=dict(status='TARGETED_SPARSE_BRANCH_BUNDLES_ONLY',
            source_branch_results_sha256=EXPECTED_SOURCE_SHA,
            source_probe_sha256=base_manifest.get('source_probe_sha256'),
            source_trial_manifest_sha256=base_manifest.get('source_trial_manifest_sha256'),
            annual_AC_8760_verified=False,source_files_modified=False,
            factors=base.FACTORS,designed_timestamps=9,design_dispatch_groups=4,
            options=len(bundles),ac_rows=len(data),reconciled_to_source_rows=n_common,
            reconciled_source_options=common,
            note='Line R×0.5 is a proxy only; not a cable quotation, manufacturer rating, changed routing, or 8760h validation. Affected length is neither cost nor total installed cable length.')
        with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('BUNDLE_AC_72_SCENARIOS_EACH.csv',data.to_csv(index=False))
            z.writestr('BUNDLE_OPTION_SUMMARY.csv',result.to_csv(index=False))
            z.writestr('BUNDLE_BRANCH_MEMBERSHIP.csv',pd.DataFrame(members).to_csv(index=False))
            z.writestr('MODEL_BRANCH_ENDPOINTS.csv',endpoint_catalog.to_csv(index=False))
            z.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest_out,indent=2)+'\n')
    print(json.dumps({'status':manifest_out['status'],'rows':len(data),
                      'complete_bundles':result.loc[result.passing.eq(72),'option'].tolist(),
                      'out':str(out)},indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--trial-dir',type=Path,default=TRIAL)
    p.add_argument('--out',type=Path,default=Path('StudyA_94022_Sparse_Bundle_Trial_v1_Results.zip'))
    p.add_argument('--preflight',action='store_true')
    args=p.parse_args()
    src,rows,reg=source_data()
    groups=proposed_options(reg)
    repo=args.repo_root.resolve();trial=args.trial_dir.resolve()
    if args.preflight:
        print(json.dumps({'status':'SPARSE_BUNDLE_PREFLIGHT','branch_screen_sha256':EXPECTED_SOURCE_SHA,
            'options':len(groups),'targeted_ac_rows':len(groups)*72,
            'source_rows':len(rows),'source_branch_count':len(reg),
            'previous_script_exists':(repo/ORIGINAL).is_file(),
            'prior_trial_exists':trial.is_dir()},indent=2))
        if not (repo/ORIGINAL).is_file() or not trial.is_dir():raise FileNotFoundError('Required previous script/trial is missing')
        return
    run(repo,trial,args.out.resolve())

if __name__=='__main__':main()
