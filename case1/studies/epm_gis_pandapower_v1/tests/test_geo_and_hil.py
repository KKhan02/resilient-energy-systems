import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from epm_topology import read_data,infer_assignments,build_territory,conductor_params,farthest_house,middle_on_path,split_for_middle
from hil_voltvar import HILParams,q_command,capability_kvar,pt1_step

class GISInputs(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.h,cls.t,cls.lv=read_data()
  cls.a=infer_assignments(cls.h,cls.t,cls.lv,'base')
 def test_inventory(self):
  self.assertEqual(len(self.h),35)
  self.assertEqual(len(self.a),35)
  self.assertEqual(len({a['house'] for a in self.a}),35)
 def test_actual_gis_lines(self):
  expected={'94022':(6,288),'106039':(15,726),'113699':(6,429.49),'85398':(1,85),'98380':(2,360)}
  for tid,(lines,meters) in expected.items():
   tr=build_territory(tid,self.h,self.t,self.lv,self.a)
   self.assertEqual(tr.line_count,lines)
   self.assertAlmostEqual(tr.metrics()['mapped_lv_m'],meters,delta=.1)
   self.assertTrue(tr.metrics()['tree'])
 def test_no_pretend_92395_lines(self):
  self.assertIsNone(build_territory('92395',self.h,self.t,self.lv,self.a))
 def test_attachments_do_not_change_epm_length(self):
  t1=build_territory('106039',self.h,self.t,self.lv,self.a,1.)
  t2=build_territory('106039',self.h,self.t,self.lv,self.a,1.6)
  self.assertEqual(t1.metrics()['mapped_lv_m'],t2.metrics()['mapped_lv_m'])
  self.assertGreater(t2.metrics()['assumed_service_m'],t1.metrics()['assumed_service_m']*1.5)
 def test_nearest_assumption_changed_nine_houses(self):
  x=infer_assignments(self.h,self.t,self.lv,'nearest_mapped')
  self.assertEqual(sum(a['changed'] for a in x),9)
  self.assertEqual(sum(a['status']=='ASSUMED_NEAREST_EPM_SEGMENT' for a in x),35)
 def test_midpoint_split_preserves_length(self):
  t=build_territory('106039',self.h,self.t,self.lv,self.a)
  g=t.graph.copy();length_before=sum(d['length_m'] for _,_,d in g.edges(data=True))
  k=split_for_middle(g,t.root,farthest_house(t))
  length_after=sum(d['length_m'] for _,_,d in g.edges(data=True))
  self.assertEqual(k,'PV_BESS_MIDPOINT')
  self.assertAlmostEqual(length_before,length_after,places=8)
 def test_known_and_fallback_conductors(self):
  self.assertTrue(conductor_params('AAC','2')[-1])
  self.assertFalse(conductor_params('UNKNOWN','8')[-1])

class Controller(unittest.TestCase):
 def test_rule_curve_signs(self):
  a=lambda v:q_command(v,0.,10.,10.,params=HILParams())
  self.assertAlmostEqual(a(.95),4.8)
  self.assertAlmostEqual(a(.99),0.)
  self.assertAlmostEqual(a(1.00),0.)
  self.assertAlmostEqual(a(1.01),0.)
  self.assertAlmostEqual(a(1.05),-4.8)
  self.assertAlmostEqual(a(.975),2.4)
  self.assertAlmostEqual(a(1.025),-2.4)
 def test_capability_circle(self):
  self.assertAlmostEqual(capability_kvar(9.8,10,10),math.sqrt(100-9.8**2))
  self.assertAlmostEqual(capability_kvar(6,10,10),4.8)
  with self.assertRaises(ValueError):capability_kvar(11,10,10)
 def test_hil_qratio_not_S(self):
  self.assertAlmostEqual(capability_kvar(0,12,8),.48*8)
  self.assertAlmostEqual(capability_kvar(0,12,8,HILParams(q_ratio=.25)),.25*8)
 def test_fixed_pf_and_unity(self):
  self.assertEqual(q_command(.92,2,10,10,mode='unity'),0.)
  self.assertLess(q_command(1,2,10,10,mode='fixed_pf',fixed_direction='absorb'),0.)
  self.assertGreater(q_command(1,2,10,10,mode='fixed_pf',fixed_direction='inject'),0.)
 def test_pt1_six_to_nine_s(self):
  q=pt1_step(0,5,10)
  self.assertGreater(q,4.7)
  self.assertLess(q,5)
 def test_invalid_slope(self):
  with self.assertRaises(ValueError):HILParams(u1=.99,u2=.98)

if __name__=='__main__':unittest.main()
