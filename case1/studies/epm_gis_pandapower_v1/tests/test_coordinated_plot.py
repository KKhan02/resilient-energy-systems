import unittest
from pathlib import Path
import sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from plot_coordinated_q import plot
class PlotTest(unittest.TestCase):
    def test_static_scatter_produces_two_files(self):
        d=pd.DataFrame([dict(trafo='94022',siting='middle',load_pf=.98,service_factor=1.0,
            policy='coordinated',q_ratio=q,min_v_pu=.97+q*.01,max_v_pu=1.03-q*.01,
            max_trafo_pct=95+q,hours=4,failed_hours=0,feasible_hours=4) for q in (0,.25,.48)])
        with tempfile.TemporaryDirectory() as folder:
            stems,passing=plot(d,Path(folder))
            self.assertEqual(len(stems),1)
            self.assertEqual(passing,3)
            self.assertTrue((Path(folder)/(stems[0]+'.png')).exists())
            self.assertTrue((Path(folder)/(stems[0]+'.svg')).exists())
if __name__=='__main__':unittest.main()
