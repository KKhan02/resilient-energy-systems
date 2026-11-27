import unittest
import remote_85398_A0_annual as r

class AnnualGate(unittest.TestCase):
    def test_exact_plan(self):
        r.plan_gate()
        self.assertEqual(len(r.CASES)*len(r.FACTORS)*8760,87600)
        self.assertEqual(len(r.PRIOR)*41,410)
    def test_source_disjoint(self):
        self.assertFalse(set(r.CASES)&set(r.src.EXPECTED))
    def test_archive_gate(self):
        rows=[]
        for k,v in r.ARCHIVE.items():
            c,p,l=k.split("|")
            rows.append(dict(case=c,pf=float(p),length_factor=float(l),source_ac_sha256=v,strict_failures=0,converged=8760))
        r.archive_gate(dict(archive_receipts=rows))
        rows[0]["strict_failures"]=1
        with self.assertRaisesRegex(ValueError,"Archive identity"):
            r.archive_gate(dict(archive_receipts=rows))
    def test_sample_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"strict_failures"):
            r.runner.sample_regression({"strict_failures":1},{"strict_failures":0})

if __name__=="__main__":unittest.main()
