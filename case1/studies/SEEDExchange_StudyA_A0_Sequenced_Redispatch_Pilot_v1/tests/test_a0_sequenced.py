import importlib.util
import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SRC=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('studya_a0_pilot_under_test', SRC/'a0_sequenced_trial.py')
a0=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a0)

class TestA0Safety(unittest.TestCase):
    def test_pinned_window_provenance_and_counts(self):
        p=SRC/'StudyA_Mapped_SOC_Windows_for_Redispatch.zip'
        self.assertEqual(a0.sha(p),a0.EXPECTED_WINDOWS_SHA)
        e,w,r,sigs=a0.load_windows(p)
        selected=a0.selected_a0(e)
        self.assertEqual(len(e),175)
        self.assertEqual(len(w),5075)
        self.assertEqual(len(selected),156)
        self.assertEqual(selected.groupby(['transformer','tier','dispatch']).ngroups,8)
        self.assertEqual(len(selected[selected.transformer=='106039']),44)
        self.assertEqual(len(selected[selected.transformer=='94022']),112)
        groups=selected.assign(day=selected.timestamp_lst.dt.date).groupby(['transformer','tier','dispatch','day']).size()
        self.assertEqual(len(groups),109)
        self.assertEqual(int((groups>1).sum()),43)
    def test_shift_preserves_energy_and_soc(self):
        ix=pd.date_range('2025-01-01',periods=8760,freq='h')
        cols=['demand_kw','pv_dc_available_kw','curtailed_pv_dc_kw','battery_charge_dc_kw',
              'battery_discharge_dc_kw','battery_soc_usable_kwh','inverter_ac_kw',
              'grid_import_kw','grid_export_kw','unserved_kw']
        d=pd.DataFrame(0.,index=ix,columns=cols)
        src=pd.Timestamp('2025-01-03 18:00:00')
        dst=pd.Timestamp('2025-01-03 20:00:00')
        d.loc[src,['demand_kw','inverter_ac_kw','battery_discharge_dc_kw']]=[.95,.95,1.]
        d.loc[dst,['demand_kw','grid_import_kw']]=[1.,1.]
        d['battery_soc_usable_kwh']=10.
        d.loc[src:,'battery_soc_usable_kwh']-=1./a0.ETA_BAT
        a0.energy_checks(d,8,12.,12.)
        cand=a0.shift_one(d,src,dst,.5,12.,12.,8)
        a0.energy_checks(cand,8,12.,12.,orig=d)
        self.assertAlmostEqual(cand.loc[src,'battery_discharge_dc_kw'],.5)
        self.assertAlmostEqual(cand.loc[dst,'battery_discharge_dc_kw'],.5)
        self.assertAlmostEqual(cand.loc[src,'grid_import_kw'],.475)
        self.assertAlmostEqual(cand.loc[dst,'grid_import_kw'],.525)
        self.assertAlmostEqual(float(d.grid_import_kw.sum()),float(cand.grid_import_kw.sum()))
        self.assertAlmostEqual(float(d.battery_soc_usable_kwh.iloc[-1]),float(cand.battery_soc_usable_kwh.iloc[-1]))
    def test_bad_donor_date_rejected(self):
        ix=pd.date_range('2025-01-01',periods=8760,freq='h')
        d=pd.DataFrame(index=ix,data={'battery_discharge_dc_kw':0.,'battery_charge_dc_kw':0.,'inverter_ac_kw':0.,'grid_import_kw':0.,'battery_soc_usable_kwh':5.})
        with self.assertRaisesRegex(ValueError,'forward, same-day'):
            a0.shift_one(d,'2025-01-01 21:00:00','2025-01-02 20:00:00',.2,5.,5.,3)
    def test_case_identity_restrictions(self):
        self.assertEqual(a0.case_parts('A0_94022_ss90_ref'),('A0','94022','ss90','ref'))
        with self.assertRaises(ValueError):a0.case_parts('A0_92395_ss90_hypothetical')
    def test_donors_only_earlier_same_day(self):
        e,w,_,_=a0.load_windows(SRC/'StudyA_Mapped_SOC_Windows_for_Redispatch.zip')
        g=w[(w.scenario=='A0')&(w.transformer=='106039')&(w.tier=='min_cost')&(w.dispatch=='causal')]
        d=pd.Timestamp(g.event_timestamp.iloc[0]);win=g[g.event_timestamp==d]
        donors=a0.donor_hours(win,d)
        self.assertTrue(len(donors)>=1)
        self.assertTrue(all(x<d and x.date()==d.date() for x in donors))

if __name__=='__main__':unittest.main()
