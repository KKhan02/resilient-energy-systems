#!/usr/bin/env python3
"""Signed local-only Study A A1/106039 AC-aware two-evening trial.

Proposes SOC-neutral battery discharge shifts, verifies 8760h annual DC/AC
energy and SOC chronology, then re-solves ONLY the changed AC hours against
existing signed AC runs for all nine approved PF/service sensitivities.

This is a fixed-hardware *candidate schedule*, not a new PyPSA optimum.
No historical source file, signed manifest, or existing annual output is edited.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ORIGINAL='case1/studies/SEEDExchange_StudyA_PVBESS_v1/study_a_pvbess.py'
OUTBASE='case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01'
ETA_INV=.95
ETA_BAT=math.sqrt(.95)
FLOOR_PER_MODULE=4.325 - .8*5.12  # original usable-energy state at 20% physical SOC
TIERS=('min_cost_ref','ss90_ref')
SHIFTS={
 'min_cost_ref':(
  ('2025-10-13 17:00:00','2025-10-13 20:00:00',.60),
  ('2025-11-27 18:00:00','2025-11-27 20:00:00',.80)),
 'ss90_ref':(
  ('2025-11-27 18:00:00','2025-11-27 20:00:00',.80),)
}
PFS=(.95,.98,1.00)
LENGTHS=(1.,1.3,1.6)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_module(path):
    spec=importlib.util.spec_from_file_location('signed_studyA_pvbess_source',path)
    if spec is None or spec.loader is None:raise FileNotFoundError(path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod


def validate_battery(df,mods,power_dc_kw):
    needed=('demand_kw','inverter_ac_kw','grid_import_kw','grid_export_kw','unserved_kw',
       'battery_discharge_dc_kw','battery_charge_dc_kw','battery_soc_usable_kwh',
       'pv_dc_generated_kw','pv_dc_available_kw','curtailed_pv_dc_kw')
    assert set(needed).issubset(df),set(needed)-set(df.columns)
    x=df[list(needed)].to_numpy(dtype=float)
    assert np.isfinite(x).all(), 'Nonfinite annual dispatch'
    assert len(df)==8760 and df.index.equals(pd.date_range('2025-01-01',periods=8760,freq='h')), 'Bad 2025 chronology'
    demand=df.demand_kw.to_numpy(float)
    inv=df.inverter_ac_kw.to_numpy(float)
    imp=df.grid_import_kw.to_numpy(float)
    ch=df.battery_charge_dc_kw.to_numpy(float)
    dis=df.battery_discharge_dc_kw.to_numpy(float)
    soc=df.battery_soc_usable_kwh.to_numpy(float)
    assert max(abs(inv+imp+df.unserved_kw.to_numpy(float)-df.grid_export_kw.to_numpy(float)-demand))<5e-5, 'AC energy not closed'
    assert abs(df.grid_export_kw.to_numpy(float)).max()<5e-5 and abs(df.unserved_kw.to_numpy(float)).max()<5e-5, 'Zero export/no unserved policy'
    assert min(dis)>-5e-5 and min(ch)>-5e-5 and max(dis)<=power_dc_kw+5e-5 and max(ch)<=power_dc_kw+5e-5, 'Battery bank power exceeded'
    floor=mods*FLOOR_PER_MODULE
    assert min(soc)>=floor-1e-4 and max(soc)<=mods*4.325+1e-4, 'Battery SOC floor or nameplate exceeded'
    solar=df.pv_dc_generated_kw.to_numpy(float)
    assert max(abs(solar+dis-ch-inv/ETA_INV))<5e-5, 'DC coupling not closed'
    delta=ETA_BAT*ch - dis/ETA_BAT
    assert max(abs((soc[1:]-soc[:-1])-delta[1:]))<5e-5, 'Battery hourly SOC change not closed'
    assert abs(soc[0]-soc[-1]-delta[0])<5e-5, 'Battery annual cyclic boundary not closed'
    return {'soc_min_kwh':round(float(min(soc)),7), 'soc_max_kwh':round(float(max(soc)),7),
     'soc_end_kwh':round(float(soc[-1]),7), 'grid_import_kwh':round(float(sum(imp)),8),
     'dc_battery_discharge_kwh':round(float(sum(dis)),8)}


def shifted(original,tier,oct_dc=.60,nov_dc=.80):
    d=original.copy(deep=True)
    events=[]
    custom={
     'min_cost_ref':[('2025-10-13 17:00:00','2025-10-13 20:00:00',oct_dc),
                     ('2025-11-27 18:00:00','2025-11-27 20:00:00',nov_dc)],
     'ss90_ref':[('2025-11-27 18:00:00','2025-11-27 20:00:00',nov_dc)]}
    for src_s,dst_s,move in custom[tier]:
        src=pd.Timestamp(src_s);dst=pd.Timestamp(dst_s)
        assert src in d.index and dst in d.index and 0<move<=2, 'Invalid shift timestamps/power'
        assert src.date()==dst.date() and src<dst,'Shift must stay within one day'
        assert float(d.loc[src,'battery_discharge_dc_kw'])>move+1e-5,'Cannot reserve more battery power than original source discharge'
        assert float(d.loc[dst,'battery_charge_dc_kw'])<=1e-8 and float(d.loc[dst,'pv_dc_available_kw'])<=1e-8,'No daylight charging at destination'
        assert float(d.loc[dst,'grid_import_kw'])>ETA_INV*move+1e-5,'Sink cannot accept that much extra inverter power without export'
        # Battery discharge_dc represents solar-bus output of the battery link.
        # At the source, defer the discharge; at the sink release same DC amount.
        # This keeps annual energy and terminal SOC identical.
        d.loc[src,'battery_discharge_dc_kw']-=move
        d.loc[dst,'battery_discharge_dc_kw']+=move
        d.loc[src,'inverter_ac_kw']-=ETA_INV*move
        d.loc[dst,'inverter_ac_kw']+=ETA_INV*move
        d.loc[src,'grid_import_kw']+=ETA_INV*move
        d.loc[dst,'grid_import_kw']-=ETA_INV*move
        # Stored energy is an after-snapshot level. The intervening snapshots
        # retain move / eta_bat more energy; sink restores original trajectory.
        window=(d.index>=src)&(d.index<dst)
        d.loc[window,'battery_soc_usable_kwh']+=move/ETA_BAT
        if 'pcc_p_kw' in d:
            for stamp in (src,dst):
                d.loc[stamp,'pcc_p_kw']=d.loc[stamp,'grid_import_kw']-d.loc[stamp,'grid_export_kw']
        if {'pcc_p_kw','pcc_q_kvar_proxy','pcc_kva_proxy'}.issubset(d.columns):
            for stamp in (src,dst):
                d.loc[stamp,'pcc_kva_proxy']=math.hypot(float(d.loc[stamp,'pcc_p_kw']),float(d.loc[stamp,'pcc_q_kvar_proxy']))
        events.append({'tier':tier,'source_hour':src_s,'target_hour':dst_s,'moved_dc_kw':float(move),
          'added_target_ac_kw':ETA_INV*move,'retained_soc_kwh':move/ETA_BAT})
    return d,events


def verify_original_ac(meta,path,source_sha,pm,ts,orig,real_mod):
    summary=json.loads(real_mod.windows_extended_path(path/'ac_summary.json').read_text(encoding='utf-8'))
    hourpath=real_mod.windows_extended_path(path/'ac_hourly.csv')
    if summary.get('hours')!=8760 or summary.get('converged_hours')!=8760:
        raise ValueError('Original 8760 AC record not fully converged')
    if summary.get('energy_manifest_sha256')!=source_sha or summary.get('input_manifest_sha256')!=pm:
        raise ValueError('Original AC case has mismatched energy or cohort source')
    if sha(hourpath)!=summary['ac_hourly_sha256']:raise ValueError('Original AC CSV hash mismatch')
    ac=pd.read_csv(hourpath,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if len(ac)!=8760 or not ac.index.equals(orig.index):raise ValueError('Annual AC timestamps differ')
    for t in ts:
        if abs(float(ac.loc[t,'inverter_ac_kw'])-float(orig.loc[t,'inverter_ac_kw']))>1e-5:
            raise ValueError('Signed AC inverter power differs from source energy trace')
    return ac,summary


def run(root,out,oct_dc=.60,nov_dc=.80,dry_run=False):
    root=root.resolve();out=out.resolve()
    if dry_run:
        return {'status':'DRY_RUN_ONLY','candidate_pairs':SHIFTS,
                'tiers':list(TIERS),'sensitivities':len(PFS)*len(LENGTHS),
                'existing_results_unchanged':True}
    if out.exists():raise FileExistsError(f'Protected output already exists: {out}')
    mod=load_module(root/ORIGINAL)
    mp=root/mod.MANIFEST_REL
    m,v6,mapping,profiles=mod.secure_context(root,mp)
    ids,house_trace=mod.source_trace(m,mapping,profiles,'A1','106039')
    if len(ids)!=11:raise ValueError('Wrong 11-house 106039 A1 territory')
    energy={};hw={};hashes={};all_events=[];energy_reviews=[]
    for tier in TIERS:
        folder=root/OUTBASE/f'energy_A1_106039_{tier}'
        original,info=mod.validated_energy_directory(folder,m,mp,'A1','106039',ids,house_trace)
        hardware=info['hardware'];mods=int(hardware['battery_modules']);bkw=float(hardware['battery_power_dc_kw'])
        assert abs(float(hardware['inverter_kva']))>0
        original_stats=validate_battery(original,mods,bkw)
        candidate,ev=shifted(original,tier,oct_dc,nov_dc)
        changed_stats=validate_battery(candidate,mods,bkw)
        assert abs(original_stats['grid_import_kwh']-changed_stats['grid_import_kwh'])<1e-5
        assert abs(original_stats['soc_end_kwh']-changed_stats['soc_end_kwh'])<1e-5
        energy[tier]=(original,candidate)
        hw[tier]=hardware
        hashes[tier]=sha(mod.windows_extended_path(folder/'energy_manifest.json'))
        all_events+=ev
        energy_reviews.append({'tier':tier,'original':original_stats,'candidate':changed_stats,
           'original_energy_manifest_sha256':hashes[tier]})

    # Register the original EPM/AC modules before importing their network builder.
    # The existing v6 runner owns this dependency path, so no source files change.
    v6.repo_modules(root)
    from run_epm_validation import build_net
    import pandapower as pp
    rows=[];results=[];ac_validation=[]
    for tier in TIERS:
        original,candidate=energy[tier]
        changed_times=sorted(set(pd.Timestamp(e[k]) for e in all_events if e['tier']==tier for k in ('source_hour','target_hour')))
        for pf in PFS:
            for length in LENGTHS:
                suffix=f'A1_106039_{tier}_mapped_optimized_pf{int(round(pf*100)):03d}_length{int(round(length*10)):02d}_annual8760'
                folder=root/OUTBASE/'annual_ac_replays_v1'/suffix
                ac,summary=verify_original_ac(None,folder,hashes[tier],sha(mp),changed_times,original,mod)
                if abs(float(summary['pf'])-pf)>1e-9 or abs(float(summary['length_factor'])-length)>1e-9:
                    raise ValueError('Signed annual AC file does not match requested PF/route')
                terr=v6.new_territory(root,'A1','106039',ids,length)
                net,node=build_net(terr,'head')
                if set(node['loads'])!=set(ids):raise ValueError('Unexpected A1 household assignment')
                kva=float(hw[tier]['inverter_kva'])
                use_rows=ac.copy()
                changed_repaired=0
                for t in changed_times:
                    for label,frame in (('original',original),('candidate',candidate)):
                        r=v6.solve_ac_hour(net,node,terr,t,house_trace.loc[t],pf,
                            float(frame.loc[t,'inverter_ac_kw']),kva,float(frame.loc[t,'pv_dc_available_kw']),.25,9,'pvbess',pp)
                        r['tier']=tier;r['pf']=pf;r['length_factor']=length;r['change']=label
                        rows.append(r)
                        if r['status']!='CONVERGED':raise RuntimeError(f'AC solve failed: {suffix}/{t}/{label}: {r.get("error")}')
                        if label=='original':
                            old=ac.loc[t]
                            for key in ('max_trafo_pct','min_v_pu','max_v_pu','pcc_kva'):
                                if abs(float(old[key])-float(r[key]))>2e-4:
                                    raise AssertionError(f'Replayed baseline differs from original signed {suffix} {t} {key}')
                        else:
                            for key,val in r.items():
                                if key in use_rows.columns:
                                    use_rows.loc[t,key]=val
                            changed_repaired+=1
                invalid=use_rows[(use_rows.status!='CONVERGED')|(~use_rows.ac_feasible.astype(bool))]
                results.append({'tier':tier,'pf':pf,'length_factor':length,
                   'baseline_bad_hours':int((~ac.ac_feasible.astype(bool)).sum()),
                   'candidate_bad_hours':len(invalid),
                   'baseline_max_trafo_pct':float(ac.max_trafo_pct.max()),
                   'candidate_max_trafo_pct':float(use_rows.max_trafo_pct.max()),
                   'min_v_pu':float(use_rows.min_v_pu.min()),
                   'changed_hours':changed_repaired,
                   'all_8760_hours_accounted_for':len(use_rows)==8760,
                   'remaining_violations':';'.join(str(t) for t in invalid.index[:8]),
                   'original_ac_sha256':summary['ac_hourly_sha256']})
    ac_result=pd.DataFrame(results)
    success=bool((ac_result.candidate_bad_hours==0).all())
    out.mkdir(parents=True,exist_ok=False)
    pd.DataFrame(all_events).to_csv(out/'candidate_shifts.csv',index=False)
    pd.DataFrame(rows).to_csv(out/'changed_hour_ac_checks.csv',index=False)
    ac_result.to_csv(out/'nine_factor_annual_reuse_comparisons.csv',index=False)
    candidate_files={}
    for tier,(orig,cand) in energy.items():
        candidate_path=out/f'A1_106039_{tier}_candidate_8760.csv'
        cand.to_csv(candidate_path,float_format='%.10f')
        candidate_files[tier]={'path':candidate_path.name,'sha256':sha(candidate_path)}
    manifest={'status':'ALL_NINE_PF_LENGTH_CASES_FEASIBLE' if success else 'CANDIDATE_NOT_FULLY_FEASIBLE',
       'not_new_pypsa_optimum':True,'mode':'SOC_CONSISTENT_FIXED_SCHEDULE_SHIFT',
       'revalidation':'Changed hours independently AC solved, unchanged hours reused from signed annual results',
       'year':2025,'territory':'A1_106039','households':ids,
       'device_reference':hw,'source_annual_signatures':hashes,'candidate_annual_files':candidate_files,
       'energy_comparison':energy_reviews,'shifts':all_events,
       'screens':results,'notes':['All source annual files unchanged',
         'Nighttime Q disabled exactly as original AC solver',
         'Loss-aware annual economics and causal implementation remain separate issues',
         'Conditionally modelled EPM 5 kVA at 106039, not a verified transformer nameplate']}
    (out/'trial_manifest.json').write_text(json.dumps(manifest,indent=2,default=str)+'\n',encoding='utf-8')
    manifest['output_directory']=str(out)
    return {'status':manifest['status'],'nine_factor_cases':len(ac_result),'bad_remaining_cases':int((ac_result.candidate_bad_hours>0).sum()),
        'changed_hour_ac_replays':len(rows),'out':str(out),'energy_cycles_preserved':True}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_A1_106039_Redispatch_Trial_v1'))
    ap.add_argument('--oct-dc',type=float,default=.60)
    ap.add_argument('--nov-dc',type=float,default=.80)
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args(argv)
    print(json.dumps(run(a.repo_root,a.out,a.oct_dc,a.nov_dc,a.dry_run),indent=2))

if __name__=='__main__':main()
