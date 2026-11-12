import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from endpoint_contract import assess


class EvidenceOwnership(unittest.TestCase):
    def test_post_end_rally_cannot_rescue_interruption(self):
        p=np.r_[np.linspace(100,109,16),np.linspace(109,90,6),np.repeat(180.,90)]
        first=assess(p,21,'DRAWDOWN8')
        p[22:]=10000
        self.assertEqual(first,assess(p,21,'DRAWDOWN8'))
        self.assertEqual(first['status'],'OBSERVED_END_BEFORE_CONFIRMATION')

    def test_post_confirmation_crash_cannot_rewrite_window(self):
        p=np.r_[np.linspace(100,130,61),np.repeat(1.,40)]
        a=assess(p,100,'DRAWDOWN8')
        p[61:]=10000
        self.assertEqual(a,assess(p,100,'DRAWDOWN8'))
        self.assertEqual(a['status'],'WITHIN_PHASE_CONFIRMED')

    def test_stage_switch_is_not_price_failure(self):
        a=assess(np.linspace(100,140,101),30,'NEW_HEATING_PHASE')
        self.assertEqual(a['status'],'SUPERSEDED_BEFORE_CONFIRMATION')

    def test_censor_is_unknown(self):
        for reason in ['RIGHT_CENSORED','CLASSIFICATION_BOUNDARY','INTERNAL_PRICE_BREAK']:
            self.assertEqual(assess(np.linspace(100,120,30),29,reason)['status'],'UNKNOWN_CENSORED')

    def test_left_origin_flag_survives_confirmation(self):
        a=assess(np.linspace(100,130,61),60,'RIGHT_CENSORED',True)
        self.assertTrue(a['left_origin_uncertain'])
        self.assertEqual(a['status'],'WITHIN_PHASE_CONFIRMED')

    def test_missing_inside_window_is_unknown(self):
        p=np.linspace(100,130,61);p[30]=np.nan
        self.assertEqual(assess(p,60,'RIGHT_CENSORED')['status'],'UNKNOWN_CENSORED')


if __name__=='__main__':unittest.main()
