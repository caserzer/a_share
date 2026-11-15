import unittest
import pandas as pd
import numpy as np
from basket_replay_r128 import rebuild

class ClassificationCutoffTests(unittest.TestCase):
    def test_transition_anchor_requires_following_month(self):
        days=pd.bdate_range('2021-10-01','2022-02-10')
        stocks={str(i):pd.DataFrame({'date':days,'qfq_close':np.arange(len(days))+10.,'close_conflict':False,'factor_chain_id':'a'}) for i in range(5)}
        rows=[]
        for era,mo in [('SW2014','2021-10'),('SW2014','2021-11'),('SW2021','2021-12'),('SW2021','2022-01')]:
            for sid in stocks:rows.append(dict(era=era,level='L2',industry_code='same',month=pd.Period(mo),security_id=sid,unresolved=0))
        m=pd.DataFrame(rows)
        dec=rebuild(m,stocks,days,'2021-12-31');jan=rebuild(m,stocks,days,'2022-01-31')
        self.assertEqual(set(dec.era),{'SW2014'})
        self.assertEqual(dec.date.max(),pd.Timestamp('2021-11-30'))
        new=jan[jan.era.eq('SW2021')]
        self.assertEqual(new.date.min(),pd.Timestamp('2021-12-31'))
        self.assertEqual(new.iloc[0].nav,1)
        self.assertTrue(pd.isna(new.iloc[0].coverage))
        # Future membership cannot leak into the December rebuild.
        changed=m.copy();changed.loc[changed.month.ge(pd.Period('2021-12')),'unresolved']=100
        pd.testing.assert_frame_equal(dec,rebuild(changed,stocks,days,'2021-12-31'))
    def test_unresolved_denominator_excludes_low_coverage(self):
        days=pd.bdate_range('2022-01-01','2022-02-10')
        stocks={str(i):pd.DataFrame({'date':days,'qfq_close':10.,'close_conflict':False,'factor_chain_id':'a'}) for i in range(5)}
        m=pd.DataFrame([dict(era='SW2021',level='L3',industry_code='x',month=pd.Period('2022-01'),security_id=s,unresolved=2) for s in stocks])
        f=rebuild(m,stocks,days,'2022-02-10')
        self.assertEqual(len(f),1) # only synthetic origin; not an observed return
        self.assertTrue(pd.isna(f.iloc[0].coverage))
