"""Solver-free three residual 94022 joint donor/target regression tests."""
import unittest
import math
import pandas as pd
import matched16_94022_ss90_remaining3_ac as a


def base_6():
    idx=pd.date_range("2025-11-29 16:00:00",periods=5,freq="h")
    return pd.DataFrame({
      "battery_discharge_dc_kw":[0,2.0,2.0,.5,0],
      "battery_soc_usable_kwh":[8.,6.,4.,3.,3.],
      "inverter_ac_kw":[0,1.9,1.9,.475,0],
      "grid_import_kw":[3.,0.,0.,3.,4.],
      "grid_export_kw":[0.,0.,0.,0.,0.],
      "pcc_p_kw":[3.,0.,0.,3.,4.]},index=idx)


class JointNovResidualTests(unittest.TestCase):
    def test_three_distinct_same_day_donor_target_windows(self):
        self.assertTrue(a.check_event_layout())
        self.assertEqual(len(a.EVENTS),3)
        self.assertEqual(len(a.SOURCE_TIMES),6)

    def test_five_candidate_grid_and_sixty_hour_model(self):
        self.assertEqual(a.SAMPLES,(0,.25,.5,.75,.98))
        self.assertEqual(len(a.SAMPLES)*len(a.SOURCE_TIMES)*len(a.PF),60)

    def test_already_accepted_march_nov27_hours_do_not_overlap(self):
        self.assertFalse(set(a.annual.CHANGED)&set(a.SOURCE_TIMES))

    def test_nov29_joint_shifts_preserve_energy_source_and_targets(self):
        o=base_6()
        x=.6;y=.8
        shifted=a.nov.transfer(o,"2025-11-29 17:00:00","2025-11-29 19:00:00",x)
        shifted=a.nov.transfer(shifted,"2025-11-29 18:00:00","2025-11-29 20:00:00",y)
        self.assertAlmostEqual(shifted.battery_discharge_dc_kw.sum(),
                               o.battery_discharge_dc_kw.sum())
        self.assertAlmostEqual(shifted.grid_import_kw.sum(),o.grid_import_kw.sum())
        self.assertLess((shifted.pcc_p_kw-shifted.grid_import_kw).abs().max(),1e-12)
        self.assertAlmostEqual(shifted.inverter_ac_kw.sum(),o.inverter_ac_kw.sum())
        self.assertAlmostEqual(shifted.iloc[2].battery_soc_usable_kwh,
                               o.iloc[2].battery_soc_usable_kwh+(x+y)/a.nov.ETA_BAT)
        self.assertAlmostEqual(shifted.iloc[3].battery_soc_usable_kwh,
                               o.iloc[3].battery_soc_usable_kwh+y/a.nov.ETA_BAT)
        self.assertAlmostEqual(shifted.iloc[4].battery_soc_usable_kwh,
                               o.iloc[4].battery_soc_usable_kwh)

    def test_source_transfer_discharge_too_large_rejected(self):
        o=base_6()
        with self.assertRaisesRegex(ValueError,"more than original"):
            a.nov.transfer(o,"2025-11-29 17:00:00","2025-11-29 19:00:00",3.)

    def test_cyclic_2025_annual_data_still_required(self):
        with self.assertRaisesRegex(ValueError,"Annual 2025 hourly"):
            a.nov.check_year(base_6(),6,8.55,10.)

    def test_events_do_not_claim_independent_additivity(self):
        self.assertTrue(a.nov.ETA_BAT<1.)
        self.assertAlmostEqual(a.nov.PHYSICAL_FLOOR_MODEL_PER_MODULE,.229)

    def test_actual_names_are_source_scope_limited(self):
        self.assertEqual(a.CASE,"A1_94022_ss90_to_A0")
        self.assertEqual(a.BASELINE.name,"StudyA_94022_SS90_MarNov_AnnualAC_PF98_v1")
        self.assertIn("Remaining3",a.OUT_PREFIX)

    def test_wrong_event_layout_duplicate_source_refused(self):
        invalid=(
          ("nov16","2025-11-16 19:00:00","2025-11-16 20:00:00"),
          ("nov29_19","2025-11-29 17:00:00","2025-11-29 19:00:00"),
          ("nov29_20","2025-11-29 17:00:00","2025-11-29 20:00:00"))
        with self.assertRaisesRegex(ValueError,"distinct unique"):
            a.check_event_layout(invalid)

    def test_wrong_event_layout_nonsame_day_refused(self):
        invalid=(
          ("nov16","2025-11-16 19:00:00","2025-11-17 20:00:00"),
          *a.EVENTS[1:])
        with self.assertRaisesRegex(ValueError,"same-day"):
            a.check_event_layout(invalid)


if __name__=="__main__":
    unittest.main()
