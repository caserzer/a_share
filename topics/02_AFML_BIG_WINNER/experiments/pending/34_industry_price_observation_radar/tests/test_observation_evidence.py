import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from observation_evidence import trailing_evidence,entry_evidence

class EvidenceTests(unittest.TestCase):
    def test_prefix_and_missing(self):
        g=pd.DataFrame({'nav':np.arange(100.,200.),'block':1},index=np.arange(100));m=pd.Series(np.arange(200.,300.),index=g.index)
        full=trailing_evidence(g,m);prefix=trailing_evidence(g.iloc[:70],m.iloc[:70]);pd.testing.assert_frame_equal(full.iloc[:70],prefix)
        g.loc[66,'nav']=np.nan
        self.assertTrue(np.isnan(trailing_evidence(g,m).loc[70,'absolute_return_5']))
        self.assertEqual(entry_evidence(g,m,65,70)[3],'UNKNOWN_PRICE_PATH')
    def test_blocks_market_and_entry(self):
        g=pd.DataFrame({'nav':[100.,110.,121.],'block':[1,1,1]},index=[0,1,2]);m=pd.Series([100.,105.,110.],index=g.index)
        a,b,e,s=entry_evidence(g,m,0,2);self.assertAlmostEqual(a,.21);self.assertAlmostEqual(e,.11)
        g.loc[1,'block']=2;self.assertEqual(entry_evidence(g,m,0,2)[3],'UNKNOWN_PRICE_PATH')
        self.assertEqual(entry_evidence(g,m,None,2)[3],'NO_OBSERVATION_ID')
        with self.assertRaises(ValueError):entry_evidence(g,m,3,2)

if __name__=='__main__':unittest.main()
