import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from build_three_factor_panel import forward_anchor,PANEL,OUT
from run_three_factor_ablation import VARIANTS,scaled_features
from evaluate_three_factor_ablation import factorial_edges


def test_forward_anchor_is_a_past_information_scenario():
    # Positive PE, known growth and prior valuation alone determine the anchor.
    np.testing.assert_allclose(forward_anchor([20,-20,100,-100],[10]*4,[15]*4),[.8,.2,.95,.05])
    np.testing.assert_allclose(forward_anchor([0],[10],[10]),[0])


def test_all_factorial_edges_exist():
    assert len(VARIANTS)==8
    assert set(map(frozenset,VARIANTS.values()))==set(frozenset(g) for g in [[],['C'],['P'],['F'],['C','P'],['C','F'],['P','F'],['C','P','F']])
    edges=factorial_edges();assert len(edges)==12
    for e in edges:
        assert set(VARIANTS[e['with_model']])-set(VARIANTS[e['without']])=={e['factor']}


def test_forward_anchor_historical_pe_reconstruction():
    d=pd.read_parquet(PANEL)
    sample=d[d.common_eligible].sample(15,random_state=24)
    for _,r in sample.iterrows():
        v=pd.read_parquet(OUT/f'local_cache/public_valuation/{r.instrument[2:]}.parquet')
        dates=pd.to_datetime(v.TRADE_DATE)
        pe=pd.to_numeric(v.PE_TTM,errors='coerce')
        history=pe[(dates<r.date)&(pe>0)]
        assert len(history)>=252
        np.testing.assert_allclose(r.prior_pe_median,history.median())
        np.testing.assert_allclose(r.forward_return_12m,(1+r.growth_assumption)*history.median()/r.current_pe-1)
        assert r.financial_available_date<r.date and r.yield_observation_date<r.date


def test_scaling_fits_training_only():
    cols=['vol63','log_cap','credit_spread_3y','credit_change63','pe_percentile','forward_log_anchor12']
    train=pd.DataFrame({c:[0.,1.,2.,3.] for c in cols})
    one=pd.DataFrame({c:[1.] for c in cols})
    _,a=scaled_features(train,one)
    other=pd.concat([one,pd.DataFrame({c:[100000.] for c in cols})],ignore_index=True)
    _,b=scaled_features(train,other)
    np.testing.assert_array_equal(a.to_numpy(),b.iloc[:1].to_numpy())


def test_growth_comes_from_available_report_not_future_earnings():
    d=pd.read_parquet(PANEL)
    sample=d[d.common_eligible].sample(10,random_state=37)
    for _,r in sample.iterrows():
        f=pd.read_parquet(OUT/f'local_cache/public_financials/{r.instrument[2:]}.{r.instrument[:2]}.parquet')
        for c in ['REPORT_DATE','NOTICE_DATE','UPDATE_DATE']:f[c]=pd.to_datetime(f[c],errors='coerce')
        f=f.dropna(subset=['REPORT_DATE','NOTICE_DATE','UPDATE_DATE'])
        f['available']=f[['NOTICE_DATE','UPDATE_DATE']].max(axis=1)
        f=f[(f.REPORT_DATE<=f.NOTICE_DATE)&(f.available<r.date)].sort_values(['REPORT_DATE','available'])
        latest=f.iloc[-1]
        assert latest.REPORT_DATE==r.financial_report_date
        assert latest.available==r.financial_available_date
        np.testing.assert_allclose(float(latest.PARENTNETPROFITTZ),r.profit_growth)
