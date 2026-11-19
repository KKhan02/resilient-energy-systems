"""Non-AC source and selection regression tests for the matched AC delta runner."""
import importlib.util
import tempfile
from pathlib import Path
import json
import hashlib
import unittest
from unittest import mock
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('delta_ac',Path(__file__).with_name('ac_delta_replay.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DeltaTests(unittest.TestCase):
    def test_changed_inverter_hours_respect_tolerance(self):
        a=np.zeros(8760)
        b=a.copy()
        b[101]=.0000001
        b[501]=.2
        b[5000]=-1.
        self.assertEqual(m.changed_inverter_hours(a,b).tolist(),[501,5000])

    def test_reject_incomplete_year(self):
        with self.assertRaisesRegex(ValueError,'8760-hour'):
            m.changed_inverter_hours(np.ones(4),np.ones(4))

    def test_reject_nan(self):
        a=np.zeros(8760);b=a.copy();b[42]=np.nan
        with self.assertRaisesRegex(ValueError,'finite'):
            m.changed_inverter_hours(a,b)

    def test_main_preflight_does_not_attempt_AC(self):
        dummy={'MC_REF':{'changed_indexes':[42], 'changed_inverter_hours':1},
               'MC_P33':{'changed_indexes':[84],'changed_inverter_hours':1}}
        data=(None,None,None,None,dummy,{'assignment':'A1'})
        with mock.patch.object(m,'prepare',return_value=data):
            with mock.patch.object(m,'matched_run',side_effect=AssertionError('no AC')) as ac:
                with mock.patch('builtins.print') as printer:
                    m.main(['--preflight-only'])
        report=json.loads(printer.call_args.args[0])
        self.assertEqual(report['status'],'SOURCE_VERIFIED_AC_DELTA_PREFLIGHT')
        self.assertNotIn('changed_indexes',report['plan']['MC_REF'])
        ac.assert_not_called()

if __name__=='__main__':
    unittest.main()
