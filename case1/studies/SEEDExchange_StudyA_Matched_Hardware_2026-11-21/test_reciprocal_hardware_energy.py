"""Source-only tests for 16 reciprocal A0/A1 fixed-hardware energy comparisons.

These tests never open an actual PyPSA solver, run a power flow, or change
historical source data. Local full-source preflight is a separate command.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

file=Path(__file__).with_name("reciprocal_hardware_energy.py")
spec=importlib.util.spec_from_file_location("matched_reciprocal_energy",file)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample_trace(n=4):
    idx=pd.date_range("2025-01-01",periods=8760,freq="h")
    return pd.DataFrame({f"H{i:02d}":np.ones(8760) for i in range(n)},index=idx)

def sample_frame(trace,import_kw=None):
    d=trace.sum(axis=1).to_numpy(float)
    val=d if import_kw is None else np.full(8760,import_kw)
    return pd.DataFrame({
        "demand_kw":d,"grid_import_kw":val,"grid_export_kw":0.,
        "unserved_kw":0.,"pv_dc_available_kw":0.,
        "curtailed_pv_dc_kw":0.,"battery_charge_dc_kw":0.,
        "battery_discharge_dc_kw":0.,"inverter_ac_kw":0.,
        "battery_soc_usable_kwh":np.ones(8760),
        "pcc_q_kvar_proxy":0.,"pcc_p_kw":val,
        "pcc_kva_proxy":val},index=trace.index)

def hw():
    return {"pv_panels":17,"battery_modules":3,"battery_power_dc_kw":5.,
            "inverter_kva":6.,"transformer_kva_assumed_or_evidenced":5.}

class ReciprocalHardwareTests(unittest.TestCase):
    def test_signed_exact_and_windows_CRLF_reconstruction(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"x.csv"
            f.write_bytes(b"a,b\r\n1,2\r\n")
            signed=hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertEqual(m.checked_bytes(f,signed),"EXACT")
            f.write_bytes(b"a,b\n1,2\n")
            self.assertEqual(m.checked_bytes(f,signed),"GIT_LF_EQUALS_SIGNED_CRLF")

    def test_tampered_signed_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"signed.csv";f.write_bytes(b"new\n")
            expected=hashlib.sha256(b"old\r\n").hexdigest()
            with self.assertRaisesRegex(ValueError,"Signed source differs"):
                m.checked_bytes(f,expected)

    def test_recipient_source_identity(self):
        row={"donor_assignment":"A0","target_assignment":"A1",
             "tier":"min_cost","transformer":"113699"}
        self.assertEqual(m.key(row),"A0_113699_min_cost_to_A1")
        self.assertEqual(m.REVERSE_KEY,"A0_113699_min_cost_to_A1")
        self.assertEqual(m.PILOT_KEY,"A1_113699_min_cost_to_A0")

    def test_exact_device_equality_including_power(self):
        a={"hw":hw()}
        b={"hw":hw()}
        self.assertTrue(m.exact_device_pair(a,b))
        b["hw"]["battery_power_dc_kw"]+=1e-10
        self.assertFalse(m.exact_device_pair(a,b))

    def test_source_alias_same_hardware_both_directions(self):
        rows=[{"donor_assignment":x,"target_assignment":y,
               "tier":"min_cost","transformer":"106039"}
              for x,y in (("A0","A1"),("A1","A0"))]
        base={"hw":hw(),
              "json":{"original_pv_source_sha256":"S",
                      "input_manifest_sha256":"M"},
              "summary":{"annual_equipment_usd":100.}}
        originals={m.key(r):{"hw":dict(base["hw"]),
                             "json":dict(base["json"]),
                             "summary":dict(base["summary"])} for r in rows}
        aliases=m.signed_existing_cross_reuse(rows,originals)
        self.assertEqual(set(aliases),{m.key(r) for r in rows})
        originals[m.key(rows[0])]["hw"]["inverter_kva"]=6.1
        self.assertEqual(m.signed_existing_cross_reuse(rows,originals),{})

    def test_all_16_roster_selects_one_reverse(self):
        rows=[{"donor_assignment":d,"target_assignment":
               ("A1" if d=="A0" else "A0"),
               "transformer":t,"tier":tier}
               for d in m.ASSIGNMENTS for tier in m.TIERS for t in m.MODELLED]
        self.assertEqual(len(m.select_keys(rows,"full")),16)
        self.assertEqual(m.select_keys(rows,"reverse"),[m.REVERSE_KEY])

    def test_synthetic_8760_balance_and_protected_power(self):
        trace=sample_trace()
        frame=sample_frame(trace)
        values=m.validate_dispatch(frame,trace,hw())
        self.assertEqual(values["demand_kwh"],4*8760)
        self.assertEqual(values["grid_import_kwh"],4*8760)
        self.assertEqual(values["battery_discharge_dc_kwh"],0)

    def test_simultaneous_charge_discharge_fails(self):
        trace=sample_trace();frame=sample_frame(trace)
        frame.at[frame.index[0],"battery_charge_dc_kw"]=.2
        frame.at[frame.index[0],"battery_discharge_dc_kw"]=.2
        with self.assertRaisesRegex(ValueError,"Simultaneous"):
            m.validate_dispatch(frame,trace,hw())

    def test_cyclic_SOC_error_fails(self):
        trace=sample_trace();frame=sample_frame(trace)
        frame.at[frame.index[100],"battery_soc_usable_kwh"]=2.
        with self.assertRaisesRegex(ValueError,"Cyclic battery"):
            m.validate_dispatch(frame,trace,hw())

    def test_below_physical_SOC_fails(self):
        trace=sample_trace();frame=sample_frame(trace)
        frame.at[frame.index[100],"battery_soc_usable_kwh"]=.1
        with self.assertRaisesRegex(ValueError,"Physical 20% SOC"):
            m.validate_dispatch(frame,trace,hw())

    def test_export_and_ens_are_rejected(self):
        trace=sample_trace();frame=sample_frame(trace)
        frame.at[frame.index[300],"unserved_kw"]=.1
        with self.assertRaisesRegex(ValueError,"zero export/ENS"):
            m.validate_dispatch(frame,trace,hw())

    def test_immutable_case_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            case="A0_113699_min_cost_to_A1"
            root=Path(d)
            m.save_case(root,case,{"status":"ENERGY_ONLY","AC_verified":False})
            self.assertTrue((root/case/"CASE_RECEIPT.json").exists())
            with self.assertRaises(FileExistsError):
                m.save_case(root,case,{"status":"ALTERED"})

    def test_recombine_eight_matched_34_house_scenarios(self):
        counts={"A0":{"106039":12,"94022":10,"113699":4,"85398":4},
                "A1":{"106039":11,"94022":8,"113699":6,"85398":5}}
        def metrics(houses):
            demand=houses*1898.
            return {x:(demand if x in ("demand_kwh","grid_import_kwh")
                       else 0.) for x in m.METRICS}
        def summary(houses):
            imports=houses*1898.
            return {"annual_equipment_usd":100.,
                    "annual_grid_import_usd":.29*imports,
                    "annual_total_usd":100.+.29*imports}
        roster=[];originals={};completed={}
        for donor in m.ASSIGNMENTS:
            for tier in m.TIERS:
                for tr in m.MODELLED:
                    target="A1" if donor=="A0" else "A0"
                    row={"donor_assignment":donor,"target_assignment":target,
                         "transformer":tr,"tier":tier}
                    roster.append(row)
                    k=m.key(row)
                    originals[k]={"hw":hw(),"metrics":metrics(counts[donor][tr]),
                                  "summary":summary(counts[donor][tr])}
                    completed[k]={"target_yearly_energy_metrics":metrics(counts[target][tr]),
                                  "target_model_summary":summary(counts[target][tr])}
        shared={tier:{"hw":hw(),"metrics":metrics(4),"summary":summary(4)}
                for tier in m.TIERS}
        portfolios,pairs=m.recombine(originals,shared,completed,roster)
        self.assertEqual(len(portfolios),8)
        self.assertEqual(len(pairs),4)
        self.assertTrue(all(x["households"]==34 and
                            x["annual_demand_kwh"]==64532. for x in portfolios))
        self.assertTrue(all(abs(x["A1_minus_A0_import_kwh"])<1e-8 for x in pairs))
        self.assertTrue(all(x["AC_verified"] is False for x in portfolios))


    def test_normalized_signed_manifest_lf_or_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"receipt.json"
            signed=hashlib.sha256(b"a\n").hexdigest()
            f.write_bytes(b"a\r\n")
            self.assertEqual(m.normalized_lf_sha(f),signed)
            f.write_bytes(b"a\n")
            self.assertEqual(m.normalized_lf_sha(f),signed)

    def test_signed_reverse_reuse_reduces_13_to_12(self):
        full=[m.key({"donor_assignment":d,"target_assignment":
                     ("A1" if d=="A0" else "A0"),
                     "transformer":tr,"tier":tier})
              for d in m.ASSIGNMENTS for tr in m.MODELLED for tier in m.TIERS]
        cross={"A0_106039_min_cost_to_A1":None,"A1_106039_min_cost_to_A0":None}
        self.assertEqual(m.expected_new_lp_count(full,cross,False),13)
        self.assertEqual(m.expected_new_lp_count(full,cross,True),12)
        self.assertEqual(m.expected_new_lp_count([m.REVERSE_KEY],cross,False),1)

    def test_missing_or_tampered_reverse_pilot_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                m.verify_reverse_pilot(Path(d),None,{},None,None,{},{})

    def test_bad_population_blocks_recombination(self):
        with self.assertRaisesRegex(ValueError,"Missing matched portfolios"):
            m.recombine({}, {}, {}, [])

if __name__=="__main__":
    unittest.main()
