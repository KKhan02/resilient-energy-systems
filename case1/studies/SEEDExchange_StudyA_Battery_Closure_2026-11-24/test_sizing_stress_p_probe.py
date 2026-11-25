import unittest
from sizing_stress_p_probe import scan

class StressProbeTests(unittest.TestCase):
    def test_all_fail(self):
        self.assertEqual(scan(lambda p:False,5),([],None))
    def test_terminal_segment(self):
        passing,bounds=scan(lambda p:p>=2,5)
        self.assertGreater(len(passing),0)
        self.assertTrue(2<=bounds[0]<=2.02)
        self.assertEqual(bounds[1],5)
    def test_nonterminal_pass(self):
        passing,bounds=scan(lambda p:1<=p<=3,5)
        self.assertGreater(len(passing),0)
        self.assertIsNone(bounds)
if __name__=="__main__":unittest.main()
