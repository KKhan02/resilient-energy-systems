import unittest
from sizing_priority_pilot import designs,hardware_tuple,FAMILIES,device_input

class PilotTests(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(list(designs("oversize"))),5)
        self.assertEqual(len(list(designs("constraint"))),2)
    def test_no_power_or_inverter_change(self):
        for family in FAMILIES:
            for _,h in designs(family):
                self.assertEqual(hardware_tuple(h)[2:],FAMILIES[family][3][2:])
    def test_continuous_bank_and_pv_limits(self):
        for family in FAMILIES:
            for _,h in designs(family):
                self.assertLessEqual(h["battery_power_dc_kw"],2.24*h["battery_modules"])
                self.assertLessEqual(h["pv_panels"]*.435,1.5*h["inverter_kva"])
    def test_isolated_and_joint(self):
        for tag,h in designs("oversize"):
            self.assertEqual((h["pv_panels"]!=26)+(h["battery_modules"]!=5),2 if tag=="P20_B4" else 1)
        for _,h in designs("constraint"):
            self.assertEqual(h["pv_panels"],27)

if __name__=="__main__":
    unittest.main()
