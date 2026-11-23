"""Solver-free regression of two-hour 94022 battery deferral and screen."""
import unittest
import math
import pandas as pd
import matched16_94022_nov_soc_shift_ac as m


def fake():
    idx=pd.date_range("2025-11-27 13:00:00",periods=8,freq="h")
    d=pd.DataFrame({
        "battery_discharge_dc_kw":[.3,1,0,0,0,0,0,0],
        "battery_charge_dc_kw":[0]*8,
        "battery_soc_usable_kwh":[4,3,2,2,2,2,2,2],
        "demand_kw":[3]*8,"grid_import_kw":[1]*8,
        "inverter_ac_kw":[2]*8,
        "grid_export_kw":[0]*8,"pv_dc_available_kw":[0]*8,
        "pcc_p_kw":[1]*8,"pcc_q_kvar_proxy":[.6]*8,
        "pcc_kva_proxy":[math.hypot(1,.6)]*8,
    },index=idx)
    return d


class ACShiftMath(unittest.TestCase):
    def test_preserve_total_power_and_discharge(self):
        a=fake()
        b=m.transfer(a,"2025-11-27 13:00:00","2025-11-27 20:00:00",.2)
        self.assertAlmostEqual(b.battery_discharge_dc_kw.sum(),a.battery_discharge_dc_kw.sum())
        self.assertAlmostEqual(b.grid_import_kw.sum(),a.grid_import_kw.sum())
        self.assertAlmostEqual(b.inverter_ac_kw.sum(),a.inverter_ac_kw.sum())
        self.assertAlmostEqual(b.iloc[0].grid_import_kw,a.iloc[0].grid_import_kw+.2*.95)
        self.assertAlmostEqual(b.iloc[-1].grid_import_kw,a.iloc[-1].grid_import_kw-.2*.95)

    def test_soc_retention_through_intervening_hour(self):
        a=fake()
        b=m.transfer(a,"2025-11-27 13:00:00","2025-11-27 20:00:00",.2)
        for i in range(7):
            self.assertAlmostEqual(b.iloc[i].battery_soc_usable_kwh,
                                   a.iloc[i].battery_soc_usable_kwh+.2/m.ETA_BAT)
        self.assertAlmostEqual(b.iloc[7].battery_soc_usable_kwh,a.iloc[7].battery_soc_usable_kwh)

    def test_zero_shift_is_identity(self):
        a=fake();b=m.transfer(a,"2025-11-27 13:00:00","2025-11-27 20:00:00",0)
        pd.testing.assert_frame_equal(a,b)

    def test_reject_overspending_donor(self):
        with self.assertRaisesRegex(ValueError,"more than original"):
            m.transfer(fake(),"2025-11-27 13:00:00","2025-11-27 20:00:00",.4)

    def test_reject_negative_shift(self):
        with self.assertRaisesRegex(ValueError,"Invalid"):
            m.transfer(fake(),"2025-11-27 13:00:00","2025-11-27 20:00:00",-.1)

    def test_shift_peak_respects_device(self):
        a=fake()
        hw={"battery_modules":1,"battery_power_dc_kw":3,
            "inverter_kva":5,"transformer_kva_assumed_or_evidenced":5}
        upper=m.bound_one_donor(a,"2025-11-27 13:00:00","2025-11-27 20:00:00",hw)
        self.assertGreaterEqual(upper,0)
        self.assertLessEqual(upper,.3+1e-9)

    def test_donor_time_must_precede_and_same_day(self):
        a=fake()
        hw={"battery_modules":1,"battery_power_dc_kw":3,
            "inverter_kva":5,"transformer_kva_assumed_or_evidenced":5}
        with self.assertRaisesRegex(ValueError,"preceding"):
            m.bound_one_donor(a,"2025-11-27 20:00:00","2025-11-27 13:00:00",hw)

    def test_matching_annual_total_accepts_small_rounding(self):
        m.same_total({"annual_import_kwh":10.00000001},{"annual_import_kwh":10}, "annual_import_kwh")

    def test_mismatch_annual_total_rejected(self):
        with self.assertRaisesRegex(ValueError,"Annual source total"):
            m.same_total({"annual_import_kwh":11},{"annual_import_kwh":10}, "annual_import_kwh")

    def test_exact_battery_20pct_model_floor_constant(self):
        self.assertAlmostEqual(m.PHYSICAL_FLOOR_MODEL_PER_MODULE,.229)
        self.assertEqual(m.CASES["A1_94022_min_cost_to_A0"],"2025-11-27 13:00:00")
        self.assertEqual(m.CASES["A1_94022_ss90_to_A0"],"2025-11-27 17:00:00")
        self.assertEqual(len(m.SAMPLE_FRACTIONS)*len(m.CASES)*len(m.PF)*2,40)


if __name__=="__main__":
    unittest.main()
