import unittest
import sizing_matched_physical_options as m
class PlanTests(unittest.TestCase):
    def test_sample(self):
        p=m.plan(m.OPTIONS,m.CASES,m.nf.FACTORS,67)
        self.assertEqual(len(p),81)
        self.assertEqual(sum(z[-1] for z in p),5427)
    def test_annual_selection(self):
        p=m.plan(["middle"],[m.CASES[0]],[(.95,1.6)],8760)
        self.assertEqual(len(p),1)
        self.assertEqual(p[0][-1],8760)
if __name__=="__main__":unittest.main()
