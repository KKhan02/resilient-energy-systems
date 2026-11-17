import unittest,tempfile,zipfile,json
from pathlib import Path
import pandas as pd
from extract_mapped_dispatch_windows import annual,load_events

class TestWindowExtractor(unittest.TestCase):
    def test_reject_partial_year(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.csv';pd.DataFrame({'timestamp_lst':['2025-01-01 00:00:00']}).to_csv(f,index=False)
            with self.assertRaises(ValueError):annual(f)
    def test_ensure_event_count_and_key(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'e.zip'
            with zipfile.ZipFile(f,'w') as z:
                z.writestr('EXTRACTION_QA.json',json.dumps({'issues':[],'verified_failing_ac_cases':126}))
                z.writestr('DEDUPLICATED_CONSTRAINT_EVENTS.csv','scenario,transformer,tier,hardware_family,topology,dispatch,timestamp_lst,failing_pf_length_combinations\nA0,94022,min_cost,archived_reference,mapped,optimized,2025-01-01 19:00:00,1\n')
            with self.assertRaises(ValueError):load_events(f)
if __name__=='__main__':unittest.main()
