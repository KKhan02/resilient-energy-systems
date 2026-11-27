import unittest
import pandas as pd
import remote_113699_reciprocal_gap as r

class GapGate(unittest.TestCase):
    def test_population(self):
        r.plan_gate()
        self.assertEqual(len(r.CASES)*len(r.FACTORS)*8760,35040)
        self.assertEqual([len(r.IDS[c]) for c in r.CASES],[6,4])
    def test_change_detection(self):
        i=pd.date_range("2025-01-01",periods=3,freq="h")
        a=pd.DataFrame({"inverter_ac_kw":[0.,1.,2.]},index=i)
        b=a.copy();b.iloc[1,0]=1.25
        self.assertEqual(r.changes(a,b),[str(i[1])])
        self.assertEqual(r.changes(a,a),[])
        with self.assertRaisesRegex(ValueError,"chronology"):r.changes(a,b.iloc[1:])
    def test_frozen_shift_plan(self):
        self.assertEqual(len(r.SHIFTS),2)
        self.assertAlmostEqual(sum(z[2] for z in r.SHIFTS),.9043401786,places=10)

if __name__=="__main__":unittest.main()
