import unittest
import pandas as pd
import numpy as np
from basket_repair_r129 import select_rows

class DeterministicRowsTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([
            dict(date='2026-09-29',known_at='2026-09-29',day_i=0,nav=1.2,coverage=1.,source_kind='observed'),
            dict(date='2026-09-30',known_at='2026-09-30',day_i=1,nav=np.nan,coverage=.5,source_kind='observed'),
            dict(date='2026-09-30',known_at='2026-10-09',day_i=1,nav=1.,coverage=np.nan,source_kind='anchor'),
            dict(date='2026-10-09',known_at='2026-10-09',day_i=2,nav=1.1,coverage=1.,source_kind='observed')]).assign(date=lambda f:pd.to_datetime(f.date),known_at=lambda f:pd.to_datetime(f.known_at))
    def test_priority_and_known_time(self):
        f=self.fixture();sep=select_rows(f,'2026-09-30');octo=select_rows(f,'2026-10-09')
        self.assertEqual(len(sep),1);self.assertEqual(len(octo),3)
        self.assertEqual(octo.iloc[1].source_kind,'anchor')
        self.assertNotEqual(octo.iloc[0].block,octo.iloc[1].block)
        self.assertEqual(octo.iloc[1].block,octo.iloc[2].block)
        f.loc[1,'nav']=1.3;self.assertEqual(select_rows(f,'2026-10-09').iloc[1].source_kind,'observed')
    def test_order_invariance_and_duplicate_rejection(self):
        f=self.fixture();a=select_rows(f,'2026-10-09').reset_index(drop=True)
        b=select_rows(f.iloc[::-1],'2026-10-09').reset_index(drop=True);pd.testing.assert_frame_equal(a,b)
        with self.assertRaises(ValueError):select_rows(pd.concat([f,f.iloc[:1]]),'2026-10-09')
    def test_block_identity_survives_earlier_isolated_insert(self):
        f=self.fixture().iloc[-1:].copy();f['day_i']=10
        a=select_rows(f,'2026-10-09');earlier=self.fixture().iloc[:1].copy()
        b=select_rows(pd.concat([earlier,f]),'2026-10-09')
        self.assertEqual(a.iloc[0].block,b.iloc[-1].block)
