import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from r02_features import change_features
from r02_candidates import CommonCandidates,select


class PriceChangeTests(unittest.TestCase):
    def raw(self):
        return pd.DataFrame(dict(era='E',industry_code='A',date=pd.bdate_range('2020-01-01',periods=150),day_i=np.arange(150),nav=np.exp(np.arange(150)**2*.00001),block=1,status='OBSERVED',stale_members=0,boundary_proxy=False))

    def test_prefix_and_future_changes(self):
        x=self.raw();full=change_features(x)
        pd.testing.assert_frame_equal(change_features(x.iloc[:100]),full.iloc[:100])
        x.loc[100:,'nav']=1e9
        pd.testing.assert_frame_equal(change_features(x).iloc[:100],full.iloc[:100])

    def test_adjacent_intervals_and_missing(self):
        x=self.raw();f=change_features(x);i=90
        expected=x.nav[i]/x.nav[i-20]-x.nav[i-20]/x.nav[i-40]
        self.assertAlmostEqual(f.delta20[i],expected)
        x=x.drop(index=80);f=change_features(x)
        self.assertTrue(f.loc[f.day_i.between(81,140),'delta20'].isna().all())

    def test_future_schema_rejected(self):
        x=self.raw();x['future_success']=True
        with self.assertRaises(ValueError):change_features(x)

    def step(self,c,day,positive=True,known=True):
        row=dict(industry_code='A',eligible=known,r5=.01 if positive else -.01,r20=-.05,delta20=.02)
        return c.step('E',pd.Timestamp('2020-01-01')+pd.Timedelta(days=day),day,[row])[0]

    def test_segment_cooldown_and_no_deferred_ticket(self):
        c=CommonCandidates();self.assertIsNotNone(self.step(c,0)['ticket_id'])
        self.assertIsNone(self.step(c,5)['ticket_id']);self.step(c,10,False)
        self.assertEqual(self.step(c,15)['reason'],'COMMON_TICKET_COOLDOWN')
        self.assertEqual(self.step(c,25)['reason'],'SAME_POSITIVE_SEGMENT')
        self.step(c,30,False);self.assertIsNotNone(self.step(c,35)['ticket_id'])

    def test_unknown_not_nonpositive(self):
        c=CommonCandidates();self.assertEqual(self.step(c,0,known=False)['reason'],'DATA_UNKNOWN')
        row=self.step(c,5);self.assertTrue(row['previous_feedback_unknown']);self.assertIsNotNone(row['ticket_id'])

    def test_same_quantity_different_rank_and_empty(self):
        rows=[dict(ticket_id=str(i),industry_code=str(i),r20=float(i),delta20=-float(i)) for i in range(8)]
        a=select(rows,'r20');b=select(rows,'delta20')
        self.assertEqual(len(a),len(b));self.assertEqual(len(a),5)
        self.assertNotEqual(a[0]['industry_code'],b[0]['industry_code'])
        self.assertEqual(select([],'r20'),[])


if __name__=='__main__':unittest.main()
