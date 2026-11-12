import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from metric_accounting import summarize,time_block_interval


def process(pid,family,mature=True,left=False):
    return dict(process_id=pid,family_id=family,mature=mature,left_origin_uncertain=left)


def result(aid,state,pid=None):
    return dict(alert_id=aid,outcome=state,process_id=pid,recall_credit=state=='SUCCESS',
                new_observation_denominator=state in {'SUCCESS','FIRST_FAILURE','UNMATCHED_FAILURE','DUPLICATE'})


class Accounting(unittest.TestCase):
    def test_complete_hand_calculated_denominators(self):
        p=[process('p1','A'),process('p2','A'),process('p3','B'),process('p4','C',left=True),process('p5','D',False),process('p6','E')]
        r=[result('a','SUCCESS','p1'),result('b','SUCCESS','p2'),result('c','DUPLICATE','p1'),
           result('d','UNMATCHED_FAILURE'),result('e','UNKNOWN','p3'),result('f','UNKNOWN','p4'),
           result('g','IMMATURE','p5'),result('update','UPDATE','p1')]
        s=summarize(p,r)
        self.assertEqual((s['precision_numerator'],s['precision_denominator']),(2,4))
        self.assertEqual((s['unique_new_alerts'],s['unknown_alerts'],s['immature_alerts'],s['updates']),(7,2,1,1))
        self.assertEqual(s['precision_unknown_bounds'],[2/6,4/6])
        self.assertEqual((s['mature_known_processes'],s['mature_left_unknown'],s['immature_processes']),(4,1,1))
        self.assertEqual((s['recall_lower'],s['recall_upper'],s['known_not_recalled']),(.5,.75,1))
        self.assertEqual((s['family_denominator'],s['family_numerator']),(3,1))
        self.assertEqual(s['family_recall_upper'],2/3)

    def test_empty_alerts_do_not_delete_ground_truth(self):
        s=summarize([process('p','f')],[])
        self.assertIsNone(s['precision']);self.assertEqual(s['recall_lower'],0)
        self.assertEqual(s['known_not_recalled'],1)

    def test_all_unknown_is_not_zero_precision(self):
        s=summarize([process('p','f')],[result('a','UNKNOWN','p')])
        self.assertIsNone(s['precision']);self.assertEqual(s['precision_unknown_bounds'],[0,1])
        self.assertEqual(s['recall_upper'],1);self.assertEqual(s['known_not_recalled'],0)

    def test_later_unknown_duplicate_cannot_rewrite_first_failure(self):
        s=summarize([process('p','f')],[result('a','FIRST_FAILURE','p'),result('b','UNKNOWN_DUPLICATE','p')])
        self.assertEqual(s['unresolved_processes'],0);self.assertEqual(s['recall_upper'],0)

    def test_input_errors_fail_loudly(self):
        with self.assertRaises(ValueError):summarize([process('p','f')],[result('a','SUCCESS','missing')])
        with self.assertRaises(ValueError):summarize([process('p','f')],[result('a','SUCCESS','p'),result('b','SUCCESS','p')])
        with self.assertRaises(ValueError):summarize([process('p','f',left=True)],[result('a','SUCCESS','p')])
        bad=result('a','UNKNOWN');bad['new_observation_denominator']=True
        with self.assertRaises(ValueError):summarize([], [bad])

    def test_success_can_be_precision_mature_before_recall_mature(self):
        s=summarize([process('p','f',False)],[result('a','SUCCESS','p')])
        self.assertEqual(s['precision'],1);self.assertIsNone(s['recall_lower'])


class TimeBlocks(unittest.TestCase):
    def test_constant_ratio_remains_constant(self):
        a=np.tile([1,2,2,4],(40,1));b=np.tile([2,4,3,6],(20,1))
        r=time_block_interval([a,b],repetitions=200)
        self.assertEqual(r['precision']['interval'],[.5,.5]);self.assertEqual(r['recall']['interval'],[.5,.5])

    def test_zero_denominator_not_artificial_zero(self):
        r=time_block_interval([np.zeros((30,4))],repetitions=50)
        self.assertIsNone(r['precision']['interval']);self.assertEqual(r['recall']['undefined_replicates'],50)

    def test_seed_reproducibility_and_ordered_finite_bounds(self):
        a=np.array([[i%2,1,i%3,3] for i in range(90)])
        r=time_block_interval([a],repetitions=200)
        self.assertEqual(r,time_block_interval([a],repetitions=200))
        for v in r.values():self.assertTrue(0<=v['interval'][0]<=v['interval'][1]<=1)

    def test_invalid_counts_rejected(self):
        with self.assertRaises(ValueError):time_block_interval([[[2,1,0,1]]])


if __name__=='__main__':unittest.main()
