#!/usr/bin/env python3
"""Independently audit the supplied 2025 A1-106039 fixed-hardware LP frontier ZIP.
This file does NOT run PyPSA/pandapower and never overwrites signed sources.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd

PREFIX = 'StudyA_A1_106039_Utilization_v1/'
IDS = ('SS_B9', 'SS_B10', 'SS_P45', 'SS_P41_KEEP20', 'MC_B9', 'MC_P37')
INDEX = pd.date_range('2025-01-01',periods=8760,freq='h')
ETA_INV = .95
ETA_BAT = math.sqrt(.95)


def digest(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def close(a,b,tol=2e-5):return abs(float(a)-float(b))<=tol

def check_case(case:str,df:pd.DataFrame,manifest:dict,annual:pd.Series,month:pd.DataFrame):
    failures=[]
    def gate(flag,message):
        if not bool(flag):failures.append(message)
    d=df.copy();d.timestamp_lst=pd.to_datetime(d.timestamp_lst)
    gate(len(d)==8760 and d.timestamp_lst.equals(pd.Series(INDEX)),'chronology')
    required={'demand_kw','pv_dc_generated_kw','pv_dc_available_kw','curtailed_pv_dc_kw',
              'battery_charge_dc_kw','battery_discharge_dc_kw','battery_soc_usable_kwh',
              'inverter_ac_kw','grid_import_kw','grid_export_kw','unserved_kw','pcc_kva_proxy'}
    gate(required.issubset(d.columns),'required columns')
    gate(np.isfinite(d[list(required)].to_numpy(dtype=float)).all(),'finite values')
    hw=manifest['hardware'];met=manifest['metrics']
    gate(manifest.get('status')=='FULL_8760H_FIXED_HARDWARE_FRONTIER_ENERGY_ONLY','case status')
    gate(manifest.get('case_id')==case and manifest.get('scenario')=='A1' and
         str(manifest.get('transformer'))=='106039','scenario identity')
    gate(len(manifest.get('selected_house_ids',[]))==11,'11 houses')
    gate(len(month)==12 and set(month.month)==set(range(1,13)),'monthly coverage')
    gate(int(hw['pv_panels'])==int(annual.pv_panels) and
         int(hw['battery_modules'])==int(annual.battery_modules) and
         close(hw['inverter_kva'],annual.inverter_kva) and
         close(hw['battery_power_dc_kw'],annual.battery_power_dc_kw),'hardware summary')
    gate(close(float(d.demand_kw.sum()),20878.,tol=.01),'annual demand')
    # CSV output rounds each hourly float to 10 decimal places; allow cumulative error.
    ac_res=np.max(np.abs(d.inverter_ac_kw+d.grid_import_kw+d.unserved_kw-d.grid_export_kw-d.demand_kw))
    dc_res=np.max(np.abs(d.pv_dc_generated_kw+d.battery_discharge_dc_kw-d.battery_charge_dc_kw-d.inverter_ac_kw/ETA_INV))
    soc=d.battery_soc_usable_kwh.to_numpy(float)
    dsoc=soc-np.roll(soc,1)-ETA_BAT*d.battery_charge_dc_kw+ d.battery_discharge_dc_kw/ETA_BAT
    soc_res=np.max(np.abs(dsoc))
    gate(ac_res<3e-6 and dc_res<3e-6 and soc_res<3e-6,'energy balance or cyclic SOC recurrence')
    gate((d.grid_export_kw.abs().max()<1e-6) and (d.unserved_kw.abs().max()<1e-6),'no export / ENS')
    floor=float(met['soc_floor_kwh']);energy=float(met['battery_modelled_usable_kwh'])
    gate(soc.min()>=floor-1e-6 and soc.max()<=energy+1e-6,'20pct SOC operating window')
    gate(d.battery_charge_dc_kw.max()<=float(hw['battery_power_dc_kw'])+1e-6 and
         d.battery_discharge_dc_kw.max()<=float(hw['battery_power_dc_kw'])+1e-6,'battery power')
    gate(float(hw['battery_power_dc_kw'])<=2.24*int(hw['battery_modules'])+1e-6,'Deye screening limit')
    gate(d.inverter_ac_kw.max()<=float(hw['inverter_kva'])+1e-6,'inverter AC power')
    gate(float(hw['pv_panels'])*.435<=1.5*float(hw['inverter_kva'])+1e-6,'DC/AC 1.5 ratio')
    gate(float(d.pcc_kva_proxy.max())<=5.000001,'energy-model PCC screening')
    gate(np.max(np.abs(d.pv_dc_available_kw-d.pv_dc_generated_kw-d.curtailed_pv_dc_kw))<1e-6,'curtailment identity')
    for col,key in [('demand_kw','annual_demand_kwh'),('pv_dc_available_kw','pv_available_dc_kwh'),
                    ('curtailed_pv_dc_kw','curtailed_pv_dc_kwh'),('grid_import_kw','grid_import_kwh'),
                    ('battery_discharge_dc_kw','battery_discharge_dc_kwh')]:
        gate(close(d[col].sum(),met[key],tol=.002) and close(d[col].sum(),annual[key],tol=.002),'summary '+key)
    for col in ['demand_kw','pv_dc_available_kw','curtailed_pv_dc_kw','grid_import_kw',
                'battery_charge_dc_kw','battery_discharge_dc_kw','inverter_ac_kw']:
        gate(close(month[col+'_kwh'].sum(),d[col].sum(),tol=.002),'monthly '+col)
    gate(close(met['annual_total_usd'],met['annual_equipment_usd']+met['annual_grid_import_usd'],tol=.001),'cost closure')
    gate(close(met['annual_grid_import_usd'],.29*met['grid_import_kwh'],tol=.001),'grid tariff closure')
    gate(close(annual.annual_total_usd,met['annual_total_usd'],tol=.002),'cost summary')
    if failures:raise AssertionError(case+': '+', '.join(failures))
    curt=(d.curtailed_pv_dc_kw>1e-4)
    near_floor=(d.battery_soc_usable_kwh<=floor+1e-3)
    near_cap=(d.battery_charge_dc_kw>=float(hw['battery_power_dc_kw'])-.001)
    return dict(case_id=case,AC_max_residual_kw=float(ac_res),DC_max_residual_kw=float(dc_res),
                SOC_max_residual_kwh=float(soc_res),SOC_floor_margin_kwh=float(soc.min()-floor),
                SOC_ceiling_margin_kwh=float(energy-soc.max()),
                PV_curtailment_hours=int(curt.sum()),
                PV_curtailment_near_SOC_floor_hours=int((curt & near_floor).sum()),
                PV_curtailment_at_charge_power_cap_hours=int((curt & near_cap).sum()),
                PV_curtailment_with_grid_import_hours=int((curt & (d.grid_import_kw>1e-4)).sum()),
                peak_inverter_ac_kw=float(d.inverter_ac_kw.max()),
                peak_battery_charge_dc_kw=float(d.battery_charge_dc_kw.max()),
                peak_battery_discharge_dc_kw=float(d.battery_discharge_dc_kw.max()),
                peak_pcc_proxy_kva=float(d.pcc_kva_proxy.max()),
                status='PASS_SIGNED_INPUT_AND_ENERGY_ONLY')


def audit(src:Path,out:Path):
    out.mkdir(parents=True,exist_ok=True)
    with ZipFile(src) as z:
        if z.testzip():raise ValueError('ZIP CRC failure')
        annual=pd.read_csv(io.BytesIO(z.read(PREFIX+'FRONTIER_ANNUAL_SUMMARY_PILOT.csv')))
        monthly=pd.read_csv(io.BytesIO(z.read(PREFIX+'FRONTIER_MONTHLY_ENERGY_PILOT.csv')))
        receipt=json.loads(z.read(PREFIX+'FRONTIER_RECEIPT_PILOT.json'))
        if set(annual.case_id)!=set(IDS)|{'MC_REF','SS_REF'} or len(annual)!=8:raise ValueError('Unexpected annual rows')
        if len(monthly)!=96 or set(monthly.case_id)!=set(annual.case_id) or monthly.duplicated(['case_id','month']).any():raise ValueError('Monthly coverage')
        if receipt.get('status')!='COMPLETE' or set(receipt.get('new_solved',[]))!=set(IDS) or receipt.get('unresolved'):raise ValueError('Runner receipt mismatch')
        qa=[]
        model_hashes=set();input_hashes=set();solar_hashes=set()
        for cid in IDS:
            path=PREFIX+'energy_'+cid+'/'
            raw=z.read(path+'energy_hourly_2025.csv')
            manifest=json.loads(z.read(path+'energy_manifest.json'))
            if digest(raw)!=manifest['energy_csv_sha256']:raise ValueError('SHA mismatch '+cid)
            if manifest['source_model_sha256']!=receipt['original_model_sha256'] or manifest['input_manifest_sha256']!=receipt['signed_source_manifest_sha256'] or manifest['original_pv_source_sha256']!=receipt['solar_source_sha256']:
                raise ValueError('Original source hash mismatch '+cid)
            model_hashes.add(manifest['source_model_sha256']);input_hashes.add(manifest['input_manifest_sha256']);solar_hashes.add(manifest['original_pv_source_sha256'])
            df=pd.read_csv(io.BytesIO(raw))
            qa.append(check_case(cid,df,manifest,annual.loc[annual.case_id.eq(cid)].iloc[0],monthly[monthly.case_id.eq(cid)]))
    qa=pd.DataFrame(qa)
    # Dominance on cost and imports only. PV curtailment retained as a distinct 3rd metric.
    vals=annual.set_index('case_id')
    frontier=[]
    for a in annual.case_id:
        row=vals.loc[a];dom=[]
        for b in annual.case_id:
            if a==b:continue
            other=vals.loc[b]
            if (other.annual_total_usd<=row.annual_total_usd+1e-6 and other.grid_import_kwh<=row.grid_import_kwh+1e-6 and
                (other.annual_total_usd<row.annual_total_usd-1e-6 or other.grid_import_kwh<row.grid_import_kwh-1e-6)):
                dom.append(b)
        frontier.append(dict(case_id=a,cost_import_dominated_by=';'.join(dom),cost_import_nondominated=not bool(dom)))
    frontier=pd.DataFrame(frontier)
    delta=[]
    pairs={'MC_B9':'MC_REF','MC_P37':'MC_REF','SS_B9':'SS_REF','SS_B10':'SS_REF',
           'SS_P45':'SS_REF','SS_P41_KEEP20':'MC_REF'}
    for c,ref in pairs.items():
        x=vals.loc[c];b=vals.loc[ref]
        delta.append(dict(case_id=c,reference=ref,change_annual_cost_usd=x.annual_total_usd-b.annual_total_usd,
          change_grid_import_kwh=x.grid_import_kwh-b.grid_import_kwh,
          change_curtailment_kwh=x.curtailed_pv_dc_kwh-b.curtailed_pv_dc_kwh,
          change_self_sufficiency_points=x.self_sufficiency_percent-b.self_sufficiency_percent,
          change_equivalent_full_cycles=x.equivalent_full_cycles-b.equivalent_full_cycles))
    delta=pd.DataFrame(delta)
    annual.merge(frontier,on='case_id').to_csv(out/'ALL_8_DESIGNS_COST_IMPORT_FRONTIER.csv',index=False,float_format='%.10f')
    qa.to_csv(out/'SIX_NEW_CASES_INDEPENDENT_QA.csv',index=False,float_format='%.10g')
    delta.to_csv(out/'SIX_CANDIDATE_DELTAS.csv',index=False,float_format='%.10f')
    monthly.to_csv(out/'MONTHLY_96_CASE_MONTH_RECORDS.csv',index=False)
    doc=dict(status='PASS',source_archive_sha256=digest(src.read_bytes()),zip_crc='PASS',
       source_models_count=len(model_hashes),sources_count=len(input_hashes),solar_source_count=len(solar_hashes),
       new_8760hour_cases=len(qa),signed_reference_rows=2,monthly_records=len(monthly),
       hourly_rows_independently_checked=len(qa)*8760,AC_validation='NOT_PERFORMED',
       numerical_solves_by_auditor=0,reference_energy_sha=receipt.get('reference_manifest_sha256'))
    (out/'INDEPENDENT_QA.json').write_text(json.dumps(doc,indent=2)+'\n')
    return annual,qa,frontier,delta,doc

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('StudyA_A1_106039_Utilization_Pilot_v1.zip'))
    p.add_argument('--out',type=Path,default=Path('StudyA_Utilization_Independent_Audit'))
    args=p.parse_args();_,_,_,_,doc=audit(args.source,args.out)
    print(json.dumps(doc,indent=2))
