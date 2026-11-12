import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from process_identity_v02 import candidate_metrics
from price_process_v03 import price_processes


def rates(x):return np.exp(np.cumsum(x))


class ConsistentPriceProcesses(unittest.TestCase):
    def test_no_trough_acceleration_has_complete_evidence(self):
        p=rates([.0005]*100+[.006]*150)
        records,_=price_processes(p,candidate_metrics(p))
        self.assertGreater(len(records),0)
        self.assertTrue((records.end>=records.evidence_end).all())

    def test_new_enhancement_does_not_cut_old_evidence(self):
        p=rates([.0005]*100+[.006]*65+[.012]*150)
        records,_=price_processes(p,candidate_metrics(p))
        self.assertGreaterEqual(len(records),2)
        self.assertEqual(records.family.nunique(),1)
        self.assertTrue(records.end.eq(len(p)-1).all())
        self.assertTrue(records.right_censored.all())

    def test_pause_is_not_price_failure(self):
        p=rates([.0005]*100+[.006]*90+[0.]*25+[.009]*100)
        records,_=price_processes(p,candidate_metrics(p))
        self.assertFalse(records.end_reason.eq('PAUSE20').any())
        self.assertTrue(records.end.eq(len(p)-1).all())

    def test_permitted_pullback_then_recovery(self):
        p=rates([-.003]*100+[.008]*25+[-.004]*20+[.008]*100)
        records,_=price_processes(p,candidate_metrics(p))
        self.assertGreater(len(records),0)
        self.assertTrue(records.end.eq(len(p)-1).all())

    def test_real_breach_ends_before_breach_day(self):
        p=rates([-.003]*100+[.006]*100+[-.02]*30)
        records,_=price_processes(p,candidate_metrics(p))
        ended=records[~records.right_censored]
        self.assertGreater(len(ended),0)
        self.assertTrue(ended.breach_day.eq(ended.end+1).all())
        self.assertTrue((ended.evidence_end<=ended.end).all())

    def test_steady_growth_not_repeated_new_heat(self):
        p=rates([-.003]*100+[.006]*400)
        records,assignments=price_processes(p,candidate_metrics(p))
        self.assertGreater(len(records),0)
        self.assertLessEqual(len(records),2)
        self.assertEqual(len(assignments),int(candidate_metrics(p).valid.sum()))


if __name__=='__main__':unittest.main()
