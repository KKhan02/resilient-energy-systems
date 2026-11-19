import importlib.util
import math
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

loc=Path(__file__).with_name('run_stage2_grid_reserve.py')
spec=importlib.util.spec_from_file_location('grid_reserve',loc)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReserveTests(unittest.TestCase):
    def simple(self):
        idx=pd.date_range('2025-10-13 17:00',periods=4,freq='h')
        df=pd.DataFrame(index=idx)
        df['battery_discharge_dc_kw']=[2.,1.,0.,0.]
        df['inverter_ac_kw']=[1.9,.95,0.,0.]
        df['grid_import_kw']=[.1,1.05,2.,2.]
        df['battery_soc_usable_kwh']=[5.,4.,4.,4.]
        df['pcc_q_kvar_proxy']=[.3,.3,.3,.3]
        df['pcc_p_kw']=df.grid_import_kw
        df['pcc_kva_proxy']=np.hypot(df.grid_import_kw,df.pcc_q_kvar_proxy)
        return df

    def test_shift_preserves_annual_dc_discharge_and_ac_grid_import(self):
        df=self.simple()
        new=m.update_shift(df,df.index[0],df.index[-1],.6)
        self.assertAlmostEqual(df.battery_discharge_dc_kw.sum(),new.battery_discharge_dc_kw.sum())
        self.assertAlmostEqual(df.grid_import_kw.sum(),new.grid_import_kw.sum())
        self.assertAlmostEqual(new.inverter_ac_kw.iat[0],1.9-.57)
        self.assertAlmostEqual(new.inverter_ac_kw.iat[3],.57)
        self.assertAlmostEqual(new.battery_soc_usable_kwh.iat[0]-df.battery_soc_usable_kwh.iat[0],
                               .6/math.sqrt(.95))
        self.assertAlmostEqual(new.battery_soc_usable_kwh.iat[-1],df.battery_soc_usable_kwh.iat[-1])
        self.assertEqual(df.inverter_ac_kw.iat[0],1.9)

    def test_transfer_rejects_unavailable_discharge(self):
        a=self.simple()
        with self.assertRaisesRegex(ValueError,'Source discharge unavailable'):
            m.update_shift(a,a.index[0],a.index[3],5.)

    def test_transfer_rejects_negative_grid_after_target(self):
        a=self.simple()
        a.loc[a.index[3],'grid_import_kw']=.01
        with self.assertRaisesRegex(ValueError,'inverter availability'):
            m.update_shift(a,a.index[0],a.index[3],.6)

    def test_shift_plan_two_distinct_timestamps(self):
        self.assertEqual(len(m.SHIFT_PLAN),2)
        self.assertEqual([x[:2] for x in m.SHIFT_PLAN],[
          ('2025-10-13 17:00:00','2025-10-13 20:00:00'),
          ('2025-11-27 17:00:00','2025-11-27 20:00:00')])

if __name__=='__main__':
    unittest.main()
