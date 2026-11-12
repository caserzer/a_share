import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post_alert_evaluation import post_alert_result,label_neighborhood_known,process_recall_mature
from matching_contract import Process,Alert,match_draft


class PostAlertEvidence(unittest.TestCase):
    def setUp(self):
        self.days=np.arange(220);self.prices=np.linspace(100,210,220);self.blocks=np.ones(220)

    def evaluate(self,**kwargs):
        return post_alert_result(self.days,self.prices,self.blocks,100,165,**kwargs)

    def test_past_gain_cannot_make_flat_future_successful(self):
        self.prices[:100]=np.linspace(1,100,100);self.prices[100:]=100
        self.assertFalse(self.evaluate()['post_valid'])

    def test_pre_alert_and_beyond_window_mutations_irrelevant(self):
        first=self.evaluate();self.prices[:100]=1e9;self.prices[161:]=1e-9
        self.assertEqual(first,self.evaluate())

    def test_uniform_maturity_exact_boundary(self):
        self.assertEqual(post_alert_result(self.days,self.prices,self.blocks,100,164)['status'],'IMMATURE')
        self.assertNotEqual(self.evaluate()['status'],'IMMATURE')
        self.assertFalse(process_recall_mature(100,174));self.assertTrue(process_recall_mature(100,175))

    def test_known_end_is_failure_censored_end_unknown(self):
        self.assertEqual(self.evaluate(process_end=150,process_end_observed=True)['status'],'PROCESS_ENDED')
        self.assertEqual(self.evaluate(process_end=150,process_end_observed=False)['status'],'UNKNOWN_PROCESS_CENSORED')

    def test_missing_after_witnessed_breach_does_not_erase_failure(self):
        self.prices[152:]=np.nan
        self.assertFalse(self.evaluate(process_end=150,process_end_observed=True)['post_valid'])
        self.prices[150]=np.nan
        self.assertIsNone(self.evaluate(process_end=150,process_end_observed=True)['post_valid'])

    def test_internal_gap_or_chain_break_unknown(self):
        self.prices[130]=np.nan;self.assertIsNone(self.evaluate()['post_valid'])
        self.prices[130]=150;self.blocks[130:]=2;self.assertIsNone(self.evaluate()['post_valid'])

    def test_unmatched_neighborhood_requires_full_candidate_support(self):
        self.assertTrue(label_neighborhood_known(self.days,self.prices,self.blocks,100,165))
        self.prices[35]=np.nan
        self.assertFalse(label_neighborhood_known(self.days,self.prices,self.blocks,100,165))
        self.assertIsNotNone(self.evaluate()['post_valid'])

    def test_missing_trading_row_is_not_shorter_window(self):
        keep=self.days!=130
        result=post_alert_result(self.days[keep],self.prices[keep],self.blocks[keep],100,165)
        self.assertIsNone(result['post_valid'])

    def test_evaluator_integrates_without_hiding_immature_or_duplicates(self):
        self.prices=100*np.exp(.005*self.days)
        p=Process('p','industry',100,200,100,160,95,110)
        early=post_alert_result(self.days,self.prices,self.blocks,100,164)
        a=Alert('first','industry',100,early['post_valid'],evaluation_status=early['status'])
        self.assertEqual(match_draft([p],[a])[0]['outcome'],'IMMATURE')
        ready=self.evaluate(process_end=200,process_end_observed=True)
        known=label_neighborhood_known(self.days,self.prices,self.blocks,100,165)
        first=Alert('first','industry',100,ready['post_valid'],known,evaluation_status=ready['status'])
        later=Alert('second','industry',101,True)
        results=match_draft([p],[first,later])
        self.assertEqual([r['outcome'] for r in results],['SUCCESS','DUPLICATE'])
        self.assertEqual(sum(r['recall_credit'] for r in results),1)


if __name__=='__main__':unittest.main()
