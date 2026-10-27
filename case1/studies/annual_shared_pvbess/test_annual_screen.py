import unittest
from annual_screen import territories,hourly,banks,simulate,study
class AnnualSharedPVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=hourly()
    def test_houses_and_known_rating_scope(self):
        t=territories()
        self.assertEqual(sum(map(len,t.values())),31)
        self.assertEqual(len(t["931076"]),7)
        self.assertEqual(len(t["923494"]),12)
    def test_matching_equipment_two_multi_house_sites(self):
        a=banks(7,24,4,5,"C")
        b=banks(7,24,4,5,"K")
        for k in ("pv","mods","power","ic"):
            self.assertEqual(sum(x[k] for x in a),sum(x[k] for x in b))
        self.assertTrue(all(len(x["ids"])>=2 for x in b))
    def test_no_der_has_no_pv_bess_bos(self):
        a=simulate(self.data,7,0,0,0,"C",0)
        self.assertEqual(a["cost_annual_usd_mid_BOS"],a["cost_annual_usd_low_BOS"])
        self.assertEqual(a["cost_annual_usd_mid_BOS"],a["cost_annual_usd_high_BOS"])
        self.assertAlmostEqual(a["cost_annual_usd_mid_BOS"],a["grid_import_kwh"]*.29,places=1)
    def test_storage_balance_and_export_cap(self):
        a=simulate(self.data,7,24,4,5,"C",0)
        self.assertEqual(a["grid_export_kwh"],0)
        self.assertLess(a["grid_import_kwh"],a["load_kwh"])
        self.assertGreater(a["battery_discharge_kwh"],0)
    def test_committed_annual_data_traceable(self):
        import csv,json
        from annual_screen import HERE
        with (HERE/"outputs/annual_scenarios.csv").open(newline="",encoding="utf-8") as f:
            saved=list(csv.DictReader(f))
        m=json.loads((HERE/"outputs/manifest.json").read_text())
        self.assertEqual(len(saved),386)
        self.assertEqual(m["total_unique_candidates"],31)
        self.assertTrue(all(r["lv_voltage_status"]=="NOT_SIMULATED" for r in saved))
        base=next(r for r in saved if r["epm_node"]=="931076" and r["pv_panels"]=="0" and r["battery_modules"]=="0")
        self.assertAlmostEqual(float(base["cost_annual_usd_mid_BOS"]),float(base["grid_import_kwh"])*.29,places=1)
    def test_study_scope_and_cost_uncertainty(self):
        a,m=study()
        self.assertGreater(len(a),200)
        self.assertEqual(m["total_unique_candidates"],31)
        self.assertTrue(all(x["lv_voltage_status"]=="NOT_SIMULATED" for x in a))
        self.assertTrue(all(x["cost_annual_usd_high_BOS"]>=x["cost_annual_usd_mid_BOS"]>=x["cost_annual_usd_low_BOS"] for x in a))
