"""Regression gates for the Stage 14 and archive-audit GitLab workflow."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PLOT = ROOT / "case1/professor_walkthrough/14_PVBESS_Sizing_and_Utilization/generate_stage14_figures.py"
AUDIT = Path(__file__).resolve().parent / "audit_repository_archives.py"


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowChecks(unittest.TestCase):
    def test_source_sha_and_nondominated_eight(self):
        plot = load_file("stage14", PLOT)
        folder = ROOT / "case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17"
        data = plot.read_checked(folder)
        self.assertEqual(len(data["annual"]), 8)
        self.assertEqual(plot.pareto(data["annual"]), {"MC_REF","MC_B9","SS_B9","SS_B10"})

    def test_readonly_duplicate_zip_audit(self):
        auditor = load_file("archive_audit", AUDIT)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            subprocess.run(["git","init","-q",str(folder)], check=True)
            with zipfile.ZipFile(folder / "one.zip","w") as f:
                f.writestr("original.txt","evidence")
            (folder / "two.zip").write_bytes((folder / "one.zip").read_bytes())
            subprocess.run(["git","-C",str(folder),"add","."],check=True)
            before = subprocess.check_output(["git","-C",str(folder),"status","--short"])
            result = auditor.audit(folder)
            self.assertEqual(result["tracked_zip_files"], 2)
            self.assertEqual(result["duplicate_groups"], 1)
            self.assertEqual(result["extra_identical_archives"], 1)
            self.assertEqual(subprocess.check_output(["git","-C",str(folder),"status","--short"]), before)


if __name__=="__main__":
    unittest.main()
