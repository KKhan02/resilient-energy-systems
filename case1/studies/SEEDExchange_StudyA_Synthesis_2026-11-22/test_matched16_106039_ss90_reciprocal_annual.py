"""Cached pair identity and flag guards. No solver."""
import unittest
import matched16_106039_ss90_reciprocal_annual as a
class Contract(unittest.TestCase):
    def fixture(self):
        c=a.CASES[0];d,t=a.thermal.EVENTS[c][0]
        rows=[{"case":c,"donor_time":d,"target_time":t,"point":point,"timestamp_lst":stamp,"fraction":"0.25","pf":"0.98"} for point,stamp in (("donor",d),("target",t))]
        return c,d,t,rows
    def test_exact_pair(self):
        c,d,t,rows=self.fixture()
        self.assertEqual(set(a.select_pair(rows,c,d,t,.25)),{d,t})
    def test_duplicate_rejected(self):
        c,d,t,rows=self.fixture()
        with self.assertRaisesRegex(ValueError,"duplicate"):a.select_pair(rows+[rows[0]],c,d,t,.25)
    def test_wrong_pf_rejected(self):
        c,d,t,rows=self.fixture();rows[0]["pf"]="0.95"
        with self.assertRaisesRegex(ValueError,"Missing"):a.select_pair(rows,c,d,t,.25)
    def test_flag(self):
        self.assertTrue(a.bool_ac("True"));self.assertFalse(a.bool_ac("False"))
        with self.assertRaises(ValueError):a.bool_ac("unknown")
if __name__=="__main__":unittest.main()
