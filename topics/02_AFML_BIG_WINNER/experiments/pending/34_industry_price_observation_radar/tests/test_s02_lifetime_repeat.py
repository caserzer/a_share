import sys
from pathlib import Path
import unittest
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from s02_lifetime_repeat import associate

class LifetimeTests(unittest.TestCase):
    def test_overlap_boundary_unknown_and_classification(self):
        p=pd.DataFrame([
            dict(era='A',industry_code='x',process_id='p',family_id='f',start_day_i=10,end_day_i=100,left_origin_uncertain=False,right_censored=False),
            dict(era='A',industry_code='x',process_id='q',family_id='f',start_day_i=80,end_day_i=120,left_origin_uncertain=False,right_censored=True),
            dict(era='B',industry_code='x',process_id='u',family_id='g',start_day_i=10,end_day_i=100,left_origin_uncertain=True,right_censored=False)])
        n=pd.DataFrame([dict(alert_id=i,day=d,era=e,industry_code='x') for i,d,e in [('pre',9,'A'),('first',10,'A'),('overlap',80,'A'),('end',100,'A'),('after',121,'A'),('u1',20,'B'),('u2',90,'B')]])
        a,l=associate(n,p);a=a.set_index('alert_id')
        self.assertEqual(a.loc['pre','associations'],0)
        self.assertEqual(a.loc['after','associations'],0)
        self.assertFalse(a.loc['first','known_repeat'])
        self.assertTrue(a.loc['overlap','mixed_first_repeat'])
        self.assertTrue(a.loc['overlap','beyond60_known_repeat'])
        self.assertEqual(a.loc['end','associations'],2)
        self.assertFalse(a.loc['u1','unknown_only_repeat'])
        self.assertTrue(a.loc['u2','unknown_only_repeat'])
        self.assertFalse(a.loc['u2','known_repeat'])
        self.assertEqual(l.loc[l.alert_id.eq('u2'),'previous_ids'].iloc[0],['u1'])
        self.assertEqual(l.loc[l.alert_id.eq('overlap')&l.process_id.eq('p'),'previous_alert_id'].iloc[0],'first')
        self.assertTrue(a.loc['overlap','family_repeat'])

if __name__=='__main__':unittest.main()
