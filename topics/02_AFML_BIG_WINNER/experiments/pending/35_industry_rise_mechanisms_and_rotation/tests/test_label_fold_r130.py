import unittest
import pandas as pd
import numpy as np
from build_panel import price_features,delayed_labels
from label_fold_audit_r130 import gate

class RepairLabelBoundaryTests(unittest.TestCase):
    def test_future_label_cannot_cross_reset(self):
        days=pd.bdate_range('2026-01-01',periods=100);market=pd.Series(100.,index=days)
        d=pd.DataFrame({'date':days,'nav':np.r_[np.linspace(1,1.5,50),np.linspace(1,1.3,50)],'block':[1]*50+[2]*50})
        repaired=pd.concat([delayed_labels(price_features(g),market) for _,g in d.groupby('block')]).sort_index()
        joined=delayed_labels(price_features(d),market)
        self.assertTrue(pd.isna(repaired.loc[40,'return20']))
        self.assertTrue(pd.notna(joined.loc[40,'return20']))
        self.assertTrue(pd.isna(repaired.loc[40,'maturity20']))
    def test_boundary_maturity_is_excluded(self):
        q=pd.DataFrame({'date':pd.to_datetime(['2025-01-31','2025-02-28','2026-01-31']),'maturity20':pd.to_datetime(['2025-12-31','2026-01-01',None]),'y':[.1,.2,np.nan]})
        rec,(fit,cal,test)=gate(q,2026,20,'return')
        self.assertEqual(len(fit),1);self.assertEqual(fit.y.iloc[0],.1);self.assertEqual(len(test),1)
        self.assertEqual(rec['reason'],'insufficient_train_months_or_rows')
