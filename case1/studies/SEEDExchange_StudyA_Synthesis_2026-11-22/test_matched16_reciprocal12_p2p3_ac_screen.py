"""Source-only P2/P3 selection contract, no numerical solver."""
import unittest
import matched16_reciprocal12_p2p3_ac_screen as a

def fixture():
    register=[]; rows=[]
    for c, band in {**{c:"P1" for c in a.p1.ANCHORS},**a.CASES}.items():
        tr=c.split("_")[1]; assignment=c[-2:]
        register.append({"reciprocal_case":c,"source_only_priority_band":band,
                         "transformer":tr,"target_assignment":assignment})
        for i in range(25):
            rows.append({"reciprocal_case":c,"transformer":tr,
                         "target_assignment":assignment,"timestamp_lst":f"2025-01-{i+1:02d} 20:00:00",
                         "selection_reason":"SOURCE_TEST"})
    return register,rows

class SourceContract(unittest.TestCase):
    def test_all_six_no_P1(self):
        reg,rows=fixture()
        selected=a.choose_all(reg,rows)
        self.assertEqual(len(selected),150)
        self.assertEqual({c for c,_,_ in selected},set(a.CASES))
        self.assertEqual(len(selected)*len(a.PF),300)
    def test_duplicate_hour_rejected(self):
        reg,rows=fixture()
        rows[1]=dict(rows[0])
        with self.assertRaisesRegex(ValueError,"25 unique"):
            a.choose_all(reg,rows)
    def test_wrong_assignment_rejected(self):
        reg,rows=fixture()
        rows[0]["target_assignment"]="wrong"
        with self.assertRaisesRegex(ValueError,"assignment mismatch"):
            a.choose_all(reg,rows)
    def test_wrong_band_rejected(self):
        reg,rows=fixture()
        next(r for r in reg if r["reciprocal_case"] in a.CASES)["source_only_priority_band"]="P1"
        with self.assertRaisesRegex(ValueError,"priority band"):
            a.choose_all(reg,rows)
    def test_missing_hour_rejected(self):
        reg,rows=fixture()
        with self.assertRaisesRegex(ValueError,"300-hour"):
            a.choose_all(reg,rows[:-1])

if __name__=="__main__":
    unittest.main()
