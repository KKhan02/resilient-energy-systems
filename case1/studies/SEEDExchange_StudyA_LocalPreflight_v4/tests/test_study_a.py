import sys
from pathlib import Path
import unittest
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0,str(SCRIPT_DIR))
import prepare_study_a as a

class SourceAndMappingTests(unittest.TestCase):
    def test_excel_homer_seasonal_shapes_match_to_rounding(self):
        rows,summary = a.compare_sources(a.workbook_raw_profiles(),a.xml_load_model()[0])
        self.assertEqual(len(rows),288)
        self.assertEqual(len(summary),12)
        self.assertLess(max(r['hourly_max_abs_diff_kw'] for r in summary),0.00013)
        self.assertAlmostEqual(summary[0]['excel_kwh_per_day'],5.122011712589554,places=10)
        self.assertAlmostEqual(summary[8]['excel_kwh_per_day'],5.952337830060126,places=10)

    def test_original_twenty_homer_profile_first_hour(self):
        df,target = a.make_profiles('homer')
        self.assertEqual(len(df),8760)
        self.assertAlmostEqual(target,1898.0,places=10)
        self.assertAlmostEqual(df.at[0,'house_1_kw'],0.2458162731563198,places=13)
        self.assertAlmostEqual(df.at[0,'house_2_kw'],0.1865510063479185,places=13)
        self.assertAlmostEqual(df.at[1,'house_1_kw'],0.1818704952568726,places=13)

    def test_unique_fixed_assignment_preserves_saved_7_9_12(self):
        sample=[{'house_id':f'H{i:02d}'} for i in range(1,36)]
        mapping=a.fixed_house_profile_mapping(sample)
        self.assertEqual(len(set(mapping.values())),35)
        for idx,hid in enumerate(a.CORE7,1):self.assertEqual(mapping[hid],idx)
        self.assertEqual(mapping['H01'],8)
        self.assertEqual(mapping['H02'],9)
        self.assertEqual(mapping['H11'],10)
        self.assertEqual(mapping['H25'],21)

    def test_excludes_northern_25kva_and_tracks_expected_moves(self):
        positions={
            '94022':(6.24695,-75.00621), '106039':(6.24284,-75.00481),
            '113699':(6.24343,-75.00813), '85398':(6.23778,-75.00292),
            '92395':(6.24706,-75.001), '98380':(6.23709,-75.0126),
        }
        original={'H03':'94022','H06':'94022','H13':'106039'}
        for h in a.CORE7 + a.CORE9_MORE:original[h]='94022'
        for h in a.CORE12:original[h]='106039'
        for n in range(1,36):
            h=f'H{n:02d}'
            original.setdefault(h,'113699' if n in (4,5,7,10) else '85398' if n in (9,12,14,15) else '92395' if n in (30,31,32,33) else '98380' if n==8 else '94022')
        houses=[]
        for hid,t in sorted(original.items()):
            physical = a.CANDIDATE_MOVES.get(hid,t)
            lat,lon=positions[physical]
            houses.append(dict(house_id=hid,latitude=lat,longitude=lon,transformer_number=t,assignment_status='possible'))
        trafos=[dict(transformer_number=k,latitude=lat,longitude=lon) for k,(lat,lon) in positions.items()]
        trafos.append(dict(transformer_number='NORTH_25KVA',latitude=6.25,longitude=-75.01))
        rows=a.paired_assignments(houses,trafos)
        self.assertEqual(len(rows),70)
        changed=[(r['house'],r['transformer']) for r in rows if r['scenario']=='A1_nearest_point' and r['changed_from_original']]
        self.assertEqual(dict(changed),a.CANDIDATE_MOVES)
        self.assertTrue(all(r['transformer']!='NORTH_25KVA' for r in rows))

    def test_gross_load_is_only_scalar_pf_screen(self):
        import pandas as pd
        profiles=pd.DataFrame({'timestamp':pd.date_range('2025-01-01',periods=8760,freq='h')})
        mapping={f'H{i:02d}':i for i in range(1,36)}
        for i in range(1,36):profiles[f'house_{i}_kw']=np.full(8760,0.1)
        assignments=[]
        for sc in ('A0_original','A1_nearest_point'):
            for h in mapping:assignments.append(dict(scenario=sc,house=h,transformer='94022'))
        rating={k:5 for k in a.MAIN_TRAFO_IDS}
        rows,_=a.build_gross_screen(profiles,assignments,mapping,rating,'test')
        self.assertEqual(len(rows),2*6*3)
        testrow=next(r for r in rows if r['transformer']=='94022' and r['load_pf']==.95)
        self.assertEqual(testrow['gross_exceedance_hours'],0)
        self.assertAlmostEqual(testrow['gross_peak_kva'],3.5/.95,places=8)
        self.assertIn('NOT_AC',testrow['result_type'])

if __name__=='__main__':unittest.main()
