import unittest
import remote_94022_A1_sizing as r

class CandidatePlan(unittest.TestCase):
    def reference(self):
        return dict(zip(("pv_panels","battery_modules","battery_power_dc_kw","inverter_kva","transformer_kva_assumed_or_evidenced"),r.REF_HW))
    def test_exact_plan(self):
        d=r.new_designs(self.reference())
        self.assertEqual(len(d),5)
        self.assertEqual([(h["pv_panels"],h["battery_modules"]) for h in d.values()],[(37,8),(34,8),(30,8),(41,7),(34,7)])
        self.assertTrue(all(h["inverter_kva"]==12. and h["battery_power_dc_kw"]==r.REF_HW[2] for h in d.values()))
    def test_reference_gate(self):
        h=self.reference();h["battery_modules"]=7
        with self.assertRaisesRegex(ValueError,"Reference hardware"):r.new_designs(h)
    def test_no_duplicates(self):
        h=self.reference();d=r.new_designs(h);r.duplicate_guard(d,{"ref":h})
    def test_duplicate_gate(self):
        h=self.reference();d=r.new_designs(h)
        with self.assertRaisesRegex(ValueError,"Duplicate"):r.duplicate_guard(d,{"existing":next(iter(d.values()))})

    def test_preflight_metadata_contract(self):
        from types import ModuleType
        context={"signatures":{"ref":"signed-source"},"candidates":{"P37":{"pv_panels":37}}}
        prepared=(ModuleType("fixed"),ModuleType("v6"),ModuleType("annual"),context)
        receipt=r.preflight_metadata(prepared)
        self.assertEqual(receipt["existing_energy_hashes"],{"ref":"signed-source"})
        self.assertEqual(receipt["new_hardware"],{"P37":{"pv_panels":37}})
        self.assertEqual(receipt["planned_archived_regressions"],100)
        context["signatures"]["new"]="new-output"
        context["candidates"]["P37"]["pv_panels"]=99
        self.assertEqual(receipt["existing_energy_hashes"],{"ref":"signed-source"})
        self.assertEqual(receipt["new_hardware"],{"P37":{"pv_panels":37}})

if __name__=="__main__":unittest.main()
