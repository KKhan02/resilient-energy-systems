import unittest
import numpy as np
import pandas as pd
import remote_94022_A1_reserve as r

class ReserveGate(unittest.TestCase):
    def fixture(self):
        ix=pd.date_range("2025-01-01",periods=8760,freq="h")
        a=pd.DataFrame(dict(demand_kw=np.full(8760,2.),pv_dc_available_kw=np.r_[np.zeros(4353),np.ones(4407)]),index=ix)
        h=dict(inverter_kva=12.,battery_power_dc_kw=11.,transformer_kva_assumed_or_evidenced=5.)
        return {"frames":{r.src.REF:a,"test":a.copy()},"hardware":{r.src.REF:h,"test":dict(h)}}
    def test_plan(self):
        r.plan_gate();self.assertEqual(len(r.CASES),6)
    def test_common_night(self):
        self.assertEqual(len(r.common_night(self.fixture())),4353)
    def test_ceiling_gate(self):
        x=self.fixture();x["hardware"]["test"]["battery_power_dc_kw"]=1.
        with self.assertRaisesRegex(ValueError,"ceiling"):r.common_night(x)
    def test_night_mask_gate(self):
        x=self.fixture();x["frames"]["test"].iloc[0,1]=1.
        with self.assertRaisesRegex(ValueError,"identity"):r.common_night(x)

if __name__=="__main__":unittest.main()
