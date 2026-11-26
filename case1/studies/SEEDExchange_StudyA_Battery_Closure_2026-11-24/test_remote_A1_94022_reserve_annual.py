import unittest
import remote_94022_A1_reserve_annual as r

class AnnualReserveGate(unittest.TestCase):
    def test_exact_plan(self):
        r.plan_gate()
        self.assertEqual(len(r.CASES)*len(r.FACTORS)*8760,105120)
        self.assertEqual(len(r.PRIOR)*91,1092)
    def test_source_disjoint(self):
        self.assertFalse(set(r.CASES)&set(r.prev.SELECTED))
    def test_corrected_identity(self):
        self.assertEqual(len({e["sha"] for e in r.EXPECTED.values()}),6)
        self.assertTrue(all(e["sha"]!=e["source_sha"] for e in r.EXPECTED.values()))
    def test_sample_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"strict_failures"):
            r.prev.sample_regression({"strict_failures":1},{"strict_failures":0})

if __name__=="__main__":unittest.main()
