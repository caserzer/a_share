import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from r01_delay_pool import DelayedPool

C=dict(version='test',weekly_new_cap=1,pool_cap=2,max_age_sessions=60,cooldown_sessions=20,missing_reviews_to_exit=2)


class DelayTests(unittest.TestCase):
    def daily(self,bad=None):
        x=pd.DataFrame(dict(day_i=range(31),eligible=True,score=.1))
        if bad is not None:x.loc[bad,'score']=-.1
        return {'A':x}

    def step(self,p,day,d):
        return p.step('E',pd.Timestamp('2020-01-03')+pd.Timedelta(days=day*7//5),day,[dict(industry_code='A',eligible=True,score=.1)],d)

    def test_wait_and_enter(self):
        p=DelayedPool(C,10);d=self.daily()
        self.assertFalse(self.step(p,0,d)[1]);self.assertFalse(self.step(p,5,d)[1])
        e=self.step(p,10,d)[1][0];self.assertEqual(e['confirmation_wait'],10)

    def test_negative_between_reviews_resets(self):
        p=DelayedPool(C,5);d=self.daily(3)
        self.step(p,0,d);self.assertFalse(self.step(p,5,d)[1]);self.assertEqual(p.pending['A'],5)
        self.assertEqual(self.step(p,10,d)[1][0]['candidate_day'],5)

    def test_missing_day_resets(self):
        p=DelayedPool(C,5);d=self.daily();d['A']=d['A'].drop(index=3)
        self.step(p,0,d);self.assertFalse(self.step(p,5,d)[1]);self.assertEqual(p.pending['A'],5)

    def test_unknown_resets(self):
        p=DelayedPool(C,5);d=self.daily();d['A'].loc[3,'eligible']=False
        self.step(p,0,d);self.assertFalse(self.step(p,5,d)[1])

    def test_future_rows_do_not_change_events(self):
        a=DelayedPool(C,5);b=DelayedPool(C,5);d=self.daily();changed=self.daily(20)
        for day in [0,5,10]:self.assertEqual(self.step(a,day,d),self.step(b,day,changed))

    def test_cooling_does_not_start_queue(self):
        p=DelayedPool(C,5);p.pool.era='E';p.era='E';p.pool.exits['A']=0
        self.assertFalse(self.step(p,5,self.daily())[1]);self.assertEqual(p.pending,{})


if __name__=='__main__':unittest.main()
