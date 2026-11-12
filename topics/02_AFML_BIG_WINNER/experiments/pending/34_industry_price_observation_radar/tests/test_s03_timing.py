import sys
from pathlib import Path
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from s03_timing_accounting import milestone

class TimingTests(unittest.TestCase):
    def test_first_hit_and_unknown_before_hit(self):
        g=pd.DataFrame({'nav':[100.,103.,109.,110.],'block':[1,1,1,1]},index=[0,1,2,3])
        rules={'post_alert_peak_horizon':3,'post_alert_peak_min_return':.08}
        self.assertEqual(milestone(g,0,3,None,rules)[:2],(2,'REACHED'))
        self.assertEqual(milestone(g.drop(1),0,3,None,rules)[:2],(None,'UNKNOWN_PATH'))
        self.assertEqual(milestone(g,0,3,1,rules)[:2],(None,'PROCESS_ENDED'))
        self.assertEqual(milestone(g,0,3,1,rules,False)[:2],(None,'UNKNOWN_PROCESS_CENSORED'))
        self.assertEqual(milestone(g,0,1,None,rules)[:2],(None,'ASOF_INCOMPLETE'))
        g['block']=[1,2,2,2]
        self.assertEqual(milestone(g,0,3,None,rules)[:2],(None,'UNKNOWN_PATH'))

if __name__=='__main__':unittest.main()
