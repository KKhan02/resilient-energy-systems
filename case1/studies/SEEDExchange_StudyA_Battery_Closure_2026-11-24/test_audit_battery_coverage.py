import tempfile
import unittest
import hashlib
from pathlib import Path
import pandas as pd
from audit_battery_coverage import native_names, reciprocal_names, signed, scalar_proxy, describe, check_dispatch

class AuditTests(unittest.TestCase):
    def test_roster_counts(self):
        self.assertEqual(len(set(native_names())),18)
        self.assertEqual(len(set(reciprocal_names())),16)
    def test_newline_guard(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"x"
            p.write_bytes(b"a\nb\n")
            self.assertEqual(signed(p,hashlib.sha256(b"a\r\nb\r\n").hexdigest()),"EXACT_NEWLINE_NORMALIZATION")
            with self.assertRaises(ValueError):
                signed(p,"0"*64)
    def test_scalar_proxy_includes_q(self):
        f=pd.DataFrame({"demand_kw":[4.],"grid_import_kw":[4.]})
        self.assertAlmostEqual(float(scalar_proxy(f,5.,1.)[0]),80.)
        self.assertGreater(float(scalar_proxy(f,5.,.95)[0]),80.)
    def test_instantaneous_headroom_is_bounded(self):
        f=pd.DataFrame({"demand_kw":[0.],"pv_dc_available_kw":[3.],"grid_import_kw":[0.],
            "curtailed_pv_dc_kw":[3.],"battery_charge_dc_kw":[0.],"battery_discharge_dc_kw":[0.],
            "battery_soc_usable_kwh":[.229],"inverter_ac_kw":[0.],"grid_export_kw":[0.],"unserved_kw":[0.]})
        hw={"battery_modules":1,"battery_power_dc_kw":1.,"inverter_kva":2.,"transformer_kva_assumed_or_evidenced":5.}
        self.assertEqual(check_dispatch(f,hw,.229,True),0.)
        self.assertEqual(describe(f,hw)["instantaneous_extra_charge_upper_sum_dc_kwh"],1.)
        f["battery_soc_usable_kwh"]=4.325
        self.assertEqual(describe(f,hw)["instantaneous_extra_charge_upper_sum_dc_kwh"],0.)
        with self.assertRaises(ValueError):
            check_dispatch(f,hw,.229,True)

if __name__=="__main__":
    unittest.main()
