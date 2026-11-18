"""Synthetic-only invariants. No PyPSA/pandapower computation in CI."""
import importlib.util
import math
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

module_path=Path(__file__).with_name('b9_soc_trial.py')
spec=importlib.util.spec_from_file_location('b9_soc_trial',module_path)
b9=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b9)


def fixture(case):
    idx=pd.date_range('2025-01-01',periods=8760,freq='h')
    a=pd.DataFrame(index=idx)
    a['demand_kw']=4.
    a['pv_dc_generated_kw']=0.
    a['pv_dc_available_kw']=0.
    a['battery_charge_dc_kw']=0.
    a['battery_discharge_dc_kw']=0.
    a['inverter_ac_kw']=0.
    a['battery_soc_usable_kwh']=9*.229
    a['grid_import_kw']=4.
    a['grid_export_kw']=0.
    a['unserved_kw']=0.
    a['curtailed_pv_dc_kw']=0.
    a['pcc_p_kw']=4.
    a['pcc_q_kvar_proxy']=.8
    a['pcc_kva_proxy']=np.hypot(a.pcc_p_kw,a.pcc_q_kvar_proxy)
    days=['2025-11-27'] if case=='SS_B9' else ['2025-10-13','2025-11-27']
    for day in days:
        charge=pd.Timestamp(day+' 12:00:00')
        donor=pd.Timestamp(day+' 18:00:00') if day.endswith('27') else pd.Timestamp(day+' 17:00:00')
        a.loc[charge,'pv_dc_generated_kw']=1+4/.95
        a.loc[charge,'pv_dc_available_kw']=1+4/.95
        a.loc[charge,'battery_charge_dc_kw']=1
        a.loc[charge,'inverter_ac_kw']=4
        a.loc[charge,'grid_import_kw']=0
        a.loc[donor,'battery_discharge_dc_kw']=.95
        a.loc[donor,'inverter_ac_kw']=.95*.95
        a.loc[donor,'grid_import_kw']=4-.95*.95
        a.loc[charge:donor-pd.Timedelta(hours=1),'battery_soc_usable_kwh']=9*.229+math.sqrt(.95)
        for t in (charge,donor):
            a.loc[t,'pcc_p_kw']=a.loc[t,'grid_import_kw']
            a.loc[t,'pcc_kva_proxy']=np.hypot(a.loc[t,'pcc_p_kw'],a.loc[t,'pcc_q_kvar_proxy'])
    return a


class B9StressTests(unittest.TestCase):
    def test_both_daily_transfers_preserve_physics(self):
        hw={'battery_modules':9,'battery_power_dc_kw':12.0,'inverter_kva':12.0}
        for case in ('SS_B9','MC_B9'):
            with self.subTest(case=case):
                source=fixture(case)
                before=source.copy(deep=True)
                b9.check_dispatch(source,hw)
                candidate,register,review=b9.shift(source,hw,case)
                self.assertEqual(len(register),1 if case=='SS_B9' else 2)
                self.assertAlmostEqual(candidate.grid_import_kw.sum(),source.grid_import_kw.sum(),places=6)
                self.assertAlmostEqual(candidate.battery_soc_usable_kwh.iloc[-1],source.battery_soc_usable_kwh.iloc[-1],places=6)
                pd.testing.assert_frame_equal(source,before)

    def test_overdraw_rejected(self):
        hw={'battery_modules':9,'battery_power_dc_kw':12.0,'inverter_kva':12.0}
        with self.assertRaises(ValueError):
            b9.shift(fixture('SS_B9'),hw,'SS_B9',nov_dc=1.1)

    def test_wrong_2025_length_rejected(self):
        hw={'battery_modules':9,'battery_power_dc_kw':12.0,'inverter_kva':12.0}
        with self.assertRaises(ValueError):
            b9.check_dispatch(fixture('SS_B9').iloc[:-1],hw)


    def test_datetime_index_ac_validation_and_string_error_overlay(self):
        """Regression for missing timestamp_lst column and pandas FutureWarning."""
        import warnings
        frontier_path = (module_path.parent.parent /
                         'SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17' /
                         'validate_frontier_ac.py')
        front_spec = importlib.util.spec_from_file_location('frontier_ac_validation', frontier_path)
        frontier = importlib.util.module_from_spec(front_spec)
        front_spec.loader.exec_module(frontier)
        idx = pd.DatetimeIndex(pd.to_datetime(['2025-11-27 18:00:00',
                                                '2025-11-27 20:00:00']),
                               name='timestamp_lst')
        frame = pd.DataFrame({
            'status': ['CONVERGED', 'CONVERGED'],
            'ac_feasible': [True, False],
            'min_v_pu': [.960, .954],
            'max_v_pu': [1.001, 1.001],
            'max_trafo_pct': [94., 107.431],
            'max_line_pct': [7.0, 7.5],
            'error': [np.nan, np.nan],
        }, index=idx)
        self.assertEqual(frame['error'].dtype.kind, 'f')
        with self.assertRaisesRegex(ValueError, 'Missing AC result columns'):
            frontier.valid_ac(frame)  # Old failure, timestamp is only an index
        record = {'status': 'CONVERGED', 'ac_feasible': True,
                  'min_v_pu': .962, 'max_v_pu': 1.001,
                  'max_trafo_pct': 98.5, 'max_line_pct': 7.3,
                  'error': ''}
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            b9.overlay_ac_hour(frame, idx[1], record)
        self.assertEqual(frame.at[idx[1], 'error'], '')
        self.assertEqual(frame['error'].dtype.kind, 'O')
        flags = b9.validated_ac_mask(frontier, frame)
        self.assertEqual(flags.tolist(), [True, True])
        self.assertTrue(flags.index.equals(idx))

    def test_ac_flag_disagreement_is_rejected(self):
        idx = pd.DatetimeIndex(pd.to_datetime(['2025-11-27 20:00:00']), name='timestamp_lst')
        frame = pd.DataFrame({
            'status': ['CONVERGED'], 'ac_feasible': [True],
            'min_v_pu': [.954], 'max_v_pu': [1.0],
            'max_trafo_pct': [107.431], 'max_line_pct': [7.5],
        }, index=idx)
        class Dummy:
            @staticmethod
            def valid_ac(df):
                if 'timestamp_lst' not in df.columns:
                    raise ValueError('Missing timestamp_lst')
                return (df['max_trafo_pct'] <= 100)
        with self.assertRaisesRegex(ValueError, 'flags inconsistent'):
            b9.validated_ac_mask(Dummy, frame)



if __name__=='__main__':
    unittest.main()
