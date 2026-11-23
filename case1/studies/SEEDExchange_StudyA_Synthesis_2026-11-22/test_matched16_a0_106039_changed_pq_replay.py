"""Synthetic unit tests for targeted A0 changed-hour P/Q audit, no AC solver."""
import unittest
import matched16_a0_106039_changed_pq_replay as x


class TargetedPQReplayTests(unittest.TestCase):
    def test_expected_family(self):
        self.assertEqual(x.RECIPROCAL,"A1_106039_min_cost_to_A0")

    def test_tolerance_exact_and_bounded(self):
        self.assertTrue(x.check_near(10,10.0001))
        self.assertFalse(x.check_near(10,10.001))

    def test_tolerance_nan_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Nonfinite"):
            x.check_near(float("nan"),10)

    def test_annual_source_comparison(self):
        rec={"status":"CONVERGED","ac_feasible":True,
             "max_trafo_pct":98.00010,
             "min_v_pu":.963123,"q_selected_kvar":0}
        old={"ac_feasible":"True","max_trafo_pct":"98.00000",
             "min_v_pu":".963123","q_selected_kvar":"0"}
        self.assertTrue(x.compare_result(rec,old,
                        ("max_trafo_pct","min_v_pu","q_selected_kvar")))

    def test_reproducing_originally_infeasible_AC_is_valid(self):
        rec={"status":"CONVERGED","ac_feasible":False,
             "max_trafo_pct":103.4916719489, "min_v_pu":.9597}
        old={"status":"CONVERGED","ac_feasible":"False",
             "max_trafo_pct":"103.4916719489","min_v_pu":"0.9597"}
        self.assertTrue(x.compare_result(rec,old,("max_trafo_pct","min_v_pu")))

    def test_original_feasibility_mismatch_fails(self):
        rec={"status":"CONVERGED","ac_feasible":True,"max_trafo_pct":103.49}
        old={"status":"CONVERGED","ac_feasible":"False","max_trafo_pct":"103.49"}
        self.assertFalse(x.compare_result(rec,old,("max_trafo_pct",)))

    def test_failed_source_compare(self):
        rec={"status":"AC_FAILURE","max_trafo_pct":98}
        old={"ac_feasible":"True","max_trafo_pct":"98"}
        self.assertFalse(x.compare_result(rec,old,("max_trafo_pct",)))

    def test_daylight_selection(self):
        s=[{"timestamp_lst":"a","pv_dc_available_kw":"0"},
           {"timestamp_lst":"b","pv_dc_available_kw":"0.25"},
           {"timestamp_lst":"c","pv_dc_available_kw":"0.56"}]
        self.assertEqual(x.choose_hours(s,["a","b","c"],"daylight"),["b","c"])
        self.assertEqual(x.choose_hours(s,["a","b","c"],"all"),["a","b","c"])

    def test_daylight_count_fail(self):
        s=[{"timestamp_lst":"a","pv_dc_available_kw":"0"}]
        with self.assertRaisesRegex(ValueError,"two daylight"):
            x.choose_hours(s,["a"],"daylight")


if __name__=="__main__":
    unittest.main()
