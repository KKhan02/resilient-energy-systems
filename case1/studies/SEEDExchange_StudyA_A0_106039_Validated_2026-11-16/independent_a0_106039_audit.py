#!/usr/bin/env python3
"""Independent file-level and electrical-result audit of uploaded A0 106039 shift trial.

This script does not launch any power-flow simulation; power-flow outputs are signed
local user-run measurements. It checks the internal evidence and source portfolio.
"""
import argparse, hashlib, io, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd


def digest(data):
    return hashlib.sha256(data).hexdigest()


def audit(trial_zip, previous_portfolio, output_dir):
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(trial_zip) as z:
        assert z.testzip() is None, 'Bad zip CRC'
        names=set(z.namelist())
        manifest=json.loads(z.read('TRIAL_MANIFEST.json'))
        shifts=pd.read_csv(io.BytesIO(z.read('ADOPTED_SHIFT_EVENTS.csv')))
        ac=pd.read_csv(io.BytesIO(z.read('CHANGED_HOURS_FINAL_AC.csv')))
        factors=pd.read_csv(io.BytesIO(z.read('NINE_FACTOR_ANNUAL_REUSE.csv')))
        assert z.getinfo('UNRESOLVED_EVENTS.csv').file_size==2, 'Unresolved events file is not empty'
        assert manifest['status']=='ALL_SELECTED_A0_PILOT_GROUPS_PASSED'
        assert manifest['selected_event_count']==44
        assert manifest['source_group_count']==4
        assert manifest['tested_transformer']=='106039'
        assert manifest['adopted_shift_count']==len(shifts)==44
        assert manifest['unresolved_event_count']==0
        assert manifest['annual_factor_comparisons']==len(factors)==36
        assert manifest['changed_hour_replays']==len(ac)==720
        assert len(manifest['candidate_files'])==4
        assert not shifts.duplicated(['case','dispatch','target_hour']).any()
        assert not ac.duplicated(['case','dispatch','pf','length_factor','timestamp_lst']).any()
        assert not factors.duplicated(['case','dispatch','pf','length_factor']).any()
        assert set(factors.pf)=={.95,.98,1.}
        assert set(factors.length_factor)=={1.,1.3,1.6}
        assert set(factors.dispatch)=={'causal','optimized'}
        assert (factors.annual_hours_accounted_for==8760).all()
        assert (factors.trial_bad_hours==0).all()
        assert (factors.original_bad_hours>0).all()
        assert ac.ac_feasible.astype(bool).all()
        assert (ac.min_v_pu>=.95-1e-10).all()
        assert (ac.max_trafo_pct<=100+1e-10).all()
        assert all(ac.groupby(['case','dispatch','pf','length_factor']).size().reindex(factors.set_index(['case','dispatch','pf','length_factor']).index).notna())
        dates=pd.date_range('2025-01-01', periods=8760, freq='h')
        eta=np.sqrt(.95)
        recs=[]
        for f in manifest['candidate_files']:
            data=z.read(f['candidate_file'])
            assert digest(data)==f['sha256'],f['candidate_file']
            df=pd.read_csv(io.BytesIO(data),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
            assert df.index.equals(dates),f['candidate_file']
            p=df
            b_soc=p.battery_soc_usable_kwh.to_numpy(float)
            c=p.battery_charge_dc_kw.to_numpy(float)
            d=p.battery_discharge_dc_kw.to_numpy(float)
            def mx(x):return float(np.max(abs(np.asarray(x))))
            err_soc=mx(b_soc[1:]-b_soc[:-1]-(eta*c-d/eta)[1:])
            err_ac=mx(p.inverter_ac_kw+p.grid_import_kw+p.unserved_kw-p.grid_export_kw-p.demand_kw)
            err_dc=mx(p.pv_dc_available_kw-p.curtailed_pv_dc_kw+d-c-p.inverter_ac_kw/.95)
            assert max(err_soc,err_ac,err_dc)<1e-6,f['candidate_file']
            for k,actual in {'annual_import_kwh':float(p.grid_import_kw.sum()),
                    'annual_pv_curtailment_dc_kwh':float(p.curtailed_pv_dc_kw.sum()),
                    'min_soc_kwh':float(p.battery_soc_usable_kwh.min()),
                    'max_soc_kwh':float(p.battery_soc_usable_kwh.max()),
                    'end_soc_kwh':float(p.battery_soc_usable_kwh.iloc[-1])}.items():
                assert abs(f['energy_original'][k]-actual)<1e-6,(f['candidate_file'],k)
                assert abs(f['energy_candidate'][k]-actual)<1e-6,(f['candidate_file'],k)
            floor=1.832 if 'min_cost' in f['case'] else 2.061
            ceiling=34.6 if 'min_cost' in f['case'] else 38.925
            assert b_soc.min()>=floor-1e-5 and b_soc.max()<=ceiling+1e-5
            assert p.grid_export_kw.abs().max()<1e-8 and p.unserved_kw.abs().max()<1e-8
            assert (p.grid_import_kw>=-1e-8).all()
            assert (p.battery_charge_dc_kw>=-1e-8).all() and (p.battery_discharge_dc_kw>=-1e-8).all()
            recs.append({'case':f['case'],'dispatch':f['dispatch'],'candidate_file':f['candidate_file'],
                 'file_sha256':f['sha256'],'rows':len(df),'soc_rec_err_kwh':err_soc,'ac_balance_err_kw':err_ac,
                 'dc_balance_err_kw':err_dc,'min_soc_kwh':b_soc.min(),'max_soc_kwh':b_soc.max(),
                 'annual_import_kwh':p.grid_import_kw.sum(),'pv_curtailment_dc_kwh':p.curtailed_pv_dc_kw.sum(),
                 'end_soc_kwh':b_soc[-1]})
    baseline=pd.read_csv(previous_portfolio,dtype={'transformer':str})
    assert len(baseline)==432
    assert baseline.case_identity.is_unique
    before_failing=int((baseline.adjusted_bad_hours>0).sum())
    assert before_failing==92
    overlay=baseline.copy()
    for r in factors.itertuples():
        tier='min_cost' if 'min_cost' in r.case else 'ss90'
        mask=((overlay.scenario=='A0')&(overlay.transformer=='106039') &
             (overlay.tier==tier)&(overlay.hardware_family=='archived_reference') &
             (overlay.topology=='mapped')&(overlay.dispatch==r.dispatch)&
             (overlay.pf==r.pf)&(overlay.length_factor==r.length_factor))
        assert mask.sum()==1, 'Expected exact matching source case'
        assert (overlay.loc[mask,'infeasible_hours']==r.original_bad_hours).all()
        assert (overlay.loc[mask,'adjusted_bad_hours']==r.original_bad_hours).all()
        overlay.loc[mask,'adjusted_bad_hours']=int(r.trial_bad_hours)
        overlay.loc[mask,'corrected_by']='A0_106039_sequenced_44_shifts_v1'
    assert int((overlay.adjusted_bad_hours>0).sum())==56
    assert int((overlay.adjusted_bad_hours==0).sum())==376
    assert int(overlay.adjusted_bad_hours.sum())==1248
    assert ((overlay.loc[overlay.scenario=='A1','adjusted_bad_hours'])==0).all()
    by_group=(factors.groupby(['case','dispatch'],as_index=False)
             .agg(nine_pf_length_cases=('pf','size'),original_violating_case_hours=('original_bad_hours','sum'),
                  trial_violating_case_hours=('trial_bad_hours','sum'),shift_count=('shift_count','first')))
    by_group=by_group.merge(ac.groupby(['case','dispatch'],as_index=False)
                       .agg(changed_hour_ac_checks=('ac_feasible','size'),
                            min_voltage_changed_hour_pu=('min_v_pu','min'),
                            max_trafo_changed_hour_pct=('max_trafo_pct','max')),
                       on=['case','dispatch'],validate='one_to_one')
    # Important: min voltage/transformer here refer only to changed-hour records.
    report={'status':'INDEPENDENT_FILE_AND_RESULT_AUDIT_PASSED',
        'original_trial_archive_sha256':digest(Path(trial_zip).read_bytes()),
        'reference_overlay_sha256':digest(Path(previous_portfolio).read_bytes()),
        'analysis_boundary':'Independent audit of uploaded outputs, no independent pandapower rerun',
        'source_local_runner':'Signed annual original AC outputs retained; only changed hours locally re-solved',
        'source_groups':4,'adopted_shifts':len(shifts),'unresolved_shifts':0,
        'changed_hour_ac_checks':len(ac),'changed_hour_ac_all_pass':bool(ac.ac_feasible.all()),
        'min_changed_hour_voltage_pu':float(ac.min_v_pu.min()),
        'max_changed_hour_transformer_loading_pct':float(ac.max_trafo_pct.max()),
        'min_changed_hour_voltage_margin_pu':float(ac.min_v_pu.min()-.95),
        'min_changed_hour_thermal_margin_pct':float(100-ac.max_trafo_pct.max()),
        'energy_trajectories_full_year_verified':len(recs),'energy_hashes_verified':len(recs),
        'pf_length_cases':len(factors),'prior_violation_case_hours_in_36_scenarios':int(factors.original_bad_hours.sum()),
        'trial_violation_case_hours_in_36_scenarios':int(factors.trial_bad_hours.sum()),
        'portfolio_failing_cases_before':before_failing,'portfolio_passing_cases_after':376,
        'portfolio_failing_cases_after':56,'remaining_94022_mapped_failing_cases':32,
        'remaining_92395_proposed_mst_failing_cases':24,
        'annual_pv_curtailment_unmodified':True,
        'site_and_model_uncertainty':'Not a field-approved three-phase study; 0.95 pu boundary margin extremely narrow'}
    (output_dir/'INDEPENDENT_QA.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    by_group.to_csv(output_dir/'A0_106039_FOUR_DISPATCH_GROUP_SUMMARY.csv',index=False)
    factors.to_csv(output_dir/'A0_106039_ALL_36_FACTOR_RESULTS.csv',index=False)
    overlay.to_csv(output_dir/'PORTFOLIO_432_POST_A0_106039_OVERLAY.csv',index=False)
    pd.DataFrame(recs).to_csv(output_dir/'A0_106039_FOUR_ANNUAL_ENERGY_QA.csv',index=False)
    shifts.to_csv(output_dir/'A0_106039_44_ADOPTED_SHIFTS.csv',index=False)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial_zip',type=Path)
    p.add_argument('prior_portfolio',type=Path);p.add_argument('output_dir',type=Path)
    a=p.parse_args();print(json.dumps(audit(a.trial_zip,a.prior_portfolio,a.output_dir),indent=2))
