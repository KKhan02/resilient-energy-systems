import sys
import unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import plot_studya_walkthrough as P
import extract_monthly_and_residual as E

class WalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agg,cls.ac,cls.gr,cls.en=P.validate(ROOT/'evidence')
    def test_exact_coverage(self):
        self.assertEqual(len(self.ac),432)
        self.assertEqual(len(self.agg),36)
        self.assertEqual(self.ac.case_identity.nunique(),432)
    def test_reference_comparison(self):
        r=P.exact(self.agg,scenario='A1',tier='ss90',pf=.98,length_factor=1.)
        self.assertEqual(int(r.five_territory_pvbess_transformer_violation_hours),1)
        self.assertEqual(int(r.five_territory_gross_transformer_violation_hours),25)
    def test_stress_coverage(self):
        r=P.exact(self.agg,scenario='A1',tier='ss90',pf=.95,length_factor=1.6)
        self.assertEqual(int(r.five_territory_pvbess_transformer_violation_hours),2)
    def test_routing_physics(self):
        a=self.ac
        r=a[(a.transformer==92395)&(a.topology=='mst')&(a.dispatch=='optimized')&(a.tier=='min_cost')&
            (a.pf==.95)&(a.length_factor==1.6)]
        self.assertEqual(len(r),1)
        self.assertEqual(int(r.iloc[0].infeasible_hours),110)
    def test_topology_sources(self):
        houses,trafos,lv,note=P.backup_geometry()
        self.assertEqual(len(houses),35)
        self.assertEqual(len(trafos),6)
        self.assertEqual(len(lv),30)
        self.assertEqual(len(lv[lv.node==923848]),0)
    def test_monthly_calculation_does_not_mix_dc_ac(self):
        hours=pd.date_range('2025-01-01',periods=8760,freq='h')
        d=pd.DataFrame({'timestamp_lst':hours,'demand_kw':2.,'grid_import_kw':1.,
                        'grid_export_kw':0.,'inverter_ac_kw':1.,'pv_dc_available_kw':4.,
                        'curtailed_pv_dc_kw':.5,'battery_charge_dc_kw':.2,
                        'battery_discharge_dc_kw':.1,'battery_soc_usable_kwh':1.})
        rows=E.monthly_frame(d,'test','causal',{})
        self.assertEqual(len(rows),12)
        self.assertAlmostEqual(sum(x['grid_import_kwh_ac'] for x in rows),8760.)
        self.assertAlmostEqual(rows[0]['self_sufficiency_pct'],50.)
    def test_signatures_required(self):
        with self.assertRaises((AssertionError,FileNotFoundError)):
            E.signed_csv(ROOT,'not_a_case','manifest.json','data.csv','sha256')

if __name__=='__main__':unittest.main()
