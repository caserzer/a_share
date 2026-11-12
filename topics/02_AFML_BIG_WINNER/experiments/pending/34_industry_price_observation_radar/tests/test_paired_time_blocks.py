import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from paired_time_blocks import paired_interval
from metric_accounting import time_block_interval


class PairedTests(unittest.TestCase):
    def test_identical_arms_zero_difference_and_same_marginal(self):
        x=np.array([[i%3,4,i%2,3] for i in range(31)])
        result=paired_interval([np.column_stack([x,x])],repetitions=200)
        self.assertEqual(result['B_minus_A_precision']['interval'],[0.,0.])
        self.assertEqual(result['B_minus_A_recall']['interval'],[0.,0.])
        self.assertEqual(result['A_precision'],time_block_interval([x],repetitions=200)['precision'])

    def test_undefined_is_not_zero_precision(self):
        result=paired_interval([np.zeros((20,8))],repetitions=30)
        self.assertIsNone(result['B_minus_A_precision']['interval'])
        self.assertEqual(result['B_minus_A_recall']['undefined_replicates'],30)

    def test_known_constant_difference(self):
        result=paired_interval([np.tile([1,10,1,10,3,10,3,10],(30,1))],repetitions=30)
        np.testing.assert_allclose(result['B_minus_A_recall']['interval'],[.2,.2])


if __name__=='__main__':unittest.main()
