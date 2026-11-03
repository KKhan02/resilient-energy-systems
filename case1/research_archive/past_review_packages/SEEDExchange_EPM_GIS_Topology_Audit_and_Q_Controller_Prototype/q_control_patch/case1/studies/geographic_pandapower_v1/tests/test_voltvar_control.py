import unittest, math
from voltvar_control import q_cap_kvar,q_target_kvar
class TestInverterQ(unittest.TestCase):
    def test_unity(self):self.assertEqual(q_target_kvar(.94,5,10,'unity'),0)
    def test_deadband(self):self.assertEqual(q_target_kvar(1.0,5,10,'volt_var'),0)
    def test_under_over_voltage(self):
        self.assertGreater(q_target_kvar(.95,5,10,'volt_var'),0)
        self.assertLess(q_target_kvar(1.05,5,10,'volt_var'),0)
    def test_cap(self):
        self.assertAlmostEqual(q_cap_kvar(9.8,10),math.sqrt(100-9.8**2))
        self.assertLessEqual(abs(q_target_kvar(.90,9.8,10,'volt_var')),q_cap_kvar(9.8,10)+1e-8)
    def test_fixed_direction(self):
        self.assertLess(q_target_kvar(1.0,5,10,'fixed_pf',fixed_direction='absorb'),0)
    def test_reject_undersized_inverter(self):
        with self.assertRaises(ValueError):q_cap_kvar(6,5)
if __name__=='__main__':unittest.main()
