import unittest
import remote_85398_A1_gap as r

class GapGate(unittest.TestCase):
    def test_population(self):
        r.plan_gate()
        self.assertEqual(len(r.RECIP)*len(r.ANNUAL_FACTORS)*8760,35040)
        self.assertEqual(len(r.NATIVE)*len(r.FACTORS)*8760,157680)
    def test_archive_naming(self):
        self.assertEqual(r.archive_key(r.NATIVE[1],.95,1.6),"A1_85398_ss90_ref_mapped_optimized_pf095_length16_annual8760")
    def test_schedule_identity(self):
        self.assertEqual(len(set(r.EXPECTED.values())),4)
        self.assertTrue(all(len(v)==64 for v in r.EXPECTED.values()))
    def test_sample_accounting(self):
        self.assertEqual((len(r.FACTORS)-len(r.ANNUAL_FACTORS))*len(r.RECIP),14)

if __name__=="__main__":unittest.main()
