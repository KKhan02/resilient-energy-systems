import importlib.util
import math
from pathlib import Path
import sys
import unittest
from dataclasses import dataclass

P=Path(__file__).resolve().parents[1]/'run_92395_star_mst.py'
spec=importlib.util.spec_from_file_location('study_a_92395',P)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

@dataclass
class Territory:
    trafo:dict
    graph:object
    attachments:list
    label:str
    root:str
    line_count:int

class TestGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ts={'92395':{'x':0.,'y':0.,'kva':5.,'identifier':'92395','epm_node':'923848'}}
        cls.hs={k:{'x':float(i*100.),'y':0.,'assignment_status':'possible'} for i,k in enumerate(m.HOUSE_IDS)}

    def test_full_sensitivity_18_unique_star_mst(self):
        p=m.plan('all')
        self.assertEqual(len(p),18)
        self.assertEqual(len(set(p)),18)
        self.assertEqual(len(m.plan('baseline')),2)
        self.assertEqual(len(m.plan('main')),8)
        self.assertEqual(len(m.plan('interactions')),8)
        self.assertEqual({k for k,_,_ in p},{'star','mst'})
        self.assertEqual({pf for _,pf,_ in p},{.95,.98,1.})
        self.assertEqual({l for _,_,l in p},{1.,1.3,1.6})

    def test_star_four_household_connections(self):
        g=m.make_territory(self.hs,self.ts,Territory,'star',1.0)
        self.assertEqual((len(g.attachments),g.graph.number_of_nodes(),g.graph.number_of_edges()),(4,5,4))
        self.assertTrue(m.nx.is_tree(g.graph))
        self.assertEqual(g.root,'PROPOSED_TRAFO_92395')
        self.assertEqual(set(g.graph.neighbors(g.root)),{'HOUSE_'+x for x in m.HOUSE_IDS})
        self.assertAlmostEqual(sum(d['length_m'] for _,_,d in g.graph.edges(data=True)),600.25)

    def test_mst_shared_feeder_and_house_stubs(self):
        terr=m.make_territory(self.hs,self.ts,Territory,'mst',1.)
        g=terr.graph
        self.assertEqual((g.number_of_nodes(),g.number_of_edges()),(9,8))
        self.assertTrue(m.nx.is_tree(g))
        for hid in m.HOUSE_IDS:
            self.assertEqual(g.degree['HOUSE_'+hid],1)
            self.assertIn('JUNCTION_'+hid,g['HOUSE_'+hid])
        self.assertGreaterEqual(g.degree[terr.root],1)
        self.assertAlmostEqual(sum(d['length_m'] for _,_,d in g.edges(data=True)),301.25)

    def test_length_scaling_independent_of_topology(self):
        for top in ('star','mst'):
            low=m.make_territory(self.hs,self.ts,Territory,top,1.)
            high=m.make_territory(self.hs,self.ts,Territory,top,1.6)
            a=sum(d['length_m'] for _,_,d in low.graph.edges(data=True))
            b=sum(d['length_m'] for _,_,d in high.graph.edges(data=True))
            self.assertAlmostEqual(b,1.6*a)

    def test_unchanged_assignments_and_source_status(self):
        for top in ('star','mst'):
            terr=m.make_territory(self.hs,self.ts,Territory,top,1.3)
            self.assertEqual([x['house'] for x in terr.attachments],list(m.HOUSE_IDS))
            self.assertTrue(all(x['assumed'] and not x['changed'] for x in terr.attachments))
            self.assertEqual(terr.line_count,0)
            self.assertEqual(terr.trafo['kva'],5.)

    def test_signed_uploaded_a0_a1_92395_groups(self):
        import json,hashlib
        source=Path('/mnt/data/input_manifest_v6_2.json')
        if not source.exists():self.skipTest('Only available in response analysis workspace')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),m.EXPECTED_MANIFEST_SHA)
        j=json.loads(source.read_text())
        self.assertEqual(j['groups']['A0']['92395'],list(m.HOUSE_IDS))
        self.assertEqual(j['groups']['A1']['92395'],list(m.HOUSE_IDS))

    def test_output_protection_rejects_partials(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'partial';self.assertFalse(m.check_existing(folder,'star',.98,1.,24,'sig'))
            folder.mkdir()
            with self.assertRaises(RuntimeError):m.check_existing(folder,'star',.98,1.,24,'sig')

    def test_bad_scenarios_rejected(self):
        with self.assertRaises(ValueError):m.make_territory(self.hs,self.ts,Territory,'underground',1.)
        with self.assertRaises(ValueError):m.make_territory(self.hs,self.ts,Territory,'star',1.2)
        with self.assertRaises(ValueError):m.plan('nope')

if __name__=='__main__':unittest.main()
