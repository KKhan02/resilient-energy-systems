"""Solver-free guards for March source case with November SS90 acceptance retained."""
import math
import unittest
import pandas as pd
import matched16_94022_mar_nov_ss90_ac as run


class MarchNovemberMath(unittest.TestCase):
    def test_fixed_dates_and_hardware(self):
        self.assertEqual(run.CASE,"A1_94022_ss90_to_A0")
        self.assertEqual(run.MARCH_DONOR,"2025-03-28 17:00:00")
        self.assertEqual(run.MARCH_TARGET,"2025-03-28 20:00:00")
        self.assertAlmostEqual(run.NOV_FRACTION,.98)

    def test_bounded_planned_20_case_hours(self):
        self.assertEqual(len(run.MARCH_FRACTIONS)*len(run.PF)*2,20)
        self.assertEqual(run.PF,(.98,.95))
        self.assertEqual(run.MARCH_FRACTIONS,(0.,.25,.5,.75,.98))

    def test_reuses_original_november_without_changing_archive(self):
        self.assertEqual(run.NOV_RUN.name,"StudyA_94022_Nov_DonorTarget_AC_Shift_v1")
        self.assertEqual(run.OUT_PREFIX,"StudyA_94022_MarNov_SS90_DonorTarget_AC_Shift_v")

    def test_archive_rejects_insufficient_rows(self):
        with self.assertRaisesRegex(ValueError,"unique November"):
            run.check_november_archive([], "abc",run.CASE,"2025-11-27 17:00:00",
                                      "2025-11-27 20:00:00",pd.DataFrame())

    def test_archive_rejects_failed_ac_row(self):
        ts1="2025-11-27 17:00:00";ts2="2025-11-27 20:00:00"
        data=pd.DataFrame({"inverter_ac_kw":[1.,2.],
                           "demand_kw":[2.,3.]},
                          index=pd.to_datetime([ts1,ts2]))
        rows=[{"case":run.CASE,"fraction":"0.98","point":point,"pf":str(pf),
               "status":"CONVERGED","ac_feasible":"True",
               "timestamp_lst":t,"original_source_energy_sha256":"abc",
               "gross_demand_kw":str(d),"inverter_ac_kw":str(inv)}
              for point,t,d,inv in (("donor",ts1,2,1),("target",ts2,3,2))
              for pf in (.95,.98)]
        self.assertEqual(len(run.check_november_archive(rows,"abc",run.CASE,ts1,ts2,data)),4)
        rows[1]["ac_feasible"]="False"
        with self.assertRaisesRegex(ValueError,"not aligned"):
            run.check_november_archive(rows,"abc",run.CASE,ts1,ts2,data)

    def test_archive_rejects_changed_november_p(self):
        ts1="2025-11-27 17:00:00";ts2="2025-11-27 20:00:00"
        data=pd.DataFrame({"inverter_ac_kw":[1.,2.],
                           "demand_kw":[2.,3.]},
                          index=pd.to_datetime([ts1,ts2]))
        rows=[{"case":run.CASE,"fraction":"0.98","point":point,"pf":str(pf),
               "status":"CONVERGED","ac_feasible":"True",
               "timestamp_lst":t,"original_source_energy_sha256":"abc",
               "gross_demand_kw":str(d),"inverter_ac_kw":str(inv)}
              for point,t,d,inv in (("donor",ts1,2,1),("target",ts2,3,2))
              for pf in (.95,.98)]
        data.iloc[0,0]=1.1234
        with self.assertRaisesRegex(ValueError,"not aligned"):
            run.check_november_archive(rows,"abc",run.CASE,ts1,ts2,data)

    def test_archive_rejects_duplicate_pf(self):
        ts1="2025-11-27 17:00:00";ts2="2025-11-27 20:00:00"
        data=pd.DataFrame({"inverter_ac_kw":[1.,2.],
                           "demand_kw":[2.,3.]},
                          index=pd.to_datetime([ts1,ts2]))
        rows=[{"case":run.CASE,"fraction":"0.98","point":"donor","pf":"0.95",
               "status":"CONVERGED","ac_feasible":"True",
               "timestamp_lst":ts1,"original_source_energy_sha256":"abc",
               "gross_demand_kw":"2","inverter_ac_kw":"1"}]*4
        with self.assertRaisesRegex(ValueError,"unique November"):
            run.check_november_archive(rows,"abc",run.CASE,ts1,ts2,data)

    def test_original_battery_min_soc_mapping_retained(self):
        self.assertAlmostEqual(run.nov.PHYSICAL_FLOOR_MODEL_PER_MODULE,.229)
        self.assertAlmostEqual(run.nov.ETA_INV,.95)
        self.assertAlmostEqual(run.nov.ETA_BAT,math.sqrt(.95))


if __name__=="__main__":
    unittest.main()
