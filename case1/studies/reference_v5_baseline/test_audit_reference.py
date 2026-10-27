import json
import tempfile
import unittest
from pathlib import Path
from audit_reference import calculate,run,HERE

class AuditedV5ReferenceTests(unittest.TestCase):
    def test_stored_reference_bounds(self):
        a,s=calculate()
        self.assertEqual([r[0] for r in a],list(range(1,21)))
        self.assertEqual(s["first_voltage_screen_failure_homes"],6)
        self.assertEqual(s["first_nominal_transformer_overload_homes"],9)
        self.assertAlmostEqual(float(a[7][3]),0.951985249,places=5)
        self.assertEqual(a[7][5:7],["false","true"])
    def test_committed_data_generated_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            run(Path(d))
            for fn in ("v5_existing_reference_limits.csv","audit_summary.json"):
                self.assertEqual((Path(d)/fn).read_bytes(),(HERE/fn).read_bytes())
