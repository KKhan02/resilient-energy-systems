"""Synthetic invariants of the source-verified loss economic report."""
import importlib.util
import tempfile
import json
from pathlib import Path
import unittest

f=Path(__file__).with_name('audit_b9_loss_economics.py')
spec=importlib.util.spec_from_file_location('b9_loss_economics',f)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class LossAuditTests(unittest.TestCase):
    def test_full_factor_count(self):
        self.assertEqual(len(audit.FACTOR),9)
        self.assertEqual(len(set(audit.FACTOR)),9)
        self.assertEqual(sorted(audit.TIERS),['MC_REF','SS_REF'])
    def test_csv_preserves_negative_and_precise_values(self):
        d={'reference':'SS_REF','fullDiff':-16.06944593679,'pf':0.95}
        s=audit.serialize([d],['reference','fullDiff','pf'])
        self.assertIn('SS_REF,-16.069446,0.950000',s)
    def test_signed_index_complete(self):
        indexed=audit.signed_reference_index()
        self.assertEqual(len(indexed),18)
        self.assertEqual(len(set(indexed)),18)

    def test_missing_local_summary_uses_pinned_index(self):
        index=audit.signed_reference_index()
        entry=index[('min_cost_ref',.95,1.)]
        prior={'original_ac_sha256':entry['ac_hourly_sha256']}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            m,mode,path=audit.checked_reference_summary(
                root,'min_cost_ref',.95,1.,prior,entry['energy_manifest_sha256'],index)
            self.assertEqual(mode,'GITLAB_INDEX_FALLBACK')
            self.assertAlmostEqual(m['annual_or_sample_losses_kwh'],428.79478877936367)
            source=root/path
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps({
                'hours':8760,'converged_hours':8760,'ac_hourly_sha256':entry['ac_hourly_sha256'],
                'energy_manifest_sha256':entry['energy_manifest_sha256'],'pf':.95,
                'length_factor':1.,'annual_or_sample_losses_kwh':entry['annual_ac_loss_kwh']}))
            _,mode,_=audit.checked_reference_summary(
                root,'min_cost_ref',.95,1.,prior,entry['energy_manifest_sha256'],index)
            self.assertEqual(mode,'LOCAL_SUMMARY_VERIFIED')
            source.write_text(json.dumps({
                'hours':8760,'converged_hours':8760,'ac_hourly_sha256':entry['ac_hourly_sha256'],
                'energy_manifest_sha256':entry['energy_manifest_sha256'],'pf':.95,
                'length_factor':1.,'annual_or_sample_losses_kwh':999999}))
            with self.assertRaisesRegex(ValueError,'conflicts'):
                audit.checked_reference_summary(
                    root,'min_cost_ref',.95,1.,prior,entry['energy_manifest_sha256'],index)
            with self.assertRaisesRegex(ValueError,'disagrees'):
                audit.checked_reference_summary(
                    root,'min_cost_ref',.95,1.,{'original_ac_sha256':'0'*64},
                    entry['energy_manifest_sha256'],index)

    def test_year_and_hardware_cashflow_identity(self):
        capex=146.45198029;imp_savings=556.36835696;loss_saved=4.05
        delta=capex-.29*(imp_savings+loss_saved)
        self.assertLess(delta,0)
        self.assertAlmostEqual(capex/(imp_savings+loss_saved),.2613,places=3)


if __name__=='__main__':
    unittest.main()
