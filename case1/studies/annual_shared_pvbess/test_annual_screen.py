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
    def test_storage_balance_and_export_cap(self):
        a=simulate(self.data,7,24,4,5,"C",0)
        self.assertEqual(a["grid_export_kwh"],0)
        self.assertLess(a["grid_import_kwh"],a["load_kwh"])
        self.assertGreater(a["battery_discharge_kwh"],0)
    def test_study_scope_and_cost_uncertainty(self):
        a,m=study()
        self.assertGreater(len(a),200)
        self.assertEqual(m["total_unique_candidates"],31)
        self.assertTrue(all(x["lv_voltage_status"]=="NOT_SIMULATED" for x in a))
        self.assertTrue(all(x["cost_annual_usd_high_BOS"]>=x["cost_annual_usd_mid_BOS"]>=x["cost_annual_usd_low_BOS"] for x in a))
