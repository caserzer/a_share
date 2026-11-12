import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from matching_contract import Process,Alert
from late_supplement import match_late,neighborhood_known


def proc(pid='p',origin=100):return Process(pid,'E|A',origin,origin+100,origin,origin+60,origin-5,origin+10)


class LateTests(unittest.TestCase):
    def test_primary_ownership_cannot_be_overwritten(self):
        r=match_late([proc()],[Alert('late','E|A',120,True)],{'p':'first_failed'})[0]
        self.assertEqual(r['outcome'],'DUPLICATE');self.assertFalse(r['late_credit'])

    def test_first_unknown_then_success_stays_unknown(self):
        r=match_late([proc()],[Alert('a','E|A',120,None),Alert('b','E|A',130,True)],{})
        self.assertEqual([x['outcome'] for x in r],['UNKNOWN','DUPLICATE'])

    def test_nearest_claimed_not_rerouted(self):
        r=match_late([proc('old',90),proc('near',100)],[Alert('a','E|A',120,True)],{'near':'first'})[0]
        self.assertEqual(r['process_id'],'near');self.assertFalse(r['late_credit'])

    def test_first_failure_not_replaced(self):
        r=match_late([proc()],[Alert('a','E|A',120,False),Alert('b','E|A',130,True)],{})
        self.assertEqual([x['outcome'] for x in r],['FIRST_FAILURE','DUPLICATE'])

    def test_primary_alert_rejected(self):
        with self.assertRaises(ValueError):match_late([proc()],[Alert('primary','E|A',120,True)],{'p':'primary'})

    def test_update_never_adds_credit(self):
        r=match_late([proc()],[Alert('a','E|A',120,True,is_new=False)],{})[0]
        self.assertEqual(r['outcome'],'UPDATE');self.assertFalse(r['denominator'])

    def test_maturity_and_neighborhood_boundaries(self):
        days=np.arange(300);v=np.ones(300);b=np.ones(300)
        self.assertTrue(neighborhood_known(days,v,b,150,215))
        self.assertFalse(neighborhood_known(days,v,b,150,214))
        v[30]=np.nan;self.assertFalse(neighborhood_known(days,v,b,150,215))
        r=match_late([proc()],[Alert('a','E|A',120,None,evaluation_status='IMMATURE')],{})[0]
        self.assertEqual(r['outcome'],'IMMATURE')

    def test_late_window_endpoints_and_unknown_not_success(self):
        for day,expected in [(110,False),(111,True),(160,True),(161,False)]:
            r=match_late([proc()],[Alert('a','E|A',day,True)],{})[0];self.assertEqual(r['late_credit'],expected)
        r=match_late([proc()],[Alert('a','E|A',120,True,False)],{})[0];self.assertEqual(r['outcome'],'UNKNOWN')


if __name__=='__main__':unittest.main()
