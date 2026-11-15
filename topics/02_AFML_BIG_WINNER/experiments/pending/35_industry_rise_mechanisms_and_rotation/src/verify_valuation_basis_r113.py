"""Independent source lookup and ratio-based identity/coverage audit."""
import pandas as pd
from common import *
def close(a,b):np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-13,equal_nan=True)
def run():
    out=ROOT/'outputs/r113';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    p=pd.read_parquet(out/'stock_basis.parquet');s=pd.read_parquet(ROOT/'outputs/r112/valuation_monthly_coverage.parquet')
    pd.testing.assert_frame_equal(p[s.columns],s)
    price=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet').set_index(['security_id','month']);idx=pd.MultiIndex.from_frame(p[['security_id','month']])
    for c in ['qfq_close','close_chain']:pd.testing.assert_series_equal(p[c].reset_index(drop=True),price.reindex(idx)[c].reset_index(drop=True),check_names=False)
    prior_idx=pd.MultiIndex.from_arrays([p.security_id,p.month-1]);source=p.set_index(['security_id','month'])
    for c in ['date','raw_close','vendor_pe_ttm','cap','total_shares','share_effective_date','listed','qfq_close','close_chain']:
        a=p['prior_'+c].reset_index(drop=True);b=source[c].reindex(prior_idx).reset_index(drop=True)
        assert a.isna().equals(b.isna());pd.testing.assert_series_equal(a[a.notna()],b[b.notna()],check_names=False)
    ix=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    calendar={m:max(ix[ix.to_period('M')==m]) for m in ix.to_period('M').unique() if m.end_time.normalize()<=ix.max()}
    for col,months in [('expected_date',p.month),('prior_expected_date',p.month-1)]:pd.testing.assert_series_equal(months.map(calendar),p[col],check_names=False)
    exact=p.date.eq(p.expected_date)&p.prior_date.eq(p.prior_expected_date)
    listing=p.listed.eq(True)&p.prior_listed.eq(True);raw=np.isfinite(p.raw_close)&p.raw_close.gt(0)&np.isfinite(p.prior_raw_close)&p.prior_raw_close.gt(0);pe=np.isfinite(p.vendor_pe_ttm)&p.vendor_pe_ttm.gt(0)&np.isfinite(p.prior_vendor_pe_ttm)&p.prior_vendor_pe_ttm.gt(0)
    status=np.full(len(p),'raw_identity_ready',object);status[~pe]='nonpositive_or_missing_pe';status[~raw]='invalid_raw_price';status[~listing]='not_listed_both';status[~exact]='missing_exact_completed_month';assert np.array_equal(status,p.status)
    valid=status=='raw_identity_ready';total=valid.copy()
    for pre in ['', 'prior_']:
        cap=p[pre+'cap'];shares=p[pre+'total_shares'];price=p[pre+'raw_close'];clock=p[pre+'share_effective_date']
        total &= (np.isfinite(cap)&cap.gt(0)&np.isfinite(shares)&shares.gt(0)&clock.notna()&clock.le(p[pre+'date'])&np.isclose(cap,price*shares,rtol=1e-10,atol=0)).to_numpy()
    adj=valid & (np.isfinite(p.qfq_close)&p.qfq_close.gt(0)&np.isfinite(p.prior_qfq_close)&p.prior_qfq_close.gt(0)&p.close_chain.notna()&~p.close_chain.isin(['','__MISSING__'])&p.close_chain.eq(p.prior_close_chain)).to_numpy()
    assert np.array_equal(total,p.total_basis_ready) and np.array_equal(adj,p.adjusted_basis_ready)
    calculations={'log_raw':(p.raw_close,p.prior_raw_close,valid),'log_pe':(p.vendor_pe_ttm,p.prior_vendor_pe_ttm,valid),'log_implied_eps':(p.raw_close/p.vendor_pe_ttm,p.prior_raw_close/p.prior_vendor_pe_ttm,valid),'log_cap':(p.cap,p.prior_cap,total),'log_shares':(p.total_shares,p.prior_total_shares,total),'log_implied_total':(p.cap/p.vendor_pe_ttm,p.prior_cap/p.prior_vendor_pe_ttm,total),'log_qfq':(p.qfq_close,p.prior_qfq_close,adj)}
    for name,(a,b,mask) in calculations.items():
        expected=np.full(len(p),np.nan);expected[mask]=np.log(a[mask]/b[mask]);close(expected,p[name])
    close(p.adjustment_wedge,p.log_qfq-p.log_raw)
    for field,mask,values in [('shares_changed',total,p.log_shares.abs()>1e-10),('adjustment_changed',adj,p.adjustment_wedge.abs()>1e-10),('implied_direction_disagreement',total,((p.log_implied_eps>1e-10).astype(int)-(p.log_implied_eps<-1e-10).astype(int))!=((p.log_implied_total>1e-10).astype(int)-(p.log_implied_total<-1e-10).astype(int)))]:
        assert p[field].isna().equals(pd.Series(~mask));assert np.array_equal(p.loc[mask,field].astype(bool),values[mask])
    annual=pd.read_csv(out/'annual_coverage.csv').set_index(['year','status'])['rows'];expected=p.groupby([p.date.dt.year.astype('int64'),'status']).size();pd.testing.assert_series_equal(annual.sort_index(),expected.sort_index(),check_names=False)
    tab=pd.read_csv(out/'basis_cross_tab.csv').set_index(['shares_changed','adjustment_changed','implied_direction_disagreement'])['rows'];expected=p.loc[total&adj].groupby(['shares_changed','adjustment_changed','implied_direction_disagreement']).size();pd.testing.assert_series_equal(tab.sort_index(),expected.sort_index(),check_names=False,check_index_type=False)
    sm=json.loads((out/'summary.json').read_text());counts=dict(rows=len(p),raw_ready=int(valid.sum()),total_ready=int(total.sum()),adjusted_ready=int(adj.sum()),both_ready=int((total&adj).sum()),share_changes=int(p.shares_changed.eq(True).sum()),adjustment_changes=int(p.adjustment_changed.eq(True).sum()),implied_direction_disagreements=int(p.implied_direction_disagreement.eq(True).sum()))
    for k,v in counts.items():assert sm[k]==v
    assert sm['status_counts']==p.status.value_counts().to_dict()
    for k,series in [('max_raw_identity_error',p.log_raw-p.log_pe-p.log_implied_eps),('max_total_identity_error',p.log_cap-p.log_pe-p.log_implied_total),('max_share_identity_error',p.log_implied_total-p.log_implied_eps-p.log_shares)]:close(sm[k],series.abs().max());assert series.abs().max()<1e-12
    for q,value in sm['abs_wedge_quantiles'].items():close(value,np.quantile(p.adjustment_wedge.dropna().abs(),float(q)))
    js(out/'verification.json',dict(status='PASS',rows=len(p),raw_identities=int(valid.sum()),total_identities=int(total.sum()),adjusted_identities=int(adj.sum()),not_economic_validation=True));print('PASS',counts)
if __name__=='__main__':run()
