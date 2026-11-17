#!/usr/bin/env python3
"""Independent summary and source-preserving 432-case overlay of uploaded 94022 shift trial.

This checks posted evidence, not a fresh pandapower execution.
Requires uploaded ZIP and previous audited 432-case portfolio CSV.
"""
from pathlib import Path
import argparse, hashlib, zipfile, io, json
import numpy as np
import pandas as pd

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(trialzip,portfolio,outdir):
    trialzip=Path(trialzip);portfolio=Path(portfolio);outdir=Path(outdir)
    outdir.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(trialzip) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('TRIAL_MANIFEST.json'))
        shifts=pd.read_csv(io.BytesIO(z.read('ADOPTED_SHIFT_EVENTS.csv')))
        ac=pd.read_csv(io.BytesIO(z.read('CHANGED_HOURS_FINAL_AC.csv')))
        factors=pd.read_csv(io.BytesIO(z.read('NINE_FACTOR_ANNUAL_REUSE.csv')))
        unresolved=pd.read_csv(io.BytesIO(z.read('UNRESOLVED_EVENTS.csv')))
        assert manifest['status']=='PARTIAL_OR_UNRESOLVED'
        assert manifest['tested_transformer']=='94022' and manifest['source_group_count']==4
        assert manifest['selected_event_count']==112 and len(shifts)==manifest['adopted_shift_count']==80
        assert manifest['unresolved_event_count']==len(unresolved)==32
        assert len(factors)==36 and len(ac)==1368
        assert factors.annual_hours_accounted_for.eq(8760).all()
        assert not shifts.duplicated(['case','dispatch','target_hour']).any()
        assert not factors.duplicated(['case','dispatch','pf','length_factor']).any()
        assert not ac.duplicated(['case','dispatch','pf','length_factor','timestamp_lst']).any()
        assert not unresolved.duplicated(['case','dispatch','event_timestamp']).any()
        assert set(factors.pf)=={.95,.98,1.} and set(factors.length_factor)=={1.,1.3,1.6}
        assert set(factors.dispatch)=={'causal','optimized'}
        assert ac.ac_feasible.astype(bool).all() and ac.min_v_pu.min()>=.95-1e-7 and ac.max_trafo_pct.max()<=100+1e-6
        assert (factors.trial_bad_hours<=factors.original_bad_hours).all()
        assert (factors.trial_bad_hours>0).sum()==32 and (factors.original_bad_hours>0).sum()==32
        assert int(factors.original_bad_hours.sum())==310 and int(factors.trial_bad_hours.sum())==126
        assert unresolved.event_timestamp.nunique()==9
        assert len(manifest['candidate_files'])==4
        rows=[]
        eta=np.sqrt(.95)
        for file in manifest['candidate_files']:
            raw=z.read(file['candidate_file'])
            assert hashlib.sha256(raw).hexdigest()==file['sha256']
            p=pd.read_csv(io.BytesIO(raw),parse_dates=['timestamp_lst']).set_index('timestamp_lst')
            assert len(p)==8760 and p.index.equals(pd.date_range('2025-01-01',periods=8760,freq='h'))
            assert np.isfinite(p.select_dtypes(include='number').to_numpy()).all()
            c=p.battery_charge_dc_kw.to_numpy(float);d=p.battery_discharge_dc_kw.to_numpy(float)
            soc=p.battery_soc_usable_kwh.to_numpy(float)
            soc_e=float(np.max(abs(soc[1:]-soc[:-1]-(eta*c-d/eta)[1:])))
            ac_e=float(np.max(abs(p.inverter_ac_kw+p.grid_import_kw+p.unserved_kw-p.grid_export_kw-p.demand_kw)))
            dc_e=float(np.max(abs(p.pv_dc_available_kw-p.curtailed_pv_dc_kw+d-c-p.inverter_ac_kw/.95)))
            assert max(soc_e,ac_e,dc_e)<1e-6
            assert (p.grid_import_kw>=-1e-8).all() and (c>=-1e-8).all() and (d>=-1e-8).all()
            assert np.max(np.minimum(c,d))<1e-8
            assert abs(p.grid_export_kw).max()<1e-8 and abs(p.unserved_kw).max()<1e-8
            floor=1.374 if 'min_cost' in file['case'] else 1.832
            assert soc.min()>=floor-1e-7
            metrics={'annual_import_kwh':float(p.grid_import_kw.sum()),
                'annual_pv_curtailment_dc_kwh':float(p.curtailed_pv_dc_kw.sum()),
                'min_soc_kwh':float(soc.min()), 'max_soc_kwh':float(soc.max()),'end_soc_kwh':float(soc[-1])}
            for k,v in metrics.items():
                assert abs(v-file['energy_original'][k])<1e-6 and abs(v-file['energy_candidate'][k])<1e-6
            key=((factors.case==file['case'])&(factors.dispatch==file['dispatch']))
            assert key.sum()==9
            adopted=shifts[(shifts.case==file['case'])&(shifts.dispatch==file['dispatch'])]
            unresolved_for=unresolved[(unresolved.case==file['case'])&(unresolved.dispatch==file['dispatch'])]
            assert len(adopted)+len(unresolved_for) in (42,41,14,15)
            rows.append(dict(case=file['case'],dispatch=file['dispatch'],source_energy_sha256=file['input_energy_sha256'],
                candidate_sha256=file['sha256'],annual_hours=8760,adopted_shifts=len(adopted),unresolved_events=len(unresolved_for),
                baseline_bad_factor_hours=int(factors[key].original_bad_hours.sum()),candidate_bad_factor_hours=int(factors[key].trial_bad_hours.sum()),
                failing_stress_cases_before=int((factors[key].original_bad_hours>0).sum()),
                failing_stress_cases_after=int((factors[key].trial_bad_hours>0).sum()),
                annual_import_kwh=metrics['annual_import_kwh'],annual_curtailment_dc_kwh=metrics['annual_pv_curtailment_dc_kwh'],
                minimum_soc_kwh=metrics['min_soc_kwh'],end_soc_kwh=metrics['end_soc_kwh'],
                soc_recurrence_error_kwh=soc_e,ac_balance_error_kw=ac_e,dc_balance_error_kw=dc_e))
    prior=pd.read_csv(portfolio,dtype={'transformer':str})
    assert len(prior)==432 and prior.case_identity.is_unique
    assert int((prior.adjusted_bad_hours>0).sum())==56 and int(prior.adjusted_bad_hours.sum())==1248
    overlay=prior.copy()
    for r in factors.itertuples(index=False):
        tier='min_cost' if 'min_cost' in r.case else 'ss90'
        s=(overlay.scenario=='A0') & (overlay.transformer=='94022') & (overlay.tier==tier) & \
          (overlay.hardware_family=='archived_reference')&(overlay.topology=='mapped') & \
          (overlay.dispatch==r.dispatch)&np.isclose(overlay.pf,r.pf)&np.isclose(overlay.length_factor,r.length_factor)
        assert s.sum()==1 and (overlay.loc[s,'adjusted_bad_hours']==r.original_bad_hours).all()
        overlay.loc[s,'adjusted_bad_hours']=r.trial_bad_hours
        overlay.loc[s,'corrected_by']='A0_94022_partial_seq_80_shifts_v1'
    assert len(overlay)==432 and int((overlay.adjusted_bad_hours>0).sum())==56
    assert int(overlay.adjusted_bad_hours.sum())==1064
    assert int(overlay.loc[(overlay.scenario=='A0')&(overlay.transformer=='92395')&(overlay.topology=='mst'),'adjusted_bad_hours'].sum())==938
    assert overlay.loc[overlay.scenario=='A1','adjusted_bad_hours'].eq(0).all()
    event_df=unresolved[['event_timestamp','case','dispatch','peak_trafo_pct','lowest_v_pu','tested_attempts']].copy()
    # Independent candidate context, do not confuse per-candidate inverter output with feeder node voltage.
    keys=[]
    with zipfile.ZipFile(trialzip) as z:
        for file in manifest['candidate_files']:
            p=pd.read_csv(io.BytesIO(z.read(file['candidate_file'])))
            events=event_df[(event_df.case==file['case'])&(event_df.dispatch==file['dispatch'])]
            for e in events.itertuples():
                c=p.loc[p.timestamp_lst==e.event_timestamp]
                assert len(c)==1
                a=c.iloc[0]
                keys.append({'timestamp_lst':e.event_timestamp,'case':file['case'],'dispatch':file['dispatch'],
                    'lowest_voltage_pu':e.lowest_v_pu,'peak_transformer_pct':e.peak_trafo_pct,
                    'demand_kw':a.demand_kw,'grid_import_kw':a.grid_import_kw,'inverter_ac_kw':a.inverter_ac_kw,
                    'battery_discharge_dc_kw':a.battery_discharge_dc_kw,'battery_end_soc_usable_kwh':a.battery_soc_usable_kwh,
                    'grid_import_zero':bool(abs(a.grid_import_kw)<1e-6)})
    context=pd.DataFrame(keys)
    assert len(context)==32
    groups=context.groupby('timestamp_lst',as_index=False).agg(
        affected_design_dispatch_groups=('case','size'),
        worst_reported_voltage_pu=('lowest_voltage_pu','min'),
        highest_reported_transformer_loading_pct=('peak_transformer_pct','max'),
        zero_grid_import_case_records=('grid_import_zero','sum'),
        min_grid_import_kw=('grid_import_kw','min'),max_grid_import_kw=('grid_import_kw','max'))
    assert len(groups)==9
    metrics={'status':'INDEPENDENT_SOURCE_FILE_AND_AC_RESULT_AUDIT_PASSED_PARTIAL_CORRECTION',
        'scope':'All four A0 94022 archived-reference case/dispatch schedules',
        'uploaded_trial_sha256':sha(trialzip),
        'previous_432_portfolio_sha256':sha(portfolio),
        'reported_trial_status':manifest['status'],
        'candidate_8760_hourly_files_verified':4,'accepted_shifts':80,'unresolved_event_records':32,
        'unique_unresolved_timestamps':9,'original_factor_violation_hours_94022':310,
        'candidate_factor_violation_hours_94022':126,'reduction_pct':round((310-126)/310*100,4),
        'AC_replays_changed_hour_verified':len(ac),
        'min_changed_hour_voltage_pu':float(ac.min_v_pu.min()),
        'max_changed_hour_transformer_pct':float(ac.max_trafo_pct.max()),
        'all_36_source_AC_cases_compared':True,
        'portfolio_total':432,'portfolio_failing_before':56,'portfolio_failing_after':56,
        'portfolio_adjusted_violation_case_hours_before':1248,
        'portfolio_adjusted_violation_case_hours_after':1064,
        'remaining_94022_mapped_violation_case_hours':126,
        'remaining_92395_mst_violation_case_hours':938,
        'original_signed_data_modified':False,
        'independent_pandapower_runs_in_this_audit':False,
        'note':'All changed-hour AC results are local replays; independent audit checks uploaded evidence, not a separate solver rerun. Partial result not a feasibility pass.'}
    pd.DataFrame(rows).to_csv(outdir/'A0_94022_FOUR_CANDIDATE_ENERGY_AUDIT.csv',index=False)
    factors.to_csv(outdir/'A0_94022_ALL_36_FACTOR_RESULTS.csv',index=False)
    context.to_csv(outdir/'A0_94022_32_UNRESOLVED_CASE_EVENTS.csv',index=False)
    groups.to_csv(outdir/'A0_94022_9_DISTINCT_RESIDUAL_HOURS.csv',index=False)
    overlay.to_csv(outdir/'STUDYA_432_POST_A0_94022_PARTIAL_OVERLAY.csv',index=False)
    (outdir/'INDEPENDENT_QA.json').write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    return metrics

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('trial_zip',type=Path);a.add_argument('previous_portfolio',type=Path);a.add_argument('output_directory',type=Path);v=a.parse_args()
    print(json.dumps(audit(v.trial_zip,v.previous_portfolio,v.output_directory),indent=2))
