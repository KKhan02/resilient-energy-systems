import importlib.util, unittest
from pathlib import Path
import numpy as np
import pandas as pd

S=Path(__file__).resolve().parents[1]/'studya_106039_soc_shift_trial.py'
spec=importlib.util.spec_from_file_location('soc_trial',S)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_daytime_redispatch_defers_battery_energy(self):
        ix=pd.date_range('2025-01-01','2025-12-31 23:00',freq='h')
        d=pd.DataFrame(index=ix)
        d['battery_discharge_dc_kw']=0.
        d['battery_charge_dc_kw']=0.
        d['battery_soc_usable_kwh']=1.832
        d['demand_kw']=5.
        d['inverter_ac_kw']=0.
        d['grid_import_kw']=5.
        d['grid_export_kw']=0.
        d['pv_dc_available_kw']=0.
        d['pcc_p_kw']=5.
        d['pcc_q_kvar_proxy']=1.
        d['pcc_kva_proxy']=np.hypot(5.,1.)
        for src,move in [(pd.Timestamp('2025-10-13 17:00'),.6),(pd.Timestamp('2025-11-27 18:00'),.8)]:
            d.loc[src,'battery_discharge_dc_kw']=move+1
            d.loc[src,'inverter_ac_kw']=mod.ETA_INV*(move+1)
            d.loc[src,'grid_import_kw']=5.-d.loc[src,'inverter_ac_kw']
        d.loc[pd.Timestamp('2025-10-13 20:00'),'inverter_ac_kw']=.256
        d.loc[pd.Timestamp('2025-10-13 20:00'),'grid_import_kw']=4.744
        c,ev=mod.shifted(d,'min_cost_ref')
        self.assertEqual(len(ev),2)
        self.assertAlmostEqual(c.grid_import_kw.sum(),d.grid_import_kw.sum(),places=8)
        for row in ev:
            src=pd.Timestamp(row['source_hour']);end=pd.Timestamp(row['target_hour'])
            self.assertAlmostEqual(c.loc[src,'battery_soc_usable_kwh']-d.loc[src,'battery_soc_usable_kwh'],row['retained_soc_kwh'])
            self.assertAlmostEqual(c.loc[end,'battery_soc_usable_kwh'],d.loc[end,'battery_soc_usable_kwh'])
            self.assertAlmostEqual(c.loc[end,'inverter_ac_kw']-d.loc[end,'inverter_ac_kw'],row['added_target_ac_kw'])
            self.assertAlmostEqual(c.loc[src,'inverter_ac_kw']-d.loc[src,'inverter_ac_kw'],-row['added_target_ac_kw'])

    def test_rejects_insufficient_source_discharge(self):
        ix=pd.date_range('2025-11-27 18:00',periods=3,freq='h')
        d=pd.DataFrame(index=ix)
        d['battery_discharge_dc_kw']=[.3,0,0]
        d['battery_charge_dc_kw']=0.
        d['pv_dc_available_kw']=0.
        d['grid_import_kw']=5.
        d['grid_export_kw']=0.
        d['inverter_ac_kw']=0.
        d['battery_soc_usable_kwh']=1.832
        with self.assertRaisesRegex(AssertionError,'reserve more'):
            mod.shifted(d,'ss90_ref')

if __name__=='__main__': unittest.main()
