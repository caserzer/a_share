import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from eps_coverage_r28 import monthly_fast,common_pairs
from barrier_sensitivity_r15 import monthly_from_history


def test_fast_query_matches_frozen_barriers_and_exact_date_cutoff():
 g=pd.DataFrame(dict(publication_proxy_date=pd.to_datetime(['2023-01-01','2023-02-01','2023-03-01','2024-06-01']),value=[0.,0.,np.nan,4.]))
 dates=pd.to_datetime(['2022-12-30','2023-01-01','2023-01-02','2023-02-01','2023-02-02','2023-03-02','2023-12-01','2024-06-02'])
 fast=monthly_fast(g,dates)
 for row in fast.itertuples():
  expected=monthly_from_history(g,row.date)
  assert row.status==expected['status'] and np.allclose(row.revision,expected['revision'],equal_nan=True)


def test_missing_immediate_value_is_not_skipped():
 g=pd.DataFrame(dict(publication_proxy_date=pd.to_datetime(['2025-01-01','2025-02-01','2025-03-01']),value=[1.,np.nan,2.]))
 r=monthly_fast(g,pd.to_datetime(['2025-03-31'])).iloc[0]
 assert r.status=='unknown_current_or_prior' and r.previous_publication==pd.Timestamp('2025-02-01')


def test_common_broker_requires_identical_report_dates():
 p=pd.DataFrame([dict(stock_code='s',broker='b',fiscal_year=2026,date=pd.Timestamp('2025-09-30'),latest_publication=pd.Timestamp('2025-08-01'),previous_publication=pd.Timestamp('2025-07-01'),status='valid',revision=.1)])
 e=p.copy();e['revision']=.2
 same,bad=common_pairs(p,e);assert len(same)==1 and bad.empty
 e['previous_publication']=pd.Timestamp('2025-06-01');same,bad=common_pairs(p,e);assert same.empty and len(bad)==1
