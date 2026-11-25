import unittest
from types import SimpleNamespace
import sizing_matched_physical_options as m

class AnnualSampleRegression(unittest.TestCase):
    def test_matching_strict_flag(self):
        calls=[]
        a=SimpleNamespace(exact_ac_regression=lambda q,r,c:calls.append(c))
        m.exact_sample_row(a,{"strict_feasible":True},{"strict_feasible":True},"sample")
        self.assertEqual(calls,["sample"])
    def test_changed_strict_flag(self):
        a=SimpleNamespace(exact_ac_regression=lambda *args:None)
        with self.assertRaisesRegex(ValueError,"strict feasibility changed"):
            m.exact_sample_row(a,{"strict_feasible":False},{"strict_feasible":True},"sample")
    def test_annual_plan(self):
        p=m.plan(["middle","head_hypothetical_R050"],m.CASES,[(.95,1.6)],8760)
        self.assertEqual(len(p),6)
        self.assertEqual(sum(z[-1] for z in p),52560)

if __name__=="__main__":unittest.main()
