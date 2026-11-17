#!/usr/bin/env python3
"""Read-only local postprocessing of completed Study A hourly runs (no solver).

Scans all 22 optimized and causal energy folders, uses their signed SHA-256
before constructing monthly summaries. Also extracts precise 106039 A1 AC
violation times for the key reference/stress variants when signed files exist.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import pandas as pd
import numpy as np

ROOT_REL=Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/pvbess_phase_01')
EXPECTED_MONTHS=list(range(1,13))
AC_CASES=(
'A1_106039_min_cost_ref_mapped_optimized_pf098_length10_annual8760',
'A1_106039_ss90_ref_mapped_optimized_pf098_length10_annual8760',
'A1_106039_ss90_ref_mapped_causal_pf098_length10_annual8760',
'A1_106039_ss90_ref_mapped_optimized_pf095_length16_annual8760',
'A1_106039_min_cost_ref_mapped_optimized_pf095_length16_annual8760',
)

def winlong(p:Path)->Path:
    p=p.resolve()
    if os.name!='nt':return p
    s=str(p)
    if s.startswith('\\\\?\\'):return p
    if s.startswith('\\\\'):return Path('\\\\?\\UNC\\'+s[2:])
    return Path('\\\\?\\'+s)


def read(p):return winlong(p).read_bytes()


def signed_csv(root:Path,name:str,manifest:str,csvname:str,hashkey:str):
    f=root/name;meta=json.loads(read(f/manifest));raw=read(f/csvname)
    got=hashlib.sha256(raw).hexdigest()
    assert got==meta.get(hashkey),f'{name}: bad {hashkey} sha or missing field'
    data=pd.read_csv(io.BytesIO(raw),parse_dates=['timestamp_lst'])
    ts=data.timestamp_lst
    assert len(data)==8760 and ts.is_unique and ts.is_monotonic_increasing
    assert ts.iloc[0]==pd.Timestamp('2025-01-01 00:00:00')
    assert ts.iloc[-1]==pd.Timestamp('2025-12-31 23:00:00')
    assert ts.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    return data,meta,got


def monthly_frame(d:pd.DataFrame,case:str,mode:str,meta:dict):
    cols=('demand_kw','grid_import_kw','grid_export_kw','inverter_ac_kw',
          'pv_dc_available_kw','curtailed_pv_dc_kw',
          'battery_charge_dc_kw','battery_discharge_dc_kw','battery_soc_usable_kwh')
    missing=set(cols)-set(d.columns)
    assert not missing,(case,missing)
    assert (d[list(cols)].apply(pd.to_numeric).replace([np.inf,-np.inf],np.nan).notna().all().all()),case
    assert (d[['demand_kw','grid_import_kw','grid_export_kw']].to_numpy()>-1e-7).all()
    g=d.assign(month=d.timestamp_lst.dt.month).groupby('month',sort=True)
    rows=[]
    for m,gg in g:
        demand=float(gg.demand_kw.sum());imp=float(gg.grid_import_kw.sum())
        out={'case':case,'operation':mode,'month':int(m),'days':len(gg)//24,'hours':len(gg),
             'demand_kwh_ac':demand,'grid_import_kwh_ac':imp,
             'grid_export_kwh_ac':float(gg.grid_export_kw.sum()),
             'pv_inverter_output_kwh_ac':float(gg.inverter_ac_kw.sum()),
             'pv_available_kwh_dc':float(gg.pv_dc_available_kw.sum()),
             'pv_curtailed_kwh_dc':float(gg.curtailed_pv_dc_kw.sum()),
             'battery_charge_kwh_dc':float(gg.battery_charge_dc_kw.sum()),
             'battery_discharge_kwh_dc':float(gg.battery_discharge_dc_kw.sum()),
             'battery_soc_start_kwh':float(gg.battery_soc_usable_kwh.iloc[0]),
             'battery_soc_end_kwh':float(gg.battery_soc_usable_kwh.iloc[-1]),
             'self_sufficiency_pct':100*(1-imp/demand)}
        rows.append(out)
    assert len(rows)==12 and set(int(r['month']) for r in rows)==set(EXPECTED_MONTHS)
    assert abs(sum(r['demand_kwh_ac'] for r in rows)-float(d.demand_kw.sum()))<1e-7
    assert abs(sum(r['grid_import_kwh_ac'] for r in rows)-float(d.grid_import_kw.sum()))<1e-7
    return rows


def diagnostic_events(root:Path):
    records=[];failures=[]
    for case in AC_CASES:
        folder='annual_ac_replays_v1/'+case
        try:
            d,meta,sha=signed_csv(root,folder,'ac_summary.json','ac_hourly.csv','ac_hourly_sha256')
            assert set(['ac_feasible','max_trafo_pct','min_v_pu','timestamp_lst','pcc_kva','inverter_ac_kw']).issubset(d.columns)
            feasible=d.ac_feasible.astype(str).str.lower()=='true'
            violating=d[~feasible].copy()
            # Record all violating rows, plus the 10 highest-loading non-violating hours.
            highest=d.sort_values('max_trafo_pct',ascending=False).head(10)
            events=pd.concat([violating,highest]).drop_duplicates('timestamp_lst').sort_values('timestamp_lst')
            for _,r in events.iterrows():
                records.append({'case':case,'timestamp_lst':str(r.timestamp_lst),
                    'violates_AC':str(r.ac_feasible).lower()!='true',
                    'min_voltage_pu':float(r.min_v_pu),
                    'max_trafo_pct':float(r.max_trafo_pct),
                    'gross_demand_kw':float(r.gross_demand_kw),
                    'inverter_ac_kw':float(r.inverter_ac_kw),
                    'pcc_kva':float(r.pcc_kva),
                    'q_selected_kvar':float(r.q_selected_kvar),
                    'q_requested_kvar':float(r.q_requested_kvar),
                    'q_controller_status':str(r.q_controller_status),
                    'energy_displacement_kw':float(r.inverter_ac_kw),
                    'source_hourly_sha256':sha})
            if len(violating)!=int(meta.get('AC_infeasible_hours',-1)):
                raise AssertionError(f'AC summary violation-hours != CSV for {case}')
        except Exception as ex:
            failures.append({'case':case,'error':str(ex)})
    return records,failures


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--out',type=Path,default=Path('StudyA_Monthly_And_Residual_Evidence.zip'))
    args=ap.parse_args(argv)
    base=args.repo_root.resolve()/ROOT_REL
    target=args.out.resolve()
    if target.exists():raise SystemExit(f'Output exists, supply fresh --out: {target}')
    outputs=[];issues=[];monthly=[]
    for case_dir in sorted(base.glob('energy_*')):
        name=case_dir.name
        if not case_dir.is_dir():continue
        suffix=name.removeprefix('energy_')
        if name.endswith('_24h'):continue
        try:
            d,m,sha=signed_csv(base,name,'energy_manifest.json','energy_hourly_2025.csv','energy_csv_sha256')
            monthly+=monthly_frame(d,suffix,'optimized',m)
            outputs.append({'case':suffix,'operation':'optimized','sha256':sha,'status':'VERIFIED'})
        except Exception as ex:issues.append({'case':name,'operation':'optimized','error':str(ex)})
        causal='causal_'+suffix
        try:
            d,m,sha=signed_csv(base,causal,'causal_summary.json','causal_pv_first_2025.csv','output_sha256')
            monthly+=monthly_frame(d,suffix,'causal',m)
            outputs.append({'case':suffix,'operation':'causal','sha256':sha,'status':'VERIFIED'})
        except Exception as ex:issues.append({'case':causal,'operation':'causal','error':str(ex)})
    events,ac_issues=diagnostic_events(base)
    issues+=ac_issues
    table=pd.DataFrame(monthly)
    if len(table):table=table.sort_values(['case','operation','month'])
    assert len(set(x['case']+x['operation'] for x in outputs))==len(outputs)
    if len(outputs)!=44 or len(table)!=528:
        issues.append({'scope':'monthly_full_coverage','error':f'Expected 44 signed annual cases / 528 monthly rows; found {len(outputs)} / {len(table)}'})
    status={'expected_energy_cases':22,'expected_causal_cases':22,'monthly_verified_annual_cases':len(outputs),
      'monthly_rows':len(table),'expected_monthly_rows':528,
      'selected_ac_cases':len(AC_CASES),'selected_ac_cases_with_errors':len(ac_issues),
      'selected_ac_events':len(events),'issues':issues,
      'method':'Read-only signed annual hourly postprocessing; no AC or investment solver executed',
      'note':'PV source and battery flows DC kWh; demand, imports, exports and inverter outputs AC kWh. Causal SOC end differences remain explicit.'}
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('MONTHLY_ALL_COHORTS_ENERGY.csv',table.to_csv(index=False,float_format='%.9f'))
        z.writestr('RESIDUAL_106039_SELECTED_AC_HOURS.csv',pd.DataFrame(events).to_csv(index=False,float_format='%.9f'))
        z.writestr('SIGNED_44_CASE_INVENTORY.json',json.dumps(outputs,indent=2))
        z.writestr('EXTRACTION_STATUS.json',json.dumps(status,indent=2))
    print(json.dumps({'output':str(target),'verified_annual_energy_causal':len(outputs),
      'monthly_rows':len(table),'critical_AC_rows':len(events),'errors':len(issues)},indent=2))
    if issues:
        print('First errors:',issues[:5])
    return 0
if __name__=='__main__':raise SystemExit(main())
