from pathlib import Path
import importlib.util,unittest,math
import numpy as np
import pandas as pd
P=Path(__file__).resolve().parents[1]/'a1_repair_trial.py'
spec=importlib.util.spec_from_file_location('a1_r',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def synthetic():
    index=pd.date_range('2025-01-01',periods=8760,freq='h')
    df=pd.DataFrame(index=index)
    for k in ('battery_discharge_dc_kw','battery_charge_dc_kw','inverter_ac_kw','pv_dc_available_kw','pv_dc_generated_kw','curtailed_pv_dc_kw','grid_export_kw','unserved_kw'):df[k]=0.
    df['demand_kw']=5.;df['grid_import_kw']=5.
    df['battery_soc_usable_kwh']=8*m.FLOOR_PER_MODULE
    ch=pd.Timestamp('2025-11-27 11:00');source=pd.Timestamp('2025-11-27 18:00')
    df.loc[ch,'battery_charge_dc_kw']=1/.95
    df.loc[ch,'pv_dc_available_kw']=1/.95
    df.loc[ch,'pv_dc_generated_kw']=1/.95
    df.loc[ch:source-pd.Timedelta(hours=1),'battery_soc_usable_kwh']+=1/m.ETA_BAT
    df.loc[source,'battery_discharge_dc_kw']=1
    df.loc[source,'inverter_ac_kw']=.95
    df.loc[source,'grid_import_kw']=4.05
    return df,source,pd.Timestamp('2025-11-27 20:00')

class Tests(unittest.TestCase):
    def test_shift_conserves_full_annual_physics(self):
        df,src,dst=synthetic()
        m.energy_checks(df,8,12,12)
        c=m.shift_one(df,src,dst,.5,12,12,8)
        audit=m.energy_checks(c,8,12,12,df)
        self.assertAlmostEqual(audit['end_soc_kwh'],df.battery_soc_usable_kwh.iloc[-1])
        self.assertAlmostEqual(c.loc[dst,'inverter_ac_kw'],.475)
        self.assertAlmostEqual(c.loc[src,'inverter_ac_kw'],.475)
    def test_excessive_donor_move_rejected(self):
        df,src,dst=synthetic()
        with self.assertRaisesRegex(ValueError,'donor'):m.shift_one(df,src,dst,1.5,12,12,8)
    def test_reverse_time_rejected(self):
        df,src,dst=synthetic()
        with self.assertRaisesRegex(ValueError,'forward'):m.shift_one(df,dst,src,.5,12,12,8)
    def test_target_export_rejected(self):
        df,src,dst=synthetic();df.loc[dst,'grid_import_kw']=.2
        with self.assertRaisesRegex(ValueError,'export'):m.shift_one(df,src,dst,.5,12,12,8)
    def test_annual_loss_rejected(self):
        df,src,dst=synthetic();c=m.shift_one(df,src,dst,.5,12,12,8)
        c.loc[dst,'grid_import_kw']+=.01
        with self.assertRaisesRegex(ValueError,'AC energy balance'):m.energy_checks(c,8,12,12,df)
    def test_inverter_limit_rejected(self):
        df,src,dst=synthetic();df.loc[dst,'inverter_ac_kw']=11.8
        with self.assertRaisesRegex(ValueError,'inverter'):m.shift_one(df,src,dst,.5,12,12,8)
    def test_donor_selection_same_day(self):
        df,src,dst=synthetic()
        w=pd.DataFrame({'hour_timestamp':[pd.Timestamp('2025-11-26 19:00'),pd.Timestamp('2025-11-27 10:00'),src,dst],
                        'battery_discharge_dc_kw':[1.,1.,.5,0.]})
        self.assertEqual(m.donor_hours(w,dst),[src])

if __name__=='__main__':unittest.main()
