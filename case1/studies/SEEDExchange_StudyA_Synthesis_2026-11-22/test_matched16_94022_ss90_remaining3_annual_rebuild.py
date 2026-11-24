"""Source-only annual reuse and merge guards. No AC solver calls."""
import unittest
import pandas as pd
import matched16_94022_ss90_remaining3_annual_rebuild as r


def synthetic():
    stamps = pd.date_range('2025-01-01', periods=8760, freq='h')
    old = []
    for stamp in stamps:
        x = dict(timestamp_lst=str(stamp), status='CONVERGED', ac_feasible='True',
                 gross_demand_kw='2.0', inverter_ac_kw='0.0', min_v_pu='0.96',
                 max_v_pu='1.0', max_trafo_pct='40', max_line_pct='10', loss_kw='0.01',
                 pcc_kva='2.0', voltage_below_095='0', voltage_below_097='1',
                 voltage_above_105='0', voltage_above_103='0', trafo_over_100='0',
                 line_over_100='0', q_selected_kvar='0.0', q_requested_kvar='0.0',
                 q_controller_status='Q_OFF', night_reactive_disabled='True',
                 load_pf='0.98', ac_evaluations='1', error='',
                 original_energy_sha256='signed', source_grid_import_kw='2.0',
                 scenario='prior_corrected')
        old.append(x)
    new = {}
    for stamp in r.joint.SOURCE_TIMES:
        x = dict(old[stamps.get_loc(pd.Timestamp(stamp))])
        x['inverter_ac_kw'] = '1.0'
        x['min_v_pu'] = '0.955'
        x['loss_kw'] = '0.008'
        new[stamp] = x
    source = pd.DataFrame({'inverter_ac_kw': 0.0, 'demand_kw': 2.0,
                           'grid_import_kw': 2.0}, index=stamps)
    for stamp in new:
        source.at[pd.Timestamp(stamp), 'inverter_ac_kw'] = 1.0
        source.at[pd.Timestamp(stamp), 'grid_import_kw'] = 1.0
    return old, new, source


class AnnualRebuildContract(unittest.TestCase):
    def test_exact_six_replaced_no_other_hour(self):
        old, new, source = synthetic()
        changed, ledger = r.merge_six(old, new, source)
        self.assertEqual(len(changed), 8760)
        self.assertEqual(len(ledger), 6)
        self.assertEqual(sum(a != b for a, b in zip(old, changed)), 6)
        self.assertEqual([d['timestamp_lst'] for d in ledger], list(r.joint.SOURCE_TIMES))
        self.assertTrue(all(d['new_corrected_min_v_pu'] == 0.955 for d in ledger))
        self.assertEqual(r.full_year_rows(old), old)
        self.assertEqual(r.full_year_rows(changed), changed)

    def test_wrong_p_in_new_ac_rejected(self):
        old, new, source = synthetic()
        new[next(iter(new))]['inverter_ac_kw'] = '2.0'
        with self.assertRaisesRegex(ValueError, 'source annual P'):
            r.merge_six(old, new, source)

    def test_missing_or_false_new_ac_rejected(self):
        old, new, source = synthetic()
        with self.assertRaisesRegex(ValueError, 'exactly six'):
            r.merge_six(old, dict(list(new.items())[:-1]), source)
        new[next(iter(new))]['ac_feasible'] = 'False'
        with self.assertRaisesRegex(ValueError, 'not converged/AC feasible'):
            r.merge_six(old, new, source)

    def test_duplicate_or_unordered_archive_rejected(self):
        old, _, _ = synthetic()
        with self.assertRaisesRegex(ValueError, 'unique ordered'):
            r.full_year_rows(old[:-1] + [old[-2]])
        with self.assertRaisesRegex(ValueError, 'unique ordered'):
            r.full_year_rows(list(reversed(old)))

    def test_wrong_new_pf_rejected(self):
        old,new,source=synthetic()
        new[next(iter(new))]['load_pf']='0.95'
        with self.assertRaisesRegex(ValueError,'load or PF changed'):
            r.merge_six(old,new,source)


if __name__ == '__main__':
    unittest.main()
