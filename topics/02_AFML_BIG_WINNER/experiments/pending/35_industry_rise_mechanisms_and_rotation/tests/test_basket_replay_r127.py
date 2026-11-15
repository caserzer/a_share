import unittest
import numpy as np
import pandas as pd
from basket_replay_r127 import append_verified,matrices

class BasketReplayTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'era':['SW2021']*2,'level':['L1']*2,'industry_code':['x']*2,'date':pd.to_datetime(['2026-09-29','2026-09-30']),'nav':[1.,1.1]})
    def test_revision_and_insertion_rejected(self):
        f=self.frame();changed=f.copy();changed.loc[0,'nav']=2
        with self.assertRaises(ValueError):append_verified(f,changed)
        inserted=f.iloc[:1].copy();inserted['industry_code']='y'
        with self.assertRaises(ValueError):append_verified(f,inserted)
        pd.testing.assert_frame_equal(append_verified(f,f),f)
        future=f.iloc[-1:].copy();future['date']=pd.Timestamp('2026-10-09')
        self.assertEqual(len(append_verified(f,future)),3)
    def test_future_chain_and_conflicts(self):
        days=pd.bdate_range('2026-01-01',periods=100)
        f=pd.DataFrame({'date':days,'qfq_close':np.arange(100)+10.,'close_conflict':False,'factor_chain_id':'a'})
        _,a,b=matrices({'s':f},days[:70]);changed=f.copy();changed.loc[70:,'qfq_close']=1e9
        _,c,d=matrices({'s':changed},days)
        np.testing.assert_array_equal(a,c[:70]);np.testing.assert_array_equal(b[63],d[63][:70])
        changed.loc[69,'close_conflict']=True
        _,c,d=matrices({'s':changed},days[:70]);self.assertTrue(np.isnan(c[69,0]));self.assertTrue(np.isnan(d[21][69,0]))
        changed.loc[69,'close_conflict']=False;changed.loc[69,'factor_chain_id']='new'
        _,c,d=matrices({'s':changed},days[:70]);self.assertTrue(np.isnan(c[69,0]));self.assertTrue(np.isnan(d[21][69,0]))
