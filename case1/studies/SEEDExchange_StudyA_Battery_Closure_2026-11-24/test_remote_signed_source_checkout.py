import unittest
from pathlib import Path
import sys,tempfile
from remote_signed_source_checkout import sha,signed_bytes

class SourceByteTests(unittest.TestCase):
    def test_exact(self):
        b=b"x\n";self.assertEqual(signed_bytes(b,sha(b)),(b,"EXACT"))
    def test_both_directions(self):
        a=b"x\ny\n";b=b"x\r\ny\r\n"
        self.assertEqual(signed_bytes(a,sha(b)),(b,"LF_TO_CRLF"))
        self.assertEqual(signed_bytes(b,sha(a)),(a,"CRLF_TO_LF"))
    def test_changed_content(self):
        with self.assertRaises(ValueError):signed_bytes(b"x\n",sha(b"y\r\n"))
    def test_mixed_newlines(self):
        with self.assertRaises(ValueError):signed_bytes(b"x\r\ny\n",sha(b"x\r\ny\r\n"))
    def test_portable_path(self):
        folder=Path(__file__).resolve().parents[1]/"SEEDExchange_StudyA_PVBESS_v1"
        sys.path.insert(0,str(folder))
        from study_a_pvbess import resolve_signed_v4_path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rel="case1/studies/SEEDExchange_StudyA_LocalPreflight_v4/outputs/run_02"
            (root/rel).mkdir(parents=True)
            old="D:\\historical\\repo"
            m={"repo_root":old,"v4_run_dir":old+"\\"+rel.replace("/","\\")}
            self.assertEqual(resolve_signed_v4_path(root,m),(root/rel).resolve())
            m["v4_run_dir"]=old+"\\wrong"
            with self.assertRaises(ValueError):resolve_signed_v4_path(root,m)
if __name__=="__main__":unittest.main()
