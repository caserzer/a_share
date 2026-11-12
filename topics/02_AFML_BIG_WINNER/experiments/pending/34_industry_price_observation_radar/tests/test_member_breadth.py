import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from member_breadth_math import member_arrays,breadth_counts,score_candidates


class BreadthTests(unittest.TestCase):
    def raw(self):
        return pd.DataFrame(dict(date=pd.bdate_range('2020-01-01',periods=70),qfq_close=np.arange(70)+10.,close_conflict=False,factor_chain_id='a'))

    def test_prefix_and_future_mutation(self):
        x=self.raw();full=member_arrays(x,x.date);prefix=member_arrays(x.iloc[:40],x.date.iloc[:40])
        for a,b in zip(full,prefix):np.testing.assert_array_equal(a[:40],b)
        x.loc[40:,'qfq_close']=-1
        for a,b in zip(full,member_arrays(x,x.date)):np.testing.assert_array_equal(a[:40],b[:40])

    def test_missing_chain_conflict_and_equal_return(self):
        for kind in ['missing','chain','conflict']:
            x=self.raw();calendar=x.date.copy()
            if kind=='missing':x=x.drop(index=30)
            elif kind=='chain':x.loc[30:,'factor_chain_id']='b'
            else:x.loc[30,'close_conflict']=True
            supported,_=member_arrays(x,calendar);self.assertFalse(supported[30:50].any())
        x=self.raw();x.qfq_close=10.;supported,up=member_arrays(x,x.date)
        self.assertTrue(supported[20:].all());self.assertFalse(up.any())

    def test_unknown_bounds_and_support(self):
        r=breadth_counts(10,8,6);self.assertEqual(r['breadth'],.75)
        self.assertEqual(r['breadth_lower'],.6);self.assertEqual(r['breadth_upper'],.8);self.assertTrue(r['supported'])
        self.assertFalse(breadth_counts(10,7,6)['supported']);self.assertIsNone(breadth_counts(10,0,0)['breadth'])

    def test_rank_ties_and_no_breadth_ablation(self):
        f=pd.DataFrame(dict(r20=[1.,1.,3.],breadth=[.8,.2,.5]))
        x=score_candidates(f);np.testing.assert_allclose(x.score_A,[.5,.5,1.])
        np.testing.assert_allclose(score_candidates(f,weight=0).score_B,x.score_A)

    def test_future_column_rejected(self):
        x=self.raw();x['future_return']=1
        with self.assertRaises(ValueError):member_arrays(x,x.date)


if __name__=='__main__':unittest.main()
