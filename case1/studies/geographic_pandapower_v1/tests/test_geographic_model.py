import sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from topology import read_evidence, choose_assignments, build_territories, TRAFO_ORDER
from run_geo_validation import stress_hours,load_weights,load_profile
import numpy as np
import pandas as pd

class GeographicalTopologyTests(unittest.TestCase):
    def test_all_assets_and_houses(self):
        h,t=read_evidence()
        self.assertEqual(len(h),35);self.assertEqual(len(t),7)
        self.assertEqual(t['98380']['epm_node'],'241054')
        self.assertAlmostEqual(t['98380']['lat'],6.237093826)
        self.assertEqual(h['H08']['trafo'],'98380')
        self.assertEqual([(x.name,len(x.houses)) for x in build_territories()],
           [('94022',10),('106039',12),('92395',4),('85398',4),('113699',4),('98380',1),('NORTH_25KVA',0)])

    def test_alt_assignments_preserve_all_houses(self):
        h,_=read_evidence()
        for alt in ['base','north','h10','h29','all_alternates']:
            a=choose_assignments(h,alt)
            self.assertEqual(set(a),set(h))
            self.assertEqual(sum(len(t.houses) for t in build_territories(alt)),35)
        a=choose_assignments(h,'north')
        self.assertEqual(a['H01']['trafo'],'NORTH_25KVA')
        self.assertEqual(a['H02']['trafo'],'NORTH_25KVA')

    def test_radial_edges_and_siting(self):
        for routing in ('mst','star'):
            for t in build_territories(routing=routing):
                self.assertEqual(len(t.parent),len(t.houses))
                if t.houses:
                    self.assertGreater(t.max_m,0)
                    self.assertGreaterEqual(t.total_m,t.max_m-1e-8)
                    self.assertEqual(t.siting_house('end'),t.farthest)
                    self.assertIsNone(t.siting_house('head'))
                    self.assertIn(t.siting_house('middle'),t.houses)
                    for h in t.houses:
                        seen=set();k=h
                        while k!='TRAFO':
                            self.assertNotIn(k,seen);seen.add(k);k=t.parent[k]
                    weights=load_weights(t,'far_end_heavy')
                    self.assertAlmostEqual(sum(weights.values()),1.)

    def test_length_multiplier_is_electrical_not_coordinate_shift(self):
        a=build_territories(route_factor=1)[0]
        b=build_territories(route_factor=1.5)[0]
        self.assertAlmostEqual(b.total_m,1.5*a.total_m)
        self.assertEqual(a.transformer['lat'],b.transformer['lat'])

    def test_synthetic_profile_validation(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            df=pd.DataFrame({'timestamp_lst':pd.date_range('2025-01-01',periods=8760,freq='h'),
                             'demand_kw':np.full(8760,1.0),'inverter_ac_kw':np.zeros(8760),
                             'grid_import_kw':np.ones(8760),'grid_export_kw':np.zeros(8760)})
            df.to_csv(p/'5_homes_hourly_dispatch.csv',index=False)
            x,label=load_profile(4,'gross',p,{})
            self.assertEqual(len(x),8760)
            self.assertAlmostEqual(float(x.demand_kw.iloc[0]),.8)
            self.assertIn('PROXY',label)
            y,reason=load_profile(4,'optimized',p,{})
            self.assertIsNone(y);self.assertIn('NO_OPTIMIZED',reason)
            self.assertGreater(len(stress_hours(x)),0)

if __name__=='__main__':unittest.main()
