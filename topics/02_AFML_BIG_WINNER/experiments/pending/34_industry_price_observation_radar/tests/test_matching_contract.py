import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from matching_contract import Process,Alert,match_draft


def process(pid='p',origin=10,**kw):
    return Process(pid,'SW2021|industry',origin,origin+60,origin,origin+60,origin-5,origin+10,**kw)


def alert(aid='a',day=10,valid=True,**kw):
    return Alert(aid,'SW2021|industry',day,valid,**kw)


class MatchingContract(unittest.TestCase):
    def test_first_failure_not_replaced_by_later_success(self):
        r=match_draft([process()],[alert('first',10,False),alert('later',11,True)])
        self.assertEqual([x['outcome'] for x in r],['FIRST_FAILURE','DUPLICATE'])
        self.assertEqual(sum(x['recall_credit'] for x in r),0)
        self.assertEqual(sum(x['new_observation_denominator'] for x in r),2)

    def test_repeat_updates_not_new_successes(self):
        r=match_draft([process()],[alert(),alert('update',11,True,is_new=False),alert('new_again',12)])
        self.assertEqual([x['outcome'] for x in r],['SUCCESS','UPDATE','DUPLICATE'])
        self.assertEqual(sum(x['recall_credit'] for x in r),1)

    def test_unknown_not_unmatched_failure(self):
        self.assertEqual(match_draft([], [alert(label_coverage_known=False)])[0]['outcome'],'UNKNOWN')
        self.assertEqual(match_draft([process()], [alert(valid=None)])[0]['outcome'],'UNKNOWN')

    def test_immature_is_separate_and_not_in_accuracy_denominator(self):
        r=match_draft([process()],[alert(valid=None,evaluation_status='IMMATURE')])[0]
        self.assertEqual(r['outcome'],'IMMATURE')
        self.assertFalse(r['new_observation_denominator'])

    def test_late_not_timely(self):
        r=match_draft([process()],[alert(day=21)])
        self.assertEqual(r[0]['outcome'],'UNMATCHED_FAILURE')

    def test_overlap_does_not_reassign_occupied_nearest_process(self):
        r=match_draft([process('early',10),process('later',15)],[alert('a',10),alert('b',11)])
        self.assertEqual([x['process_id'] for x in r],['early','early'])
        self.assertEqual(r[1]['outcome'],'DUPLICATE')

    def test_identity_and_interval_errors_rejected(self):
        with self.assertRaises(ValueError):match_draft([process(),process()],[])
        with self.assertRaises(ValueError):match_draft([process()],[alert(),alert()])
        bad=Process('p','i',10,20,10,70,5,20)
        with self.assertRaises(ValueError):match_draft([bad],[])

    def test_left_origin_not_claimed_early_success(self):
        self.assertEqual(match_draft([process(left_origin_uncertain=True)],[alert()])[0]['outcome'],'UNKNOWN')

    def test_order_deterministic_and_single_assignment(self):
        a=[alert('b',10),alert('a',10)]
        r=match_draft([process()],a)
        self.assertEqual(r,match_draft([process()],list(reversed(a))))
        self.assertEqual(sum(x['recall_credit'] for x in r),1)


if __name__=='__main__':unittest.main()
