import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import numpy as np
from eps_comparability_r24 import pairs,sequences


def test_pair_requires_exact_report_and_year_and_no_conflict():
 base=dict(stock_code='000001',broker='b',publication_proxy_date=pd.Timestamp('2025-01-01'),raw_sha256='h')
 v=pd.DataFrame([dict(base,infoCode='a',fiscal_year=2025,basis='eps_cny_per_share',value=1.),dict(base,infoCode='a',fiscal_year=2025,basis='profit_cny',value=100.),dict(base,infoCode='b',fiscal_year=2025,basis='profit_cny',value=200.),dict(base,infoCode='a',fiscal_year=2026,basis='eps_cny_per_share',value=2.)])
 p=pairs(v);assert len(p)==3 and p.implied_shares.notna().sum()==1 and p.implied_shares.max()==100
 v=pd.concat([v,pd.DataFrame([dict(base,infoCode='a',fiscal_year=2025,basis='eps_cny_per_share',value=3.)])]);assert pairs(v).implied_shares.isna().all()


def test_missing_intermediate_report_blocks_pairing():
 reports=pd.DataFrame(dict(stock_code='000001',broker='b',infoCode=['a','b','c'],publication_proxy_date=pd.to_datetime(['2025-01-01','2025-02-01','2025-03-01'])))
 p=pd.DataFrame(dict(stock_code='000001',broker='b',infoCode=['a','c'],fiscal_year=2025,profit=[100.,120.],eps=[1.,1.2]))
 s=sequences(p,reports);assert len(s)==2 and s.implied_share_ratio.isna().all()


def test_profit_up_eps_down_exposes_denominator_not_inferred_split():
 reports=pd.DataFrame(dict(stock_code='000001',broker='b',infoCode=['a','b'],publication_proxy_date=pd.to_datetime(['2025-01-01','2025-02-01'])))
 p=pd.DataFrame(dict(stock_code='000001',broker='b',infoCode=['a','b'],fiscal_year=2025,profit=[100.,120.],eps=[1.,.8]))
 s=sequences(p,reports).iloc[0];assert s.opposite_revision_signs and np.isclose(s.implied_share_ratio,1.5)
 p.loc[1,'eps']=0;s=sequences(p,reports).iloc[0];assert pd.isna(s.implied_share_ratio)
