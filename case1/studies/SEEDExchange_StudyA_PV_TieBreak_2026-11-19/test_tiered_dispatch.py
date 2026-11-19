"""Lightweight independent checks; source preflight is an explicit local command."""
import importlib.util
from pathlib import Path
import unittest
import contextlib
import io
import json
import sys
from unittest import mock
import numpy as np
import pandas as pd

path=Path(__file__).with_name('tiered_dispatch.py')
spec=importlib.util.spec_from_file_location('tiered_dispatch',path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TieBreakTests(unittest.TestCase):
    def test_daily_weight_is_bounded_and_prefers_early_hours(self):
        dates=pd.to_datetime(['2025-01-01 07:00','2025-01-01 14:00',
                              '2025-01-02 07:00','2025-01-02 14:00'])
        w=m.morning_weight(dates)
        self.assertTrue(np.all((w>=1.)&(w<=2.)))
        self.assertGreater(w[0],w[1]);self.assertAlmostEqual(w[0],w[2])
        self.assertAlmostEqual(w[1],w[3])

    def test_objective_weights_with_timestamp_lst_named_index(self):
        import xarray as xr
        idx=pd.date_range('2025-01-01',periods=24,freq='h',name='timestamp_lst')
        lp_var=xr.DataArray(np.arange(24.,dtype=float),
                            coords={'snapshot':idx.to_numpy()},dims=('snapshot',))
        weights=m.objective_snapshot_weights(idx,lp_var)
        self.assertEqual(weights.dims,('snapshot',))
        self.assertEqual(weights.coords['snapshot'].dims,('snapshot',))
        self.assertTrue(np.array_equal(weights.coords['snapshot'].to_numpy(),idx.to_numpy()))
        self.assertAlmostEqual(float((weights*lp_var).sum()),
                               float(np.dot(m.morning_weight(idx),np.arange(24.))))

    def test_objective_weights_reject_misaligned_lp_timestamps(self):
        import xarray as xr
        idx=pd.date_range('2025-01-01',periods=4,freq='h',name='timestamp_lst')
        shifted=idx + pd.Timedelta(hours=1)
        lp_var=xr.DataArray(np.ones(4),
                            coords={'snapshot':shifted.to_numpy()},dims=('snapshot',))
        with self.assertRaisesRegex(ValueError,'snapshots do not match'):
            m.objective_snapshot_weights(idx,lp_var)

    def test_source_metrics_flag_naive_grid_violation(self):
        class Audit:
            @staticmethod
            def grid_bound(demand):
                return np.full(len(demand),4.5)
        idx=pd.date_range('2025-01-01',periods=2,freq='h')
        h=pd.DataFrame({'demand_kw':[5.,3.], 'curtailed_pv_dc_kw':[1.,0.],
          'grid_import_kw':[5.,2.], 'battery_charge_dc_kw':[0.,1.],
          'battery_discharge_dc_kw':[0.,0.], 'battery_soc_usable_kwh':[3.,4.]},index=idx)
        stats=m.annual_metrics(h,Audit)
        self.assertEqual(stats['grid_proxy_failure_hours'],1)
        self.assertEqual(stats['simultaneous_grid_import_curtailment_hours'],1)
        self.assertAlmostEqual(stats['annual_battery_dc_throughput_kwh'],1.)
        self.assertGreater(stats['weighted_daily_early_curtailment_score'],1.)

    def test_preflight_cli_succeeds_without_errors_key(self):
        signed = {'status':'SIGNED_SOURCE_PREFLIGHT_ONLY',
                  'checks':{'MC_REF':{'hours':8760},'MC_P33':{'hours':8760}}}
        output=io.StringIO()
        with mock.patch.object(m,'run',return_value=signed) as run_stub:
            with mock.patch.object(sys,'argv',['tiered_dispatch.py','--preflight-only']):
                with contextlib.redirect_stdout(output):
                    m.main()
        self.assertEqual(json.loads(output.getvalue()),signed)
        self.assertTrue(run_stub.call_args.kwargs.get('preflight_only',False) or
                        run_stub.call_args.args[-1] is True)

    def test_full_run_cli_preserves_failure_exit(self):
        simulated={'status':'INCOMPLETE_OR_FAILURES_NOT_AC_VALIDATED',
                   'cases':{},'errors':{'MC_REF':{'type':'RuntimeError'}}}
        with mock.patch.object(m,'run',return_value=simulated):
            with mock.patch.object(sys,'argv',['tiered_dispatch.py','--out','mock_new']):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        m.main()
        self.assertEqual(ctx.exception.code,2)

    def test_negative_tolerance_fails_before_source_read(self):
        with self.assertRaisesRegex(ValueError,'negative'):
            m.run('.',selected='MC_P33',import_tolerance=-1,preflight_only=True)

if __name__=='__main__':
    unittest.main()
