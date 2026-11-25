import unittest
import pandas as pd
from reserve_full_night import interval,intersect,changed_mask,strict_point,zero_archive,CASES
class NightTests(unittest.TestCase):
    def test_interval(self):
        a=interval(lambda p:p>=.6,2.)
        self.assertGreater(a[0],.6)
        self.assertLess(a[0],.62)
        self.assertEqual(a[1],2.)
    def test_no_upper_segment(self):
        self.assertIsNone(interval(lambda p:p<1.,2.))
    def test_intersect(self):
        self.assertEqual(intersect((1,3),(2,4)),(2,3))
        with self.assertRaises(ValueError):intersect((1,2),(3,4))
    def test_exact_change(self):
        a=pd.DataFrame(dict(demand_kw=[1.,1.],pv_dc_available_kw=[0.,0.],inverter_ac_kw=[.5,.5]))
        b=a.copy();b.loc[1,"inverter_ac_kw"]+=1e-12
        self.assertEqual(changed_mask(a,b).tolist(),[False,True])
        b.loc[0,"demand_kw"]+=1e-12
        with self.assertRaises(ValueError):changed_mask(a,b)
    def test_strict_threshold(self):
        r=dict(status="CONVERGED",ac_feasible=True,min_v_pu=.9499995,max_v_pu=1.,max_trafo_pct=50.,max_line_pct=10.)
        self.assertFalse(strict_point(r));r["min_v_pu"]=.950001
        self.assertTrue(strict_point(r))
    def test_zero_archive(self):
        rows={c:pd.DataFrame(dict(inverter_ac_kw=[1.],status=["CONVERGED"])) for c in CASES}
        self.assertEqual(zero_archive(0,rows),(None,None))
        rows[CASES[1]].loc[0,"inverter_ac_kw"]=0.
        self.assertEqual(zero_archive(0,rows)[0],CASES[1])
if __name__=="__main__":unittest.main()
