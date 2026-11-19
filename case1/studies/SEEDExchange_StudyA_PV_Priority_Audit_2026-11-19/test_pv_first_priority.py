"""Synthetic tests for PV-first chronological operation, source identity and limits."""
import hashlib
import importlib.util
import tempfile
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

script=Path(__file__).with_name('audit_pv_first_priority.py')
spec=importlib.util.spec_from_file_location('audit_pv_first_priority',script)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PvPriorityTests(unittest.TestCase):
    def test_signed_lf_exactly_matches_windows_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.csv'
            original=b'timestamp_lst,demand_kw\r\n2025-01-01 00:00:00,4\r\n'
            expected=hashlib.sha256(original).hexdigest()
            p.write_bytes(original)
            self.assertEqual(m.signature_mode(p,expected),'SIGNED_BYTES')
            p.write_bytes(original.replace(b'\r\n',b'\n'))
            self.assertEqual(m.signature_mode(p,expected),'EXACT_GIT_NEWLINE_NORMALIZATION')
            p.write_bytes(original.replace(b'4\r\n',b'5\n').replace(b'\r\n',b'\n'))
            with self.assertRaisesRegex(ValueError,'differs'):
                m.signature_mode(p,expected)

    def test_solar_first_prefers_load_and_then_battery(self):
        idx=pd.date_range('2025-01-01',periods=4,freq='h')
        data=pd.DataFrame({
            'demand_kw':[2,2,2,2],'pv_dc_available_kw':[0.,10.,0.,0.]
        },index=idx)
        hw={'battery_modules':8,'battery_power_dc_kw':12.,'inverter_kva':12.}
        init=5.
        out=m.causal_pv_first(data,hw,init)
        self.assertEqual(len(out),4)
        self.assertGreater(out.battery_charge_dc_kw.iloc[1],0.)
        self.assertAlmostEqual(out.grid_import_kw.iloc[1],0.)
        self.assertAlmostEqual(out.curtailed_pv_dc_kw.iloc[1],0.)
        self.assertGreater(out.battery_discharge_dc_kw.iloc[0],0.)
        self.assertFalse(((out.battery_charge_dc_kw>1e-6)&
                          (out.battery_discharge_dc_kw>1e-6)).any())
        self.assertGreaterEqual(out.battery_soc_usable_kwh.min(),.229*8-1e-6)
        self.assertLessEqual(out.battery_soc_usable_kwh.max(),4.325*8+1e-6)
        self.assertTrue(np.isfinite(out.to_numpy(float)).all())

    def test_grid_proxy_flag_is_not_ac_certification(self):
        self.assertLess(float(m.grid_bound([5.32667697])[0]),5.)
        self.assertAlmostEqual(float(m.grid_bound([5.32667697])[0]),4.8816064062,places=7)

    def test_wrong_initial_soc_rejected(self):
        frame=pd.DataFrame({'demand_kw':[1.],
            'pv_dc_available_kw':[0.]},
            index=pd.date_range('2025-01-01',periods=1,freq='h'))
        hw={'battery_modules':8,'battery_power_dc_kw':12.,'inverter_kva':12.}
        with self.assertRaisesRegex(ValueError,'initial state'):
            m.causal_pv_first(frame,hw,0.)


if __name__=='__main__':
    unittest.main()
