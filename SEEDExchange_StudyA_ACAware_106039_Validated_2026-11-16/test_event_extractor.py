"""Synthetic fixture for event extractor, tests no network, solver, or local files."""
import importlib.util, json, hashlib, tempfile, unittest
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('studya_diag',HERE/'extract_remaining_events_and_pv.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class TestExtract(unittest.TestCase):
 def test_one_signed_violation_with_dispatch_join(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   base=root/mod.BASE
   e=base/'energy_A0_94022_min_cost_ref';e.mkdir(parents=True)
   acdir=base/'annual_ac_replays_v1'/'A0_94022_min_cost_ref_mapped_optimized_pf095_length10_annual8760';acdir.mkdir(parents=True)
   idx=pd.date_range('2025-01-01',periods=8760,freq='h')
   en=pd.DataFrame({'timestamp_lst':idx,'demand_kw':2.,'inverter_ac_kw':.5,'grid_import_kw':1.5,'battery_soc_usable_kwh':3.,'battery_charge_dc_kw':0.,'battery_discharge_dc_kw':.5,'pv_dc_available_kw':1.,'curtailed_pv_dc_kw':.25})
   en.to_csv(e/'energy_hourly_2025.csv',index=False)
   def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
   (e/'energy_manifest.json').write_text(json.dumps({'energy_csv_sha256':digest(e/'energy_hourly_2025.csv'),'hardware':{'pv_panels':5,'battery_modules':3,'battery_power_dc_kw':2.,'inverter_kva':5.}}))
   ac=pd.DataFrame({'timestamp_lst':idx,'status':'CONVERGED','ac_feasible':True,'gross_demand_kw':2.,'inverter_ac_kw':.5,'max_trafo_pct':70.,'max_line_pct':5.,'min_v_pu':.97,'pcc_kva':3.})
   ac.loc[30,'ac_feasible']=False;ac.loc[30,'max_trafo_pct']=104.
   ac.to_csv(acdir/'ac_hourly.csv',index=False)
   (acdir/'ac_summary.json').write_text(json.dumps({'hours':8760,'converged_hours':8760,'scenario':'A0','transformer':'94022','topology':'mapped','dispatch':'optimized','pf':.95,'length_factor':1.0,'ac_hourly_sha256':digest(acdir/'ac_hourly.csv')}))
   r=pd.DataFrame([{'case':acdir.name,'scenario':'A0','transformer':'94022','tier':'min_cost','hardware_family':'archived_reference','topology':'mapped','dispatch':'optimized','pf':.95,'length_factor':1.0,'infeasible_hours':1,'effective_infeasible_hours':1}])
   ev,unique,pv,valid,issues=mod.collect(root,r)
   self.assertEqual((valid,len(issues),len(ev),len(unique),len(pv)),(1,0,1,1,1))
   self.assertEqual(str(ev.iloc[0].timestamp_lst),'2025-01-02 06:00:00')
   self.assertEqual(pv.iloc[0].curtailment_hours,8760)
 def test_long_path_helper_returns_strings(self):
  p=mod.xp(Path('.'));self.assertIsInstance(p,str)

if __name__=='__main__':unittest.main()
