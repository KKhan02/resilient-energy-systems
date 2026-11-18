"""Non-solver tests for the source-verified full-year B9 AC overlay."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

src=Path(__file__).with_name('b9_full_annual_ac_overlay.py')
spec=importlib.util.spec_from_file_location('b9_full_annual_ac_overlay',src)
impl=importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)


class AnnualOverlayTests(unittest.TestCase):
    def test_all_nine_coverage(self):
        self.assertEqual(len(impl.FACTOR_VALUES),9)
        self.assertEqual(len(set(impl.FACTOR_VALUES)),9)
        self.assertIn((.95,1.6),impl.FACTOR_VALUES)

    def test_rejects_incorrect_changed_ac_and_keeps_loss_requirement(self):
        prior={'min_v_pu':.96,'max_v_pu':.99,'max_trafo_pct':99.,
               'max_line_pct':7.,'ac_feasible':True}
        result=dict(prior,status='CONVERGED',loss_kw=.05,pcc_kva=4.95)
        impl.compare_ac(result,prior,'candidate','SS_B9',.95,1.6,pd.Timestamp('2025-11-27 20:00'))
        with self.assertRaisesRegex(ValueError,'mismatches'):
            impl.compare_ac(dict(result,max_trafo_pct=103.),prior,'candidate','SS_B9',
                            .95,1.6,pd.Timestamp('2025-11-27 20:00'))
        with self.assertRaises(KeyError):
            impl.compare_ac({k:v for k,v in result.items() if k!='loss_kw'},prior,
                            'candidate','SS_B9',.95,1.6,pd.Timestamp('2025-11-27 20:00'))

    def test_loss_accounting_one_replaced_hour(self):
        dates=pd.DatetimeIndex(pd.date_range('2025-01-01',periods=3,freq='h'),name='timestamp_lst')
        data=pd.DataFrame({'status':['CONVERGED']*3,'ac_feasible':[True]*3,
            'min_v_pu':[.97,.98,.99],'max_v_pu':[1.0]*3,
            'max_trafo_pct':[90.,90.,90.],'max_line_pct':[6.,6.,6.],
            'loss_kw':[.10,.20,.30]},index=dates)
        corrected=data.copy()
        corrected.loc[dates[1],'loss_kw']=.17
        class Frontier:
            @staticmethod
            def valid_ac(frame):
                assert 'timestamp_lst' in frame
                return (frame.status=='CONVERGED')&(frame.max_trafo_pct<=100)
        class B9:
            @staticmethod
            def validated_ac_mask(frontier,frame):
                return frontier.valid_ac(frame.assign(timestamp_lst=frame.index))
        result=impl.summarize(data,corrected,'SS_B9',.95,1.6,
                              {'ac_hourly_sha256':'original'},Frontier,B9,[dates[1]])
        self.assertAlmostEqual(result['baseline_ac_losses_kwh'],.6)
        self.assertAlmostEqual(result['corrected_ac_losses_kwh'],.57)
        self.assertAlmostEqual(result['delta_ac_losses_kwh'],-.03)
        self.assertEqual(result['corrected_bad_hours'],0)


if __name__=='__main__':
    unittest.main()
