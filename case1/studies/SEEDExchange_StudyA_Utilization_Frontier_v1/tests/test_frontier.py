import importlib.util
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

SCRIPT=Path(__file__).resolve().parents[1]/'run_a1_106039_frontier.py'
spec=importlib.util.spec_from_file_location('frontier_tested',SCRIPT)
f=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=f
spec.loader.exec_module(f)

class SyntheticModel:
    PANEL_KW=.435
    BATTERY_USABLE_KWH=4.325
    BAT_POWER_USD_KW=0.
    PV_USD_KWP=739.86
    BAT_USD_KWH=276.16
    INV_USD_KW_AC=666.
    IMPORT_USD_KWH=.29
    @staticmethod
    def annualized_rate(amount,years):
        return .12*amount

class Tests(unittest.TestCase):
    def test_candidate_counts(self):
        self.assertEqual(len(f.REFERENCE),2)
        self.assertEqual(len(f.PILOT_IDS),6)
        self.assertEqual(len(f.FULL_IDS),10)
        self.assertEqual(len(f.all_cases()),12)
        self.assertEqual(len(set(f.FULL_IDS)),10)
    def test_all_hardware_passes(self):
        for design in f.all_cases().values():self.assertTrue(f.validate_device(design))
    def test_inverter_dc_pv_constraint(self):
        with self.assertRaisesRegex(ValueError,'ratio'):
            f.validate_device(dict(panels=49,modules=8,battery_kw=12.,inverter_kva=12.))
    def test_bank_current(self):
        with self.assertRaisesRegex(ValueError,'Deye'):
            f.validate_device(dict(panels=41,modules=8,battery_kw=20.,inverter_kva=20.))
    def test_inverter_battery_port(self):
        with self.assertRaisesRegex(ValueError,'port'):
            f.validate_device(dict(panels=41,modules=8,battery_kw=13.,inverter_kva=12.))
    @staticmethod
    def synthetic_frame():
        e=pd.DataFrame(index=f.INDEX)
        e.index.name='timestamp_lst'
        e['demand_kw']=20878/8760
        e['pv_dc_available_kw']=21657.242803252095/8760
        e['curtailed_pv_dc_kw']=2443.604268953586/8760
        e['battery_charge_dc_kw']=0.
        e['battery_discharge_dc_kw']=0.
        e['battery_soc_usable_kwh']=1.832
        e['inverter_ac_kw']=0.
        e['grid_import_kw']=e.demand_kw
        e['grid_export_kw']=0.
        e['unserved_kw']=0.
        return e
    def test_chronology(self):
        frame=self.synthetic_frame();f.check_chronology(frame)
        frame.index=frame.index.where(frame.index!=frame.index[-1],frame.index[0])
        with self.assertRaisesRegex(ValueError,'timestamps'):f.check_chronology(frame)
    def test_export(self):
        frame=self.synthetic_frame();frame.iloc[0,frame.columns.get_loc('grid_export_kw')]=.1
        with self.assertRaisesRegex(ValueError,'Export'):f.check_chronology(frame)
    def test_reference_cost_and_months(self):
        frame=self.synthetic_frame()
        row=f.case_summary('MC_REF',f.REFERENCE['MC_REF'],frame,SyntheticModel,'reference')
        self.assertEqual(row['battery_modules'],8)
        self.assertAlmostEqual(row['annual_demand_kwh'],20878,places=5)
        self.assertEqual(len(f.monthly('MC_REF',frame)),12)
        self.assertGreater(row['annual_total_usd'],row['annual_equipment_usd'])
    def test_manifest_data_guard(self):
        self.assertEqual(f.REFERENCE['SS_REF']['panels'],49)
        self.assertEqual(f.CANDIDATES['SS_P45']['panels'],45)
        self.assertEqual(f.CANDIDATES['SS_B10']['modules'],10)
    def test_signed_csv_crlf_exact_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'energy_hourly_2025.csv'
            signed=b'timestamp_lst,demand_kw\r\n2025-01-01 00:00:00,4\r\n'
            expected=hashlib.sha256(signed).hexdigest()
            path.write_bytes(signed)
            self.assertEqual(f.verify_energy_csv_signature(path,expected),'SIGNED_BYTES_MATCH')
            path.write_bytes(signed.replace(b'\r\n',b'\n'))
            self.assertEqual(f.verify_energy_csv_signature(path,expected),'EXACT_GIT_LF_TO_SIGNED_CRLF')
            path.write_bytes(b'timestamp_lst,demand_kw\n2025-01-01 00:00:00,9\n')
            with self.assertRaisesRegex(ValueError,'differs'):
                f.verify_energy_csv_signature(path,expected)
            path.write_bytes(b'timestamp_lst,demand_kw\r\n2025-01-01 00:00:00,4\n')
            with self.assertRaisesRegex(ValueError,'differs'):
                f.verify_energy_csv_signature(path,expected)

    def test_full_preflight_refuses_missing_pilots(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError,'six existing signed pilot'):
                f.preflight_existing({'repo':Path(tmp)},'full',Path(tmp)/'not_present')

    def test_zip_no_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'data';out.mkdir();(out/'a.txt').write_text('ok')
            archive=Path(t)/'a.zip';f.package_zip(out,archive)
            with self.assertRaises(FileExistsError):f.package_zip(out,archive)

if __name__=='__main__':unittest.main()
