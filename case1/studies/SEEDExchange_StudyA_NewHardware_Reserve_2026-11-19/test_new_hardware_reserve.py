"""Synthetic tests only; do not claim AC feasibility without user-local pandapower."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

src=Path(__file__).with_name("new_hardware_reserve.py")
spec=importlib.util.spec_from_file_location("new_hardware_reserve",src)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReserveTransferTests(unittest.TestCase):
    def fixture(self):
        i=pd.date_range("2025-11-27 18:00:00",periods=3,freq="h")
        f=pd.DataFrame(index=i)
        f["battery_discharge_dc_kw"]=[2.,0.,0.]
        f["battery_charge_dc_kw"]=0.
        f["pv_dc_available_kw"]=0.
        f["inverter_ac_kw"]=[1.9,0.,0.]
        f["grid_import_kw"]=[0.,4.5,4.8]
        f["grid_export_kw"]=0.
        f["battery_soc_usable_kwh"]=[4.,4.,4.]
        f["pcc_q_kvar_proxy"]=[.8,.9,1.]
        f["pcc_p_kw"]=f.grid_import_kw
        f["pcc_kva_proxy"]=(f.pcc_p_kw**2+f.pcc_q_kvar_proxy**2)**.5
        return f

    def test_transfer_preserves_import_and_discharge(self):
        a=self.fixture()
        b=m.move_one(a,a.index[0],a.index[-1],.8,12.,12.)
        self.assertAlmostEqual(float(a.grid_import_kw.sum()),float(b.grid_import_kw.sum()))
        self.assertAlmostEqual(float(a.battery_discharge_dc_kw.sum()),
                               float(b.battery_discharge_dc_kw.sum()))
        self.assertAlmostEqual(float(b.inverter_ac_kw.iat[-1]),.76)
        self.assertAlmostEqual(float(b.battery_soc_usable_kwh.iat[-1]),
                               float(a.battery_soc_usable_kwh.iat[-1]))
        self.assertAlmostEqual(float(b.pcc_p_kw.iat[0]),.76)
        self.assertEqual(float(a.inverter_ac_kw.iat[0]),1.9)

    def test_rejects_unavailable_donor_discharge(self):
        a=self.fixture()
        with self.assertRaisesRegex(ValueError,"Insufficient donor"):
            m.move_one(a,a.index[0],a.index[-1],3.,12.,12.)

    def test_rejects_non_nighttime_destination(self):
        a=self.fixture();a.at[a.index[-1],"pv_dc_available_kw"]=.1
        with self.assertRaisesRegex(ValueError,"Target must have no PV"):
            m.move_one(a,a.index[0],a.index[-1],.8,12.,12.)

    def test_rejects_export_after_shift(self):
        a=self.fixture();a.at[a.index[-1],"grid_import_kw"]=.1
        with self.assertRaisesRegex(ValueError,"Target would export"):
            m.move_one(a,a.index[0],a.index[-1],.8,12.,12.)

    def test_exact_case_names_and_distinct_target_hours(self):
        self.assertEqual(set(m.CASES),set(m.PLAN))
        self.assertEqual(set(m.CASES),set(m.KNOWN_BASELINE_FAILURES))
        for case in m.CASES:
            self.assertEqual({t for _,t,_ in m.PLAN[case]},
                             m.KNOWN_BASELINE_FAILURES[case])
            self.assertEqual(len(m.PLAN[case]),len(m.KNOWN_BASELINE_FAILURES[case]))

if __name__=="__main__":
    unittest.main()
