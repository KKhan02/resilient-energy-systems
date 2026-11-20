"""Synthetic new-hardware nine-factor screening checks (no pandapower execution)."""
import importlib.util
import json
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
import pandas as pd

file=Path(__file__).with_name("new_hardware_nine_factor.py")
spec=importlib.util.spec_from_file_location("nh_nine_factor",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NineFactorTests(unittest.TestCase):
    def test_factor_grid_is_complete(self):
        self.assertEqual(len(m.FACTORS),9)
        self.assertEqual(m.FACTORS[0],(.95,1.))
        self.assertEqual(m.FACTORS[-1],(1.,1.6))

    def test_accepts_only_named_relative_case_paths(self):
        with tempfile.TemporaryDirectory() as d:
            expected=Path(d)/"MC_B10"/"CHANGED_HOUR_AC.csv"
            self.assertEqual(m.checked_case_path(Path(d),"MC_B10",
                r"MC_B10\CHANGED_HOUR_AC.csv"),expected)
            with self.assertRaisesRegex(ValueError,"Unexpected signed"):
                m.checked_case_path(Path(d),"MC_B10",r"SS_B10\CHANGED_HOUR_AC.csv")
            with self.assertRaisesRegex(ValueError,"Unexpected signed"):
                m.checked_case_path(Path(d),"MC_B10","MC_B10/../escape.csv")

    def test_synthetic_pandapower_feasibility_screen(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.955,
           "max_v_pu":1.02,"max_trafo_pct":99.4,"max_line_pct":7.1,
           "loss_kw":.1,"pcc_kva":4.8}
        self.assertTrue(m.ac_screen(r)["ac_feasible"])
        bad={**r,"ac_feasible":False,"max_trafo_pct":101}
        self.assertFalse(m.ac_screen(bad)["ac_feasible"])

    def test_inconsistent_solver_flag_is_rejected(self):
        r={"status":"CONVERGED","ac_feasible":True,"min_v_pu":.955,
           "max_v_pu":1.02,"max_trafo_pct":102,"max_line_pct":7.1,
           "loss_kw":.1,"pcc_kva":4.8}
        with self.assertRaisesRegex(ValueError,"feasibility flag disagrees"):
            m.ac_screen(r)

    def test_nonconvergent_metrics_are_explicit_not_nan(self):
        rec={"status":"NOT_CONVERGED","ac_feasible":False}
        self.assertFalse(m.ac_screen(rec)["ac_feasible"])
        x=pd.Series([float("nan"),None])
        self.assertIsNone(m.finite_extreme(x,"min"))
        self.assertIsNone(m.finite_extreme(x,"max"))

    def test_stress_hour_numeric_check_rejects_tampering(self):
        saved=pd.DataFrame([{"timestamp_lst":"2025-11-27 20:00:00",
            "old_trafo_pct":107.43117,"new_trafo_pct":92.53,
            "old_min_v_pu":.9542,"new_min_v_pu":.9572,
            "old_loss_kw":.19,"new_loss_kw":.17,
            "old_ac_feasible":False,"new_ac_feasible":True}])
        observed={"max_trafo_pct":90.,"min_v_pu":.9572,
                  "loss_kw":.17,"ac_feasible":True}
        with self.assertRaisesRegex(ValueError,"stress solver mismatch"):
            m.compare_stress_stored(saved,"MC_B10","candidate",
                "2025-11-27 20:00:00",observed)


    def test_source_gate_accepts_complete_case_payload(self):
        """Replays the exact DataFrame-vs-case-dict boundary that failed locally."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            cases={}
            for case in ("MC_B10","SS_B10","SS_P45_B9"):
                cases[case]={
                    "original":pd.DataFrame({"inverter_ac_kw":[1.0]}),
                    "candidate":pd.DataFrame({"inverter_ac_kw":[1.0]}),
                    "changed":[10,11],
                    "energy_manifest_sha256":"energy_"+case,
                    "ac_manifest":{"ac_hourly_sha256":"ac_"+case}}
            document={
                "status":"STRESS_PASS_ONLY_ALL_NINE_PENDING",
                "case_count":3,
                "cases":{case:{} for case in cases},
                "all_nine_factors_tested":False,
                "stress_factor":{"pf":.95,"length_factor":1.6}}
            (root/"RUN_MANIFEST.json").write_text(json.dumps(document))
            nh=SimpleNamespace(
                CASES=tuple(cases),
                preflight=lambda repo: (None,None,None,{},cases,None))
            called=[]
            def check_gate(nh_arg,root_arg,payload,metadata,mcase,case):
                self.assertIs(payload,cases[case])
                self.assertIs(metadata,cases[case])
                self.assertIn("candidate",payload)
                self.assertIn("changed",payload)
                called.append(case)
                return {"candidate_sha256":"trial_"+case,
                        "changed_sha256":"changes_"+case,
                        "candidate_mode":"EXACT_SIGNED_BYTES",
                        "changed_mode":"EXACT_SIGNED_BYTES"}
            with patch.object(m,"import_nh",return_value=nh), \
                 patch.object(m,"exact_source_stress",side_effect=check_gate):
                result=m.verify_source(root,root)
            self.assertEqual(set(called),set(cases))
            self.assertEqual(result[-1]["planned_changed_hour_AC_solves"],108)
            self.assertEqual(result[-1]["annual_ac_cases_completed_by_this_screen"],0)
            self.assertEqual(result[-1]["status"],
                             "SIGNED_3CASE_STRESS_PREFLIGHT_PASS_NO_NEW_AC")

    def test_original_stress_gate_realistic_signed_annual_fixture(self):
        """Verify a 8760-row saved candidate and changed-hour CSV, no AC solver."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            case="MC_B10"
            directory=root/case
            directory.mkdir()
            frame=pd.DataFrame(
                {"inverter_ac_kw":[1.0]*8760},
                index=pd.date_range("2025-01-01",periods=8760,freq="h"))
            frame.index.name="timestamp_lst"
            datafile=directory/"CANDIDATE_ENERGY_8760.csv"
            frame.to_csv(datafile,float_format="%.10f")
            changedfile=directory/"CHANGED_HOUR_AC.csv"
            changed=pd.DataFrame({
                "case_id":[case,case],
                "timestamp_lst":[str(frame.index[10]),str(frame.index[11])],
                "new_ac_feasible":[True,True]})
            changed.to_csv(changedfile,index=False)
            signed={"original":frame.copy(),"candidate":frame,
                    "changed":[10,11],"energy_manifest_sha256":"energy_sha",
                    "ac_manifest":{"ac_hourly_sha256":"ac_sha"}}
            manifest={"source_energy_manifest_sha256":"energy_sha",
                "source_ac_hourly_sha256":"ac_sha","changed_hour_count":2,
                "stress_result":{
                    "status":"STRESS_PASS_ONLY_ALL_NINE_PENDING",
                    "corrected_bad_hours":0,"baseline_bad_hours":2,
                    "source_original_ac_sha256":"ac_sha",
                    "candidate_energy_csv":case+r"\CANDIDATE_ENERGY_8760.csv",
                    "changed_hour_csv":case+r"\CHANGED_HOUR_AC.csv",
                    "candidate_energy_sha256":hashlib.sha256(datafile.read_bytes()).hexdigest(),
                    "changed_hour_sha256":hashlib.sha256(changedfile.read_bytes()).hexdigest()}}
            def check_text(path,expected):
                actual=hashlib.sha256(path.read_bytes()).hexdigest()
                if actual!=expected:
                    raise ValueError("Signed bytes changed")
                return "EXACT_SIGNED_BYTES"
            nh=SimpleNamespace(
                KNOWN_BASELINE_FAILURES={case:{"t1","t2"}},
                verify_signed_text=check_text)
            got=m.exact_source_stress(nh,root,signed,signed,manifest,case)
            self.assertEqual(got["candidate_mode"],"EXACT_SIGNED_BYTES")
            self.assertEqual(len(got["original_stress"]),2)
            self.assertEqual(got["changed_sha256"],
                             manifest["stress_result"]["changed_hour_sha256"])

if __name__=="__main__":
    unittest.main()
