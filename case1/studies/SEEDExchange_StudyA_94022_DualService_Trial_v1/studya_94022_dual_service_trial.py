#!/usr/bin/env python3
"""Read-only A0 94022 paired H01/H06 assumed-service and mapped-LV R sensitivity.

Purely an electrical what-if screen. Uses previous signed source comparisons and
user-local pandapower. Does not change dispatch, hardware or original results.
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

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'inputs' / 'StudyA_94022_Sparse_Bundle_Trial_v1_Results.zip'
SOURCE_SHA256 = '7c6f9921b83060b83f564e654dbb7f5e381f71002a343f26d3b0f4cdbd9fb0f7'
PRIOR_SCRIPT = Path('case1/studies/SEEDExchange_StudyA_94022_Sparse_Bundle_v1/studya_94022_sparse_bundle_trial.py')
DEFAULT_TRIAL = Path('StudyA_A0_94022_Sequenced_Trial_v1')
KEY = ['case','dispatch','pf','length_factor','timestamp_lst','option']
NUM = ['minimum_voltage_pu','maximum_voltage_pu','transformer_loading_pct','line_loading_pct']

# IDs refer to electrical-model edges, not independently verified cable assets.
# 007 = modelled H01 service (326.55 m), 004 = modelled H06 service (315.27 m).
# Other indices represent tapped pieces of EPM mapped LV spans.
OPTIONS = {
    'head_reference': [],
    'svc007_gis014_011_R050': [7,14,11],            # previous 70/72 control
    'svc007_gis_top9_R050': [7,14,11,16,18,21,22,17,15,19],  # previous 70/72 control
    'service_only_R050': 'ALL_SERVICE',
    'GIS_only_R050': 'ALL_GIS',
    'all_LV_R050': 'ALL_LV',                     # previous 72/72 control
    'svc004_R050': [4],
    'svc007_004_R050': [7,4],
    'svc007_004_gis011_R050': [7,4,11],
    'svc007_004_gis014_R050': [7,4,14],
    'svc007_004_gis014_011_R050': [7,4,14,11],
    'svc007_004_gis014_011_016_R050': [7,4,14,11,16],
    'svc007_004_gis014_011_016_018_R050': [7,4,14,11,16,18],
    'svc007_004_gis_top9_R050': [7,4,14,11,16,18,21,22,17,15,19],
    'svc004_gis014_011_R050': [4,14,11],
    'svc004_gis_top9_R050': [4,14,11,16,18,21,22,17,15,19],
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_source(path:Path=SOURCE):
    if not path.is_file():
        raise FileNotFoundError(f'Previous sparse-bundle source missing: {path}')
    if sha(path) != SOURCE_SHA256:
        raise ValueError('Uploaded sparse-bundle source checksum does not match vetted copy')
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            raise ValueError('Source ZIP CRC mismatch')
        rows = pd.read_csv(io.BytesIO(z.read('BUNDLE_AC_72_SCENARIOS_EACH.csv')))
        summary = pd.read_csv(io.BytesIO(z.read('BUNDLE_OPTION_SUMMARY.csv')))
        branches = pd.read_csv(io.BytesIO(z.read('MODEL_BRANCH_ENDPOINTS.csv')))
        manifest = json.loads(z.read('BUNDLE_MANIFEST.json'))
    if len(rows) != 1080 or len(summary) != 15 or len(branches) != 26:
        raise ValueError('Unexpected prior evidence size')
    if manifest.get('status') != 'TARGETED_SPARSE_BRANCH_BUNDLES_ONLY' or manifest.get('annual_AC_8760_verified') is not False:
        raise ValueError('Unexpected source manifest meaning')
    if rows.status.ne('CONVERGED').any() or rows.duplicated(KEY).any():
        raise ValueError('Source AC data invalid')
    if not rows[NUM].apply(np.isfinite).all().all():
        raise ValueError('Source AC numerical values invalid')
    audit = feasible(rows)
    if not (audit == rows.ac_feasible).all():
        raise ValueError('Source AC feasibility flags inconsistent with measured values')
    if len(set(branches.line_index)) != 26 or (branches.to_model_bus.isna().any()):
        raise ValueError('Incomplete source branch endpoints')
    h01 = branches.loc[branches.line_index.eq(7)].iloc[0]
    h06 = branches.loc[branches.line_index.eq(4)].iloc[0]
    if not (h01.to_model_bus == 'HOUSE_H01' and h06.to_model_bus == 'HOUSE_H06' and
            h01.kind == 'ASSUMED_SERVICE' and h06.kind == 'ASSUMED_SERVICE'):
        raise ValueError('H01/H06 service edge mapping does not match source model')
    assert len(OPTIONS) == 16
    return rows, summary, branches, manifest


def feasible(df:pd.DataFrame) -> pd.Series:
    return (df.minimum_voltage_pu >= .95) & (df.maximum_voltage_pu <= 1.05) & (
            df.transformer_loading_pct <= 100.) & (df.line_loading_pct <= 100.) & df.status.eq('CONVERGED')


def compare_controls(current: pd.DataFrame, previous: pd.DataFrame):
    common = sorted(set(current.option).intersection(set(previous.option)))
    required = {'head_reference', 'svc007_gis014_011_R050', 'svc007_gis_top9_R050',
                'GIS_only_R050', 'service_only_R050', 'all_LV_R050'}
    if not required.issubset(common):
        raise ValueError('Required historical network controls omitted')
    a=current[current.option.isin(common)].sort_values(KEY).reset_index(drop=True)
    b=previous[previous.option.isin(common)].sort_values(KEY).reset_index(drop=True)
    if len(a)!=len(b) or not a[KEY].equals(b[KEY]):
        raise ValueError('Historical source/control scenario keys do not match')
    if not np.allclose(a[NUM],b[NUM],rtol=0,atol=2e-4):
        raise ValueError('Source/control powerflow mismatch')
    if not a.ac_feasible.equals(b.ac_feasible):
        raise ValueError('Source/control AC feasibility mismatch')
    return len(a),common,float(np.abs(a[NUM].to_numpy()-b[NUM].to_numpy()).max())


def validate_output(rows,source_rows,branches,summary):
    if len(rows)!=72*len(OPTIONS) or rows.option.nunique()!=len(OPTIONS):
        raise ValueError('Missing paired-service AC results')
    if rows.duplicated(KEY).any() or rows.status.ne('CONVERGED').any():
        raise ValueError('Duplicate/unconverged AC result')
    if not rows[NUM].apply(np.isfinite).all().all():
        raise ValueError('Nonfinite AC result')
    if not feasible(rows).equals(rows.ac_feasible):
        raise ValueError('AC result threshold flags inconsistent')
    for key,g in rows.groupby('option'):
        if len(g)!=72 or len(g[['case','dispatch','pf','length_factor','timestamp_lst']].drop_duplicates())!=72:
            raise ValueError(f'Incomplete factor/time coverage for {key}')
    nc, controls, maxdiff = compare_controls(rows,source_rows)
    for _,r in summary.iterrows():
        g=rows[rows.option.eq(r.option)]
        if len(g)!=72 or int(g.ac_feasible.sum()) != int(r.passing):
            raise ValueError(f'Invalid group summary: {r.option}')
    return nc, controls, maxdiff


def load_previous_module(repo:Path):
    path=repo/PRIOR_SCRIPT
    if not path.is_file():
        raise FileNotFoundError('Extract SEEDExchange_StudyA_94022_Sparse_Bundle_v1 under case1/studies: '+str(path))
    spec=importlib.util.spec_from_file_location('studyA_94022_prior_sparse',path)
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


def run(repo:Path,trial:Path,out:Path):
    if out.exists():
        raise FileExistsError('Refusing to overwrite existing output: '+str(out))
    src,_,branches,src_manifest=read_source()
    old=load_previous_module(repo)
    if not trial.is_dir():
        raise FileNotFoundError('A0 94022 partial annual trial folder not found: '+str(trial))
    old.BRANCH_OPTIONS=OPTIONS
    if not (repo/old.ORIGINAL).is_file():
        raise FileNotFoundError('Prior branch-isolation model script missing')
    old_manifest,old_rows,reg=old.source_data()
    if len(old_rows)!=2160:
        raise ValueError('Source branch-isolation AC evidence incomplete')
    old.verify_lines(reg, branches)
    options=old.proposed_options(reg)
    if len(options)!=len(OPTIONS):raise ValueError('Option parsing incomplete')
    with tempfile.TemporaryDirectory(prefix='studyA_dual_service_',dir=out.parent) as d:
        p=Path(d)/'ac_outputs.zip'
        old.run(repo,trial,p)
        with zipfile.ZipFile(p) as z:
            if z.testzip():raise ValueError('New powerflow evidence CRC mismatch')
            rows=pd.read_csv(io.BytesIO(z.read('BUNDLE_AC_72_SCENARIOS_EACH.csv')))
            summ=pd.read_csv(io.BytesIO(z.read('BUNDLE_OPTION_SUMMARY.csv')))
            members=pd.read_csv(io.BytesIO(z.read('BUNDLE_BRANCH_MEMBERSHIP.csv')))
            endpoints=pd.read_csv(io.BytesIO(z.read('MODEL_BRANCH_ENDPOINTS.csv')))
        n,common,err=validate_output(rows,src,branches,summ)
        endpoints=endpoints.sort_values('line_index').reset_index(drop=True)
        branch_ref=branches.sort_values('line_index').reset_index(drop=True)
        cols=['line_index','line_name','kind','from_model_bus','to_model_bus']
        if not endpoints[cols].equals(branch_ref[cols]):
            raise ValueError('Network endpoint IDs changed from audited prior version')
        numeric=['length_m','r_ohm_per_km','x_ohm_per_km','max_i_ka']
        if not np.allclose(endpoints[numeric],branch_ref[numeric],rtol=1e-9,atol=2e-4):
            raise ValueError('Network branch electrical parameters/lengths changed from audit')
        # Added sorted rank is descriptive. Affected model edge length is not cost.
        s=summ.sort_values(['failing','changed_branch_count','affected_original_length_m','option']).reset_index(drop=True)
        status='TARGETED_DUAL_SERVICE_SENSITIVITY_NOT_ANNUAL'
        manifest={
            'status':status,'source_sparse_sha256':SOURCE_SHA256,
            'source_branch_sha256':src_manifest['source_branch_results_sha256'],
            'prior_trial_manifest_sha256':src_manifest['source_trial_manifest_sha256'],
            'source_controls_recalculated':common,'source_control_rows_compared':n,
            'source_control_max_abs_error':err,
            'all_powerflows_converged':True,
            'scenarios':len(rows),'options':len(OPTIONS),'case_dispatch_groups':4,
            'selected_timestamps':9,'pf_length_pairs':[[.98,1.0],[.95,1.6]],
            'annual_8760_AC_verified':False,'source_files_modified':False,
            'passing_sparse_options':s[(s.passing==72)&(s.changed_branch_count<26)].option.tolist(),
            'notes':'R*0.5 changes modelled resistance only. Service geometry, actual conductors, ampacity and costs unverified. Design-hour snapshots do not establish full-year compliance.'
        }
        with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('DUAL_SERVICE_AC_72_CASES_EACH.csv',rows.to_csv(index=False))
            z.writestr('DUAL_SERVICE_OPTIONS_RANKED.csv',s.to_csv(index=False))
            z.writestr('DUAL_SERVICE_BRANCH_MEMBERSHIP.csv',members.to_csv(index=False))
            z.writestr('DUAL_SERVICE_MODEL_BRANCH_ENDPOINTS.csv',endpoints.to_csv(index=False))
            z.writestr('DUAL_SERVICE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':status,'ac_cases':len(rows),'previous_controls_rechecked':n,
                      'passing_sparse_options':manifest['passing_sparse_options'], 'out':str(out)},indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--trial-dir',type=Path,default=DEFAULT_TRIAL)
    p.add_argument('--out',type=Path,default=Path('StudyA_94022_DualService_Trial_v1_Results.zip'))
    p.add_argument('--preflight',action='store_true')
    args=p.parse_args()
    src,_,branches,_=read_source()
    repo=args.repo_root.resolve()
    old=load_previous_module(repo)
    old.BRANCH_OPTIONS=OPTIONS
    old.source_data()  # prior 2160-row source is cryptographically checked here
    if args.preflight:
        print(json.dumps({'status':'DUAL_SERVICE_PREFLIGHT_PASS',
              'source_rows':len(src),'expected_trial_ac_cases':72*len(OPTIONS),
              'source_checksum':SOURCE_SHA256,
              'H01_service_m':float(branches.loc[branches.line_index.eq(7),'length_m'].iloc[0]),
              'H06_service_m':float(branches.loc[branches.line_index.eq(4),'length_m'].iloc[0]),
              'prior_trial_exists':args.trial_dir.resolve().is_dir(),
              'prior_model_script_exists':(repo/old.ORIGINAL).is_file()},indent=2))
        if not args.trial_dir.resolve().is_dir() or not (repo/old.ORIGINAL).is_file():
            raise FileNotFoundError('Previous trial folder / original branch screen not installed')
        return
    run(repo,args.trial_dir.resolve(),args.out.resolve())

if __name__=='__main__':main()
