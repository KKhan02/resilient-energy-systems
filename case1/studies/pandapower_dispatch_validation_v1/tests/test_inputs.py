import sys,unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run_validation import load_dispatch,critical_indices,allocation_weights
class TestInputs(unittest.TestCase):
    def test_all_three_8760_hour_dispatches(self):
        for count in (7,9,12):
            d=load_dispatch(HERE/'input'/'dispatch'/f'{count}_homes_hourly_dispatch.csv')
            self.assertEqual(len(d),8760)
            self.assertTrue(np.all(d['grid_import_kw'].to_numpy()>=-1e-4))
    def test_selection(self):
        d=load_dispatch(HERE/'input'/'dispatch'/'12_homes_hourly_dispatch.csv')
        ix=critical_indices(d)
        self.assertIn(int(d.demand_kw.idxmax()),ix)
        self.assertIn(int(d.pcc_kva_proxy.idxmax()),ix)
        self.assertGreater(len(ix),15)
    def test_load_allocation(self):
        for n in (7,9,12):
            for mode in ('equal','far_end_heavy'):
                w=allocation_weights(n,mode)
                self.assertAlmostEqual(w.sum(),1.0,places=10)
                self.assertEqual(len(w),n)
                self.assertTrue((w>=0).all())
if __name__=='__main__':unittest.main()
