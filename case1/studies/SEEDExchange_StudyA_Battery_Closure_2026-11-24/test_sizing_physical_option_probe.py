import unittest
from types import SimpleNamespace
import pandas as pd
from sizing_physical_option_probe import apply_bundle
class BundleTest(unittest.TestCase):
    def fixture(self):
        n=SimpleNamespace(line=pd.DataFrame({"name":["a"],"from_bus":[0],"to_bus":[1],"length_km":[.1],"r_ohm_per_km":[3.3]}),
            bus=pd.DataFrame({"name":["root","house"]}))
        r=pd.DataFrame({"line_index":[0],"line_name":["a"],"from_model_bus":["root"],"to_model_bus":["house"],"kind":["ASSUMED_SERVICE"],"original_length_m":[100.],"original_r_ohm_per_km":[3.3]})
        return n,r
    def test_exact_branch(self):
        n,r=self.fixture();apply_bundle(n,r,1.);self.assertEqual(n.line.at[0,"r_ohm_per_km"],1.65)
    def test_length_mismatch(self):
        n,r=self.fixture()
        with self.assertRaisesRegex(ValueError,"length mismatch"):apply_bundle(n,r,1.6)
        self.assertEqual(n.line.at[0,"r_ohm_per_km"],3.3)
    def test_endpoint_mismatch(self):
        n,r=self.fixture();r.at[0,"to_model_bus"]="wrong"
        with self.assertRaisesRegex(ValueError,"identity mismatch"):apply_bundle(n,r,1.)
if __name__=="__main__":unittest.main()
