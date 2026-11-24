"""No-solver synthetic guards for annual AC source/changed-hour reconstruction."""
import unittest
import matched16_94022_ss90_mar_nov_annual_ac as a


def point(ts, minv=.97, feasible=True,loss=1.,tf=40.):
    return {"timestamp_lst":ts,"status":"CONVERGED","ac_feasible":feasible,
            "min_v_pu":minv,"max_v_pu":1.01,"max_trafo_pct":tf,"max_line_pct":20,
            "loss_kw":loss,"pcc_kva":2,"q_selected_kvar":0,
            "voltage_below_095":int(minv<.95),"voltage_above_105":0,
            "voltage_below_097":int(minv<.97),"voltage_above_103":0,
            "trafo_over_100":int(tf>100),"line_over_100":0,
            "gross_demand_kw":3,"inverter_ac_kw":1}


class AnnualReconstructionTests(unittest.TestCase):
    def test_exact_four_source_hours(self):
        self.assertEqual(len(a.CHANGED),4)
        self.assertEqual(a.CHANGED,tuple(sorted(a.CHANGED)))
        self.assertEqual(len(set(a.CHANGED)),4)

    def test_ref_source_fractions(self):
        self.assertAlmostEqual(a.MARCH_FRACTION,.5)
        self.assertAlmostEqual(a.NOV_FRACTION,.98)
        self.assertEqual(a.PF_OPTIONS,(.98,.95))

    def test_archive_resolver_rejects_missing_sample(self):
        with self.assertRaisesRegex(ValueError,"Missing/duplicate"):
            a.unique_archived([],a.combined.CASE,a.CHANGED[0],.98,.5,"donor")

    def test_archive_resolver_accepts_one(self):
        row={"case":a.combined.CASE,"timestamp_lst":a.CHANGED[0],"pf":".98",
             "fraction":".50","point":"donor"}
        self.assertEqual(a.unique_archived([row],a.combined.CASE,a.CHANGED[0],.98,.5,"donor"),row)

    def test_archive_resolver_rejects_duplicate_sample(self):
        row={"case":a.combined.CASE,"timestamp_lst":a.CHANGED[0],"pf":".98",
             "fraction":".50","point":"donor"}
        with self.assertRaisesRegex(ValueError,"Missing/duplicate"):
            a.unique_archived([row,row],a.combined.CASE,a.CHANGED[0],.98,.5,"donor")

    def test_exact_hourly_ac_comparison_accepts_equal(self):
        x=point("2025-03-28 17:00:00")
        a.exact_ac_regression(x,dict(x),"synthetic")

    def test_exact_hourly_ac_comparison_rejects_voltage_mismatch(self):
        x=point("2025-03-28 17:00:00")
        y=dict(x,min_v_pu=.96)
        with self.assertRaisesRegex(ValueError,"quantity changed"):
            a.exact_ac_regression(x,y,"synthetic")

    def test_exact_hourly_ac_comparison_rejects_feasibility_mismatch(self):
        x=point("2025-03-28 17:00:00")
        y=dict(x,ac_feasible=False)
        with self.assertRaisesRegex(ValueError,"feasible changed"):
            a.exact_ac_regression(x,y,"synthetic")

    def test_full_year_summary_fail_low_voltage(self):
        rows=[point(f"2025-{m:02d}-{h:02d}") for m in range(1,2) for h in range(1,2)]
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            a.annual_summary(rows)

    def test_no_annual_ac_in_preflight_source(self):
        self.assertIn("ANNUAL_AC_PREFLIGHT_ZERO_NEW_AC","SIGNED_94022_SS90_MAR50_NOV98_ANNUAL_AC_PREFLIGHT_ZERO_NEW_AC")


    def test_full_year_metrics_one_voltage_failure(self):
        import pandas as pd
        ts=pd.date_range("2025-01-01",periods=a.HOURS,freq="h")
        records=[point(str(v)) for v in ts]
        records[13]["min_v_pu"]=.94
        records[13]["ac_feasible"]=False
        records[13]["voltage_below_095"]=1
        records[13]["voltage_below_097"]=1
        stats=a.annual_summary(records)
        self.assertEqual(stats["case_hour_records"],8760)
        self.assertEqual(stats["converged_hours"],8760)
        self.assertEqual(stats["main_band_infeasible_hours"],1)
        self.assertEqual(stats["undervoltage_under_095_hours"],1)
        self.assertFalse(stats["all_2025_model_main_band_pass"])
        self.assertAlmostEqual(stats["annual_ac_network_losses_kwh"],8760.)

    def test_annual_summary_marks_nonconvergence_incomplete(self):
        import pandas as pd
        ts=pd.date_range("2025-01-01",periods=a.HOURS,freq="h")
        records=[point(str(v)) for v in ts]
        records[12]["status"]="AC_FAILURE"
        records[12]["ac_feasible"]=False
        records[12]["min_v_pu"]=None
        records[12]["voltage_below_095"]=None
        records[12]["voltage_below_097"]=None
        stats=a.annual_summary(records)
        self.assertEqual(stats["nonconverged_hours"],1)
        self.assertIsNone(stats["annual_ac_network_losses_kwh"])
        self.assertFalse(stats["all_2025_model_main_band_pass"])


    def test_november_identical_hour_pf_fraction_selects_ss90_not_min_cost(self):
        ss90={"case":a.combined.CASE,"timestamp_lst":"2025-11-27 20:00:00",
              "pf":"0.98","fraction":"0.98","point":"target",
              "inverter_ac_kw":"1.7853624109447"}
        minimum=dict(ss90,case="A1_94022_min_cost_to_A0",
                     inverter_ac_kw="0.10742439635059998")
        found=a.unique_archived([minimum,ss90],a.combined.CASE,
             "2025-11-27 20:00:00",.98,.98,"target")
        self.assertIs(found,ss90)
        self.assertAlmostEqual(float(found["inverter_ac_kw"]),1.7853624109447)

    def test_wrong_hardware_case_cannot_satisfy_archived_lookup(self):
        minimum={"case":"A1_94022_min_cost_to_A0",
                 "timestamp_lst":"2025-11-27 20:00:00",
                 "pf":"0.98","fraction":"0.98","point":"target"}
        with self.assertRaisesRegex(ValueError,"Missing/duplicate"):
            a.unique_archived([minimum],a.combined.CASE,
                 "2025-11-27 20:00:00",.98,.98,"target")

    def test_same_hardware_duplicate_at_nov_target_is_rejected(self):
        ss90={"case":a.combined.CASE,"timestamp_lst":"2025-11-27 20:00:00",
              "pf":"0.98","fraction":"0.98","point":"target"}
        with self.assertRaisesRegex(ValueError,"Missing/duplicate"):
            a.unique_archived([ss90,dict(ss90)],a.combined.CASE,
                 "2025-11-27 20:00:00",.98,.98,"target")

    def test_case_argument_required(self):
        with self.assertRaisesRegex(ValueError,"explicit archived hardware case"):
            a.unique_archived([],None,"2025-11-27 20:00:00",.98,.98,"target")


if __name__=="__main__":
    unittest.main()
