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

if __name__=="__main__":unittest.main()
