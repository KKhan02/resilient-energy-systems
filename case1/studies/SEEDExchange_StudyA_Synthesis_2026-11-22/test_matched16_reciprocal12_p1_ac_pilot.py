"""No-solver synthetic regression for bounded P1 selection."""
import unittest
import matched16_reciprocal12_p1_ac_pilot as m

def mock(case):
    rows = [{"reciprocal_case":case,"timestamp_lst":ts,
             "pv_dc_available_kw":"0.0","night_Q_disabled_source_rule":"True",
             "selection_reason":"OTHER_EQUIPMENT_ARCHIVE_STRESS"}
            for ts in m.ANCHORS[case]]
    rows.append({"reciprocal_case":case,"timestamp_lst":"2025-09-04 12:00:00",
                 "pv_dc_available_kw":"12.0","night_Q_disabled_source_rule":"False",
                 "selection_reason":"PV_AVAILABILITY_PEAK"})
    i=0
    while len(rows)<25:
        rows.append({"reciprocal_case":case,"timestamp_lst":f"2025-01-01 {i:02d}:00:00",
                     "pv_dc_available_kw":"0.0","night_Q_disabled_source_rule":"True",
                     "selection_reason":"GROSS_LOAD_SECONDARY"})
        i+=1
    return rows

class P1SelectionTests(unittest.TestCase):
    def test_count(self):
        self.assertEqual(len(m.ANCHORS),6)
        self.assertEqual(sum(len(x)+1 for x in m.ANCHORS.values()),18)

    def test_pf(self):
        self.assertEqual(m.PF,(.98,.95))

    def test_94022(self):
        c="A1_94022_min_cost_to_A0"
        self.assertEqual(len(m.choose_case(c,mock(c))),3)

    def test_113699(self):
        c="A0_113699_ss90_to_A1"
        self.assertEqual(len(m.choose_case(c,mock(c))),4)

    def test_106039(self):
        c="A1_106039_ss90_to_A0"
        self.assertEqual(len(m.choose_case(c,mock(c))),2)

    def test_unknown_case(self):
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            m.choose_case("A0_85398_min_cost_to_A1",[])

    def test_missing_annual_anchor(self):
        c="A0_113699_min_cost_to_A1"
        x=mock(c)
        x[0]["timestamp_lst"]="2025-02-01 18:00:00"
        with self.assertRaisesRegex(ValueError,"Missing archived"):
            m.choose_case(c,x)

    def test_duplicate_timestamp(self):
        c="A0_106039_ss90_to_A1"
        x=mock(c)
        x[-1]["timestamp_lst"]=x[0]["timestamp_lst"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            m.choose_case(c,x)

    def test_invalid_night(self):
        c="A0_106039_ss90_to_A1"
        x=mock(c)
        x[0]["pv_dc_available_kw"]="0.1"
        with self.assertRaisesRegex(ValueError,"not night"):
            m.choose_case(c,x)

    def test_no_day(self):
        c="A1_94022_ss90_to_A0"
        x=mock(c)
        x[2]["selection_reason"]="GROSS_LOAD_SECONDARY"
        with self.assertRaisesRegex(ValueError,"No source-selected"):
            m.choose_case(c,x)

if __name__=="__main__":
    unittest.main()
