import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from process_identity_v02 import candidate_metrics, segment


def path(rates):
    return np.exp(np.cumsum(np.asarray(rates)))


class ProcessSemantics(unittest.TestCase):
    def test_constant_growth_is_not_new_heating(self):
        m = candidate_metrics(path([.005]*260))
        self.assertFalse(m.valid.any())

    def test_monotonic_acceleration_needs_no_trough(self):
        p = path([.0005]*100+[.006]*150)
        self.assertTrue((np.diff(p)>0).all())
        m = candidate_metrics(p)
        self.assertTrue((m.valid & m.kind.eq('HEATING')).any())
        phases,_ = segment(p,m)
        self.assertGreaterEqual(len(phases),1)

    def test_weak_to_strong(self):
        m = candidate_metrics(path([-.003]*100+[.006]*150))
        self.assertTrue((m.valid & m.kind.eq('WARMING')).any())

    def test_bounce_that_reverses_fails(self):
        p = path([-.003]*100+[.012]*12+[-.012]*20+[0.]*130)
        m = candidate_metrics(p)
        at = m[m.position.eq(99)].iloc[0]
        self.assertTrue(at.amplitude)
        self.assertFalse(at.valid)

    def test_new_acceleration_keeps_parent_identity(self):
        p = path([.0005]*100+[.006]*65+[.012]*150)
        phases,_ = segment(p,candidate_metrics(p))
        self.assertGreaterEqual(len(phases),2)
        self.assertEqual(phases.parent.nunique(),1)
        self.assertTrue(phases.end_reason.eq('NEW_HEATING_PHASE').any())

    def test_price_pause_ends_parent_without_window_merging(self):
        p = path([.0005]*100+[.006]*90+[0.]*25+[.009]*100)
        phases,_ = segment(p,candidate_metrics(p))
        self.assertTrue(phases.end_reason.eq('PAUSE20').any())
        self.assertGreaterEqual(phases.parent.nunique(),2)

    def test_drawdown_reset_and_censored_tail(self):
        # Explicit candidate isolates identity semantics from persistence eligibility.
        p=np.array([100.,110.,120.,109.,110.,115.])
        m=pd.DataFrame(dict(position=[0,4],valid=[True,True],kind=['WARMING','HEATING'],gain20=[.1,.2]))
        phases,_=segment(p,m,'CLASSIFICATION_BOUNDARY')
        self.assertEqual(phases.end_reason.tolist(),['DRAWDOWN8','CLASSIFICATION_BOUNDARY'])
        self.assertEqual(phases.right_censored.tolist(),[False,True])

    def test_missing_cannot_be_treated_as_continuous(self):
        p=path([.0005]*100+[.006]*150); p[110]=np.nan
        m=candidate_metrics(p)
        self.assertFalse(m.position.between(60,170).any())
        with self.assertRaises(ValueError): segment(p,m)


if __name__=='__main__': unittest.main()
