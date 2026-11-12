import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from r01_features import features,complete_week_reviews
from r01_pool import ObservationPool


class HistoricalFeatures(unittest.TestCase):
    def frame(self):
        return pd.DataFrame(dict(era='E',industry_code='A',date=pd.bdate_range('2020-01-01',periods=150),
                                 day_i=np.arange(150),nav=np.exp(np.arange(150)*.003),block=1,status='OBSERVED',stale_members=0,boundary_proxy=False))

    def test_prefix_and_future_mutation(self):
        f=self.frame();whole=features(f)
        for cutoff in [61,80,110]:
            pd.testing.assert_frame_equal(features(f.iloc[:cutoff]),whole.iloc[:cutoff].reset_index(drop=True))
        f.loc[100:,'nav']=1e10
        pd.testing.assert_frame_equal(features(f).iloc[:100],whole.iloc[:100])

    def test_missing_date_and_chain_break_reset_history(self):
        f=self.frame().drop(index=80);g=features(f)
        self.assertFalse(g.loc[g.day_i.between(81,140),'eligible'].any())
        f=self.frame();f.loc[80:,'block']=2
        self.assertFalse(features(f).loc[80:139,'eligible'].any())

    def test_future_field_rejected(self):
        f=self.frame();f['future_return']=1
        with self.assertRaises(ValueError):features(f)

    def test_partial_final_week_excluded(self):
        dates=pd.bdate_range('2026-10-05','2026-10-21')
        self.assertEqual(complete_week_reviews(dates,'2026-10-21')[-1],pd.Timestamp('2026-10-16'))


class PoolRules(unittest.TestCase):
    def setUp(self):
        self.config=dict(version='test',weekly_new_cap=2,pool_cap=3,max_age_sessions=60,cooldown_sessions=20,missing_reviews_to_exit=2)
        self.pool=ObservationPool(self.config)

    def step(self,n,known=True,score=.1):
        return self.pool.step('E',pd.Timestamp('2020-01-03')+pd.Timedelta(weeks=n),n*5,
                              [dict(industry_code=c,eligible=known,score=score if known else np.nan) for c in ['A','B','C','D']])

    def test_weekly_and_pool_caps_and_no_rank_reentry(self):
        s,e=self.step(0);self.assertEqual([x['industry_code'] for x in e if x['event']=='NEW'],['A','B'])
        s,e=self.step(1);self.assertEqual(sum(x['event']=='NEW' for x in e),1)
        s,e=self.step(2);self.assertEqual(sum(x['event']=='NEW' for x in e),0)
        self.assertEqual(len(self.pool.active),3)

    def test_empty_pool_when_no_positive_candidates(self):
        s,e=self.step(0,score=0);self.assertEqual(len(self.pool.active),0);self.assertEqual(len(s),4)

    def test_unknown_suspension_and_second_unknown_exit(self):
        self.step(0);s,e=self.step(1,known=False)
        self.assertTrue(s['A']['in_pool']);self.assertEqual(s['A']['state'],'DATA_INSUFFICIENT')
        s,e=self.step(2,known=False)
        self.assertEqual(s['A']['reason'],'REPEATED_DATA_UNKNOWN');self.assertFalse(s['A']['in_pool'])

    def test_cooldown_and_new_identity(self):
        self.step(0);oid=self.pool.active['A']['observation_id'];self.step(1,score=-.1)
        self.step(2);self.assertNotIn('A',self.pool.active)
        self.step(5);self.assertIn('A',self.pool.active);self.assertNotEqual(self.pool.active['A']['observation_id'],oid)

    def test_classification_boundary_closes_all(self):
        self.step(0);e=self.pool.close_era(pd.Timestamp('2020-01-07'),2)
        self.assertEqual(len(e),2);self.assertFalse(self.pool.active)
        self.assertTrue(all(x['reason']=='CLASSIFICATION_BOUNDARY' for x in e))

    def test_age_exit_does_not_replace_with_same_industry(self):
        self.step(0)
        for n in range(1,13):s,e=self.step(n)
        self.assertEqual(s['A']['reason'],'MAX_OBSERVATION_AGE');self.assertNotIn('A',self.pool.active)


if __name__=='__main__':unittest.main()
