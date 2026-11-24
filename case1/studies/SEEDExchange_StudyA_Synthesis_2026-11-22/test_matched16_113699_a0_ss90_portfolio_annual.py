"""Source-only sample identity regression tests."""
import unittest
import matched16_113699_a0_ss90_portfolio_annual as a
class Contract(unittest.TestCase):
    def fixture(self):
        p=[{"case":a.CASE,"timestamp_lst":f"2025-01-{i+1:02d} 20:00:00"} for i in range(25)]
        rows=[{**r,"pf":".98","source_sha256":"example","status":"CONVERGED","ac_feasible":"True"} for r in p]
        return rows,p
    def test_exact_benchmarks(self):
        r,p=self.fixture();self.assertEqual(len(a.select_benchmarks(r,p,"example")),25)
    def test_duplicate_rejected(self):
        r,p=self.fixture()
        with self.assertRaisesRegex(ValueError,"exact 25"):a.select_benchmarks(r+[r[0]],p,"example")
    def test_wrong_pf_rejected(self):
        r,p=self.fixture();r[0]["pf"]=".95"
        with self.assertRaisesRegex(ValueError,"exact 25"):a.select_benchmarks(r,p,"example")
    def test_wrong_source_rejected(self):
        r,p=self.fixture();r[0]["source_sha256"]="wrong"
        with self.assertRaisesRegex(ValueError,"source or pass"):a.select_benchmarks(r,p,"example")
if __name__=="__main__":unittest.main()
