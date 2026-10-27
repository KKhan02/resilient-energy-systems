import unittest
from conditional_powerflow import house_points,length_m,source_hours,make_network,solve,STAMPS,HOUSE_IDS
class ConditionalPowerflowChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.points=house_points();cls.hour=source_hours()
    def test_house_ids_and_distance_limits(self):
        self.assertEqual(len(self.points),7)
        self.assertEqual(sorted(self.points),sorted(HOUSE_IDS))
        for p in self.points.values():
            self.assertGreater(length_m(p,"euclidean"),0)
            self.assertGreaterEqual(length_m(p,"rectilinear"),length_m(p,"euclidean"))
    def test_single_original_transformer(self):
        net,buses,loads,lines,inverters=make_network(self.points,"euclidean","shared_two_sites")
        self.assertEqual(len(net.trafo),1)
        self.assertAlmostEqual(float(net.trafo.sn_mva.iloc[0]),.015)
        self.assertEqual(len(lines),7)
        self.assertEqual(len(inverters),2)
    def test_two_shared_sites_same_total_power_as_central(self):
        a=solve(self.points,self.hour[STAMPS[0]],"euclidean","central","storage",bess_kw=2)
        b=solve(self.points,self.hour[STAMPS[0]],"euclidean","shared_two_sites","storage",bess_kw=2)
        self.assertAlmostEqual(a["actual_injection_kw"],b["actual_injection_kw"])
        self.assertTrue(0<a["min_lv_pu"]<2)
        self.assertTrue(0<b["min_lv_pu"]<2)
    def test_export_cap_not_higher_than_total_house_demand(self):
        a=solve(self.points,self.hour[STAMPS[1]],"euclidean","central","pv",pv_kwp=10.44,export="gross_load_capped")
        self.assertLessEqual(a["actual_injection_kw"],sum(self.hour[STAMPS[1]]["house_kw"])+1e-6)
        self.assertLessEqual(a["actual_injection_kw"],5.)
    def test_committed_ac_outputs_match_recomputed_study(self):
        import csv
        from pathlib import Path
        from conditional_powerflow import study
        rows, distances=study()
        base=Path(__file__).resolve().parent/"results"
        with (base/"conditional_snapshots.csv").open(newline="",encoding="utf-8") as f:
            committed=list(csv.DictReader(f))
        self.assertEqual(len(rows),36)
        self.assertEqual(len(committed),36)
        for simulated, saved in zip(rows, committed):
            self.assertEqual(simulated["screen_pass"], saved["screen_pass"]=="True")
            self.assertEqual(simulated["architecture"],saved["architecture"])
            self.assertEqual(simulated["distance"],saved["distance"])
            self.assertAlmostEqual(simulated["min_lv_pu"],float(saved["min_lv_pu"]),places=5)
            self.assertAlmostEqual(simulated["max_lv_pu"],float(saved["max_lv_pu"]),places=5)
            self.assertAlmostEqual(simulated["trafo_loading_pct"],float(saved["trafo_loading_pct"]),places=4)
        with (base/"distance_sensitivity.csv").open(newline="",encoding="utf-8") as f:
            saved_dist=list(csv.DictReader(f))
        self.assertEqual(len(saved_dist),7)
        for new, old in zip(distances,saved_dist):
            self.assertEqual(new["house_id"],old["house_id"])
            self.assertAlmostEqual(new["rectilinear_m"],float(old["rectilinear_m"]),places=3)

if __name__=="__main__":unittest.main()
