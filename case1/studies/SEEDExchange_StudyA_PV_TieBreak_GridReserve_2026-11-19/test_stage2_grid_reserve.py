import importlib.util
import hashlib
import tempfile
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

    def test_signed_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.csv'
            data=b'a,b\r\n1,2\r\n'
            path.write_bytes(data)
            self.assertEqual(m.verify_signed_sha(path,hashlib.sha256(data).hexdigest()),
                             'EXACT_SIGNED_BYTES')

    def test_git_lf_reproduces_original_crlf_signature(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.csv'
            path.write_bytes(b'a,b\n1,2\n')
            signed=hashlib.sha256(b'a,b\r\n1,2\r\n').hexdigest()
            self.assertEqual(m.verify_signed_sha(path,signed),
                             'GIT_LF_RECONSTRUCTS_SIGNED_CRLF')

    def test_tampered_signed_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.csv'
            path.write_bytes(b'a,b\n1,3\n')
            signed=hashlib.sha256(b'a,b\r\n1,2\r\n').hexdigest()
            with self.assertRaisesRegex(ValueError,'Signed source SHA256 mismatch'):
                m.verify_signed_sha(path,signed)

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

    def test_valid_prior_stage2_overlap_is_counted_once(self):
        lineage=m.verify_reserve_change_set(
            [6857,6860,7937,7940],[6857,6860,7937,7940],[20,21,7937])
        self.assertEqual(lineage['overlap_with_stage2_indexes'],[7937])
        self.assertEqual(lineage['overlap_with_stage2_hours'],1)
        self.assertEqual(lineage['reserve_corrected_hours'],4)
        self.assertEqual(lineage['unique_changed_since_stage1_hours'],6)

    def test_unexpected_reserve_hour_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unexpected reserve candidate changed-hour set'):
            m.verify_reserve_change_set(
                [6857,6860,7937,7941],[6857,6860,7937,7940],[7937])

    def test_overlapping_stage2_ac_row_is_replaced_by_reserve(self):
        t=pd.Timestamp('2025-11-27 17:00:00')
        stitched=pd.DataFrame({'status':['CONVERGED'],
                              'ac_feasible':[True],'max_trafo_pct':[65.879]},index=[t])
        m.patch_ac(stitched,t,{'stage2_max_trafo_pct':36.7338640691},'stage2_')
        self.assertAlmostEqual(float(stitched.at[t,'max_trafo_pct']),36.7338640691)
        m.patch_ac(stitched,t,{'reserve_max_trafo_pct':42.0},'reserve_')
        self.assertAlmostEqual(float(stitched.at[t,'max_trafo_pct']),42.0)


if __name__=='__main__':
    unittest.main()
