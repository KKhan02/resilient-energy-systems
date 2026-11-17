"""Small synthetic tests only. NEVER call the historical investment optimizer or AC solver."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from shapely.geometry import LineString
from types import SimpleNamespace
import numpy as np
import pandas as pd

SOURCE = Path(__file__).resolve().parents[1] / 'seed_study_a_v6.py'
spec = importlib.util.spec_from_file_location('seed_study_a_v6', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestIngestion(unittest.TestCase):
    def test_map_unique_and_profile_recognition(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'map.csv'
            pd.DataFrame({'house_id':[f'H{k:02d}' for k in range(1,36)],
                          'profile_index':list(range(1,36))}).to_csv(path,index=False)
            found=mod.load_house_map(path)
            self.assertEqual(found['H01'],1)
            self.assertEqual(found['H35'],35)
            self.assertEqual(mod.profile_number('house_07_kw'),7)
            self.assertEqual(mod.profile_number('profile_11'),11)
            self.assertEqual(mod.profile_number('H06'),6)
            self.assertIsNone(mod.profile_number('DC_PV'))
            bad=pd.read_csv(path,dtype=str)
            bad.loc[1,'profile_index']='1'
            bad.to_csv(path,index=False)
            with self.assertRaises(ValueError):mod.load_house_map(path)

    def test_exact_8760_and_per_profile_energy(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'profiles.csv'
            hourly=pd.DataFrame({'timestamp_lst':pd.date_range('2025-01-01',periods=8760,freq='h').astype(str)})
            for j in range(1,36):
                hourly[f'house_{j}_kw']=np.ones(8760)*(1898/8760)
            hourly.to_csv(path,index=False)
            v=mod.load_profiles(path)
            self.assertEqual(v.shape,(8760,35))
            self.assertAlmostEqual(v.to_numpy().sum(),66430,places=4)
            hourly.loc[0,'house_1_kw']=-.2
            hourly.to_csv(path,index=False)
            with self.assertRaises(ValueError):mod.load_profiles(path)

    def test_fail_on_output_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):mod.new_output(Path(td))
            self.assertEqual(mod.new_output(Path(td)/'fresh.json').name,'fresh.json')

    def test_individual_loads_not_equal_splits(self):
        class FakeLoc:
            def __init__(self):self.table={}
            def __setitem__(self, key, value):self.table[key]=value
            def __getitem__(self, key):return self.table[key]
        class FakeNet:
            def __init__(self):self.load=type('L',(),{'at':FakeLoc()})()
        net=FakeNet()
        meta={'loads':{'H01':0,'H02':1}}
        mod.inject_individual_loads(net,meta,pd.Series({'H01':1.,'H02':2.}),.98,3.)
        self.assertAlmostEqual(net.load.at[0,'p_mw'],.003)
        self.assertAlmostEqual(net.load.at[1,'p_mw'],.006)
        self.assertNotEqual(net.load.at[0,'p_mw'],net.load.at[1,'p_mw'])
        self.assertGreater(net.load.at[1,'q_mvar'],net.load.at[0,'q_mvar'])
        with self.assertRaises(ValueError):
            mod.inject_individual_loads(net,meta,pd.Series({'H01':1,'H03':2}),.98,3.)

    def test_causal_pv_first_physics(self):
        # Source-equivalent 95% AC inverter and 95% roundtrip battery, 20% physical SOC.
        cap=17.3/4
        min_soc_store=cap-.8*5.12
        t=mod.causal_pv_first_dispatch([.0, 1.0, 1.0, 0.5], [3.0, 0.0, 0.0, 0.0],
                                       min_soc_store, 12, 1, 5., 2.)
        self.assertEqual(len(t),4)
        self.assertGreater(t.loc[0,'battery_charge_dc_kw'],0)
        self.assertEqual(t.loc[0,'grid_import_kw'],0)
        self.assertGreater(t.loc[1,'battery_discharge_dc_kw'],0)
        self.assertLess(t.loc[1,'grid_import_kw'],1.0)
        self.assertTrue((t.battery_soc_usable_kwh>=min_soc_store-1e-8).all())
        self.assertTrue((t.battery_soc_usable_kwh<=cap+1e-8).all())
        self.assertTrue((t.grid_export_kw==0.).all())
        self.assertTrue(np.allclose(t.demand_kw,t.grid_import_kw+t.inverter_ac_kw))
        self.assertTrue(np.allclose(t.pv_dc_available_kw,t.pv_dc_direct_to_inverter_kw+
                        t.pv_dc_battery_charge_kw+t.curtailed_pv_dc_kw))
        with self.assertRaises(ValueError):
            mod.causal_pv_first_dispatch([1],[1],0,12,1,5.,2.)

    def test_ss90_anchor_selection_uses_archived_hardware_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            base=root/'case1/studies/household_frontier_reuse_v1/outputs'
            base.mkdir(parents=True)
            rows=[{'case':'5_homes','equipment_id':'ref_min','selection_reasons':'MIN_ANNUAL_COST',
                    'pv_panels':17,'battery_modules':3,'battery_power_dc_kw':5.0,
                    'inverter_kva':5.0,'archived_self_sufficiency_pct':79.,'archived_annual_cost_usd':2000.},
                  {'case':'5_homes','equipment_id':'ref_ss90','selection_reasons':'LOWEST_COST_SS_AT_LEAST_90_PCT',
                    'pv_panels':20,'battery_modules':5,'battery_power_dc_kw':6.0,
                    'inverter_kva':6.0,'archived_self_sufficiency_pct':91.,'archived_annual_cost_usd':2100.}]
            pd.DataFrame(rows).to_csv(base/'stage_a_50_network_routing.csv',index=False)
            high=mod.archived_hardware_selection(root,'A0','85398','ss90')
            self.assertEqual(high[0],'ref_ss90')
            self.assertIn('BORROWED_NOT_OPTIMAL_FOR_4_HOUSES',high[-1])
            mini=mod.archived_hardware_selection(root,'A0','85398','min_cost')
            self.assertEqual(mini[0],'EC-18f85cfb1c7c7d0d19a2')
            with self.assertRaises(ValueError):
                mod.archived_hardware_selection(root,'A0','85398','wrong')

    def test_read_only_graph_membership_matrix(self):
        self.assertEqual(sum(mod.EXPECTED_COUNTS['A0'].values()),35)
        self.assertEqual(sum(mod.EXPECTED_COUNTS['A1'].values()),35)
        self.assertEqual(len(mod.ANCHORS),8)
        self.assertEqual(mod.ELIGIBLE,set(mod.EXPECTED_COUNTS['A0'])-{'92395','98380'})
        self.assertTrue(all((k[0],k[1]) in mod.ANCHORS for k in mod.ANCHORS))


class TestTransformerPositionA1(unittest.TestCase):
    """Transformer-distance membership, LV used only for downstream AC taps."""

    def fixture(self):
        a0={
          '94022':['H01','H02','H03','H06','H26','H27','H28','H29','H34','H35'],
          '106039':['H11','H13','H16','H17','H18','H19','H20','H21','H22','H23','H24','H25'],
          '113699':['H04','H05','H07','H10'],
          '85398':['H09','H12','H14','H15'],
          '92395':['H30','H31','H32','H33'],
          '98380':['H08'],
        }
        centers={'94022':0.,'113699':10.,'106039':20.,'85398':30.,'92395':40.,'98380':50.}
        trafos={tid:{'identifier':tid,'epm_node':'node_'+tid,'kva':3. if tid=='113699' else 5.,
                      'x':x,'y':0.} for tid,x in centers.items()}
        houses={hid:{'x':centers[tid],'y':1.,'source_status':'PROVISIONAL'}
                for tid,seq in a0.items() for hid in seq}
        houses['H03']['x']=8.1;houses['H06']['x']=9.;houses['H13']['x']=28.1
        # An actual transformer close to these houses but missing extracted LV geometry.
        houses['H30']['x']=40.;houses['H31']['x']=41.;houses['H32']['x']=41.3;houses['H33']['x']=42.
        lv=[{'node':'node_'+tid,'fid':tid+'A','geom':LineString([(x,0),(x,2)])}
             for tid,x in centers.items() if tid!='92395']
        # Make the H03/H06 original transformer LV appear closer, despite its
        # actual transformer being farther. Ownership must follow transformer centers.
        lv.extend([
          {'node':'node_94022','fid':'near_H03_but_wrong_trafo',
           'geom':LineString([(8.,0.),(8.,2.)])},
          {'node':'node_113699','fid':'near_113699',
           'geom':LineString([(9.1,0.),(9.1,2.)])},
          {'node':'node_85398','fid':'near_85398',
           'geom':LineString([(28.2,0.),(28.2,2.)])},
        ])
        original=[{'house':hid,'original':tid,'transformer':tid,'changed':False,
                   'segment_id':'' if tid=='92395' else tid+'A',
                   'gis_proximity_m':None,'source_status':'PROVISIONAL','status':'A0_BASE'}
                   for tid,seq in a0.items() for hid in seq]
        policies=[]
        def fake_infer(_hs,_ts,_lv,policy='base'):
            policies.append(policy)
            if policy!='base':raise AssertionError('Global nearest LV policy is forbidden')
            return [dict(rec) for rec in original]
        return houses,trafos,lv,fake_infer,policies

    def test_transformer_distance_controls_membership_even_if_wrong_lv_is_closer(self):
        houses,ts,lv,infer,policies=self.fixture()
        a0=mod.resolve_v4_assignments(houses,ts,lv,infer,'A0')
        a1=mod.resolve_v4_assignments(houses,ts,lv,infer,'A1')
        moves={x['house']:x['transformer'] for x,y in zip(a1,a0)
               if x['transformer']!=y['transformer']}
        self.assertEqual(moves,mod.A1_MOVE_TARGETS)
        self.assertEqual(policies,['base','base'])
        self.assertEqual(next(x for x in a1 if x['house']=='H03')['transformer'],'113699')
        self.assertEqual(next(x for x in a1 if x['house']=='H03')['segment_id'],'near_113699')
        self.assertEqual(next(x for x in a1 if x['house']=='H13')['segment_id'],'near_85398')
        self.assertEqual(next(x for x in a1 if x['house']=='H03')['status'],
                         'PROVISIONAL_TRANSFORMER_NEAREST_LV_TAP_GEOMETRY')
        self.assertEqual({k:sum(x['transformer']==k for x in a1) for k in mod.EXPECTED_COUNTS['A1']},
                         mod.EXPECTED_COUNTS['A1'])
        self.assertEqual({x['transformer'] for x in a1 if x['house'] in ('H30','H31','H32','H33')}, {'92395'})
        self.assertEqual(next(x for x in a1 if x['house']=='H30')['segment_id'],'')

    def test_missing_lv_does_not_disqualify_original_transformer(self):
        houses,ts,lv,infer,_=self.fixture()
        lv=[x for x in lv if x['node']!='node_92395']
        a1=mod.resolve_v4_assignments(houses,ts,lv,infer,'A1')
        self.assertEqual({x['house'] for x in a1 if x['transformer']=='92395'},
                         {'H30','H31','H32','H33'})

    def test_nearest_transformer_independent_of_all_lv_segments(self):
        houses,ts,lv,infer,_=self.fixture()
        ranking=mod.transformer_distance_ranking(houses['H03'],ts)
        self.assertEqual(ranking[0][0],'113699')
        self.assertEqual(ranking[1][0],'94022')
        self.assertLess(ranking[0][1],ranking[1][1])
        self.assertEqual(mod.resolve_v4_assignments(houses,ts,lv,infer,'A1')[2]['transformer'],'113699')

    def test_no_target_lv_blocks_ac_tap_only(self):
        houses,ts,lv,infer,_=self.fixture()
        lv=[x for x in lv if x['node']!='node_113699']
        self.assertEqual(mod.transformer_distance_ranking(houses['H03'],ts)[0][0],'113699')
        with self.assertRaisesRegex(ValueError,'missing GIS geometry'):
            mod.resolve_v4_assignments(houses,ts,lv,infer,'A1')

    def test_external_transformer_not_silently_added_to_six(self):
        houses,ts,lv,infer,_=self.fixture()
        ts['113306']={'identifier':'113306','epm_node':'extra','x':41.9,'y':0.,'kva':5.}
        with self.assertRaisesRegex(ValueError,'original SIX'):
            mod.resolve_v4_assignments(houses,ts,lv,infer,'A1')

    def test_actual_evidence_if_full_checkout_is_present(self):
        # In the user's checkout, this is an actual-source regression, not just mock GIS.
        repo=Path(__file__).resolve().parents[4]
        epm=repo/'case1/studies/epm_gis_pandapower_v1/epm_topology.py'
        if not epm.is_file():
            self.skipTest('Full GitLab checkout not mounted in isolated packaging environment')
        rd,infer,_,_=mod.repo_modules(repo)
        houses,trafos,lv=rd()
        mapping={hid:i+1 for i,hid in enumerate(sorted(houses))}
        groups,ass=mod.all_memberships(repo,mapping)
        self.assertEqual({t:len(ids) for t,ids in groups['A1'].items()},mod.EXPECTED_COUNTS['A1'])
        self.assertEqual(groups['A1']['92395'],['H30','H31','H32','H33'])
        moved={hid:ass['A1'][hid]['transformer'] for hid in houses
               if ass['A0'][hid]['transformer']!=ass['A1'][hid]['transformer']}
        self.assertEqual(moved,mod.A1_MOVE_TARGETS)

    def test_memberships_and_ac_geometry_consistent(self):
        houses,ts,lv,infer,policies=self.fixture()
        def read():return houses,ts,lv
        def builder(t,_hs,_ts,_lv,ass,factor):
            attached=[{'house':row['house'],'trafo':t,'segment':row['segment_id']}
                      for row in ass if row['transformer']==t]
            return SimpleNamespace(trafo=ts[t],graph='synthetic_graph',attachments=attached,
                                  label='proximity_test',root='R',line_count=2)
        class Territory(SimpleNamespace):pass
        with patch.object(mod,'repo_modules',lambda root:(read,infer,builder,Territory)):
            groups,ass=mod.all_memberships(Path('mock_git_checkout'),{h:i+1 for i,h in enumerate(houses)})
            self.assertEqual(groups['A1']['92395'],['H30','H31','H32','H33'])
            terr=mod.new_territory(Path('mock_git_checkout'),'A1','106039',groups['A1']['106039'],1.)
            self.assertEqual(len(terr.attachments),11)
            self.assertEqual(terr.trafo['kva'],5.)
            self.assertNotIn('H13',{row['house'] for row in terr.attachments})
            self.assertTrue(all(p=='base' for p in policies))


if __name__=='__main__':unittest.main()
