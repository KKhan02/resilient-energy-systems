import unittest
import pandas as pd
import remote_portfolio_loss_overlay as r
class OverlayTests(unittest.TestCase):
    def test_population(self):
        self.assertEqual(len(r.PLAN)*len(r.FACTORS)*8760,70080)
        self.assertEqual(sum(v[3] for k,v in r.PLAN.items() if k!=r.MC0)*4,32)
    def test_changed(self):
        i=pd.date_range("2025-01-01",periods=3,freq="h")
        a=pd.DataFrame(dict(demand_kw=[2.,2.,2.],pv_dc_available_kw=[0.,0.,0.],inverter_ac_kw=[1.,1.,1.]),index=i)
        b=a.copy();b.inverter_ac_kw=[.8,1.2,1.]
        self.assertEqual(list(r.changed(a,b)),list(i[:2]))
        b.iloc[0,0]=3.
        with self.assertRaises(ValueError):r.changed(a,b)
    def test_overlay(self):
        i=pd.date_range("2025-01-01",periods=2,freq="h")
        a=pd.DataFrame(dict(ac_feasible=[True,False],min_v_pu=[.96,.94],max_v_pu=[1.,1.],max_trafo_pct=[50.,60.],max_line_pct=[10.,10.],loss_kw=[.1,.2]),index=i)
        b=r.overlay(a,{i[1]:dict(ac_feasible=True,min_v_pu=.955,loss_kw=.15)})
        self.assertTrue(b.strict_feasible.all())
        self.assertAlmostEqual(b.loss_kw.sum(),.25)
        self.assertAlmostEqual(a.loss_kw.sum(),.3)
if __name__=="__main__":unittest.main()
