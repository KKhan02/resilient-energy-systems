"""Synthetic signed-source validation only. No PyPSA solver execution."""
import hashlib
import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

p=Path(__file__).with_name("matched_hardware_pilot.py")
spec=importlib.util.spec_from_file_location("matched_control_pilot",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PilotSourceTests(unittest.TestCase):
    def test_direct_signed_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"file.csv";f.write_bytes(b"a,b\r\n1,2\r\n")
            want=hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertEqual(m.signed_bytes(f,want),"EXACT")

    def test_exact_git_lf_to_signed_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"file.csv";f.write_bytes(b"a,b\n1,2\n")
            want=hashlib.sha256(b"a,b\r\n1,2\r\n").hexdigest()
            self.assertEqual(m.signed_bytes(f,want),
                             "SIGNED_CRLF_RECONSTRUCTED_FROM_GIT_LF")

    def test_changed_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"file.csv";f.write_bytes(b"a,b\n2,1\n")
            want=hashlib.sha256(b"a,b\r\n1,2\r\n").hexdigest()
            with self.assertRaisesRegex(ValueError,"SHA mismatch"):
                m.signed_bytes(f,want)

    def test_only_approved_pilot_identity(self):
        self.assertEqual(m.TRIAL_CASE["transformer"],"113699")
        self.assertEqual(m.TRIAL_CASE["donor"],"A1")
        self.assertEqual(m.TRIAL_CASE["target"],"A0")
        self.assertEqual(m.TRIAL_CASE["tier"],"min_cost")

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/(m.OUTPUT_STEM+"1")).mkdir()
            self.assertEqual(m.choose_output(root),root/(m.OUTPUT_STEM+"2"))

if __name__=="__main__":
    unittest.main()
