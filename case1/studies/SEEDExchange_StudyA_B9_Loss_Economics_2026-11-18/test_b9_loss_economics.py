"""Synthetic invariants of the source-verified loss economic report."""
import importlib.util
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
    def test_year_and_hardware_cashflow_identity(self):
        capex=146.45198029;imp_savings=556.36835696;loss_saved=4.05
        delta=capex-.29*(imp_savings+loss_saved)
        self.assertLess(delta,0)
        self.assertAlmostEqual(capex/(imp_savings+loss_saved),.2613,places=3)


if __name__=='__main__':
    unittest.main()
