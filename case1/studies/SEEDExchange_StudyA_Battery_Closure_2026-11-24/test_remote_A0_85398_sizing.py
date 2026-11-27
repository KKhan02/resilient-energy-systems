import unittest
import remote_85398_A0_sizing as r

class CandidateGate(unittest.TestCase):
    def reference(self):
        return dict(zip(("pv_panels","battery_modules","battery_power_dc_kw","inverter_kva","transformer_kva_assumed_or_evidenced"),r.REF_HW))
    def test_exact_plan(self):
        d=r.new_designs(self.reference())
        self.assertEqual([(h["pv_panels"],h["battery_modules"]) for h in d.values()],[(18,5),(17,5),(16,5),(20,4),(17,4)])
        self.assertTrue(all(h["inverter_kva"]==6 and h["battery_power_dc_kw"]==r.REF_HW[2] for h in d.values()))
    def test_archive_naming(self):
        self.assertEqual(r.archive_key("A0_85398_ss90_ref",.95,1.6),"A0_85398_ss90_ref_mapped_optimized_pf095_length16_annual8760")
        self.assertEqual(r.archive_key("A0_85398_min_cost_four",1.,1.),"A0_85398_min_cost_four_mapped_optimized_pf100_length10_annual8760")
    def test_reference_gate(self):
        h=self.reference();h["battery_modules"]=4
        with self.assertRaisesRegex(ValueError,"Reference hardware"):r.new_designs(h)
    def test_duplicate_gate(self):
        d=r.new_designs(self.reference())
        with self.assertRaisesRegex(ValueError,"Duplicate"):r.prior.duplicate_guard(d,{"old":next(iter(d.values()))})
    def test_archive_population(self):
        self.assertEqual(set(r.ARCHIVE_FAMILY),set(r.EXPECTED))
        self.assertEqual(len(r.FACTORS)*len(r.ARCHIVE_FAMILY),36)

    def test_native_four_house_schema(self):
        h=dict(pv_panels=17,battery_modules=3,battery_power_dc_kw=5.76,inverter_kva=5.,transformer_kva_assumed_or_evidenced=5.)
        m=dict(status="OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION",export_policy="zero",panels_equivalent=17,
            battery_modules_equivalent=3,battery_power_dc_kw=5.76,inverter_ac_kva_assumed_unity_pf=5.,
            transformer_assumed_kva=5.,grid_import_kwh=763.8373264560142,annual_grid_import_usd=221.5128246722441,
            annual_equipment_usd=1413.254355078876,annual_total_usd=1634.76717975112)
        receipt=dict(status="FULL_8760H_NEW_FOUR_HOUSE_MILP_ENERGY_ONLY_NOT_AC_VALIDATED",
            hardware_reoptimized=True,hardware=h,model_summary=m)
        self.assertEqual(r.native_model_summary(receipt),m)
        with self.assertRaisesRegex(ValueError,"hardware mismatch"):
            r.native_model_summary(dict(receipt,model_summary=dict(m,battery_modules_equivalent=4)))
        with self.assertRaisesRegex(ValueError,"cost mismatch"):
            r.native_model_summary(dict(receipt,model_summary=dict(m,annual_total_usd=0)))
        with self.assertRaisesRegex(ValueError,"manifest type"):
            r.native_model_summary(dict(receipt,hardware_reoptimized=False))

if __name__=="__main__":unittest.main()
