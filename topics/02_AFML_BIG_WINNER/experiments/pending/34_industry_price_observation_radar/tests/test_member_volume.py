import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from member_volume_math import volume_ratio,score_candidates

class VolumeTests(unittest.TestCase):
    def test_support_zero_and_prefix(self):
        c=pd.date_range('2020-01-01',periods=100)
        x=pd.DataFrame({'date':c,'volume':np.r_[np.ones(63)*10,np.ones(37)*20],'volume_conflict':False})
        v=volume_ratio(x,c);self.assertEqual(v[83],2.)
        np.testing.assert_allclose(v[:90],volume_ratio(x.iloc[:90],c[:90]),equal_nan=True)
        x.loc[63:83,'volume']=0;self.assertEqual(volume_ratio(x,c)[83],0.)
        x.loc[0:62,'volume']=0;self.assertTrue(np.isnan(volume_ratio(x,c)[83]))
        x.loc[:,'volume']=10;x.loc[40,'volume_conflict']=True
        self.assertTrue(np.isnan(volume_ratio(x,c)[83]))
        self.assertTrue(np.isnan(volume_ratio(x.drop(40),c)[83]))
    def test_rank_ties(self):
        x=score_candidates(pd.DataFrame({'r20':[1,1,3],'volume_ratio':[3,2,0]}))
        self.assertEqual(x.score_A.iloc[0],.5)
        self.assertEqual(x.score_B.iloc[0],.75)

if __name__=='__main__':unittest.main()
