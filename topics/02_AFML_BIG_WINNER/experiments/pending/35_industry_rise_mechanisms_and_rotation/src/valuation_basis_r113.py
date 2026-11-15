"""Raw, share and adjusted-price algebra; implied earnings are not actuals."""
import pandas as pd
from common import *
TOL=1e-10
FIELDS=['date','raw_close','vendor_pe_ttm','cap','total_shares','share_effective_date','listed','qfq_close','close_chain']
def calculate(s,calendar):
    s=s.copy();assert not s.duplicated(['security_id','month']).any()
    old=s[['security_id','month']+FIELDS].rename(columns={c:'prior_'+c for c in FIELDS});old['month']=old.month+1
    p=s.merge(old,on=['security_id','month'],how='left',validate='one_to_one')
    p['expected_date']=p.month.map(calendar);p['prior_expected_date']=(p.month-1).map(calendar)
    exact=p.date.eq(p.expected_date)&p.prior_date.eq(p.prior_expected_date)
    listed=p.listed.eq(True)&p.prior_listed.eq(True)
    price=np.isfinite(p.raw_close)&p.raw_close.gt(0)&np.isfinite(p.prior_raw_close)&p.prior_raw_close.gt(0)
    pe=np.isfinite(p.vendor_pe_ttm)&p.vendor_pe_ttm.gt(0)&np.isfinite(p.prior_vendor_pe_ttm)&p.prior_vendor_pe_ttm.gt(0)
    p['status']=np.select([~exact,~listed,~price,~pe],['missing_exact_completed_month','not_listed_both','invalid_raw_price','nonpositive_or_missing_pe'],default='raw_identity_ready');ready=p.status.eq('raw_identity_ready')
    def delta(a,b,mask):
        v=pd.Series(np.nan,index=p.index);v.loc[mask]=np.log(a[mask])-np.log(b[mask]);return v
    p['log_raw']=delta(p.raw_close,p.prior_raw_close,ready);p['log_pe']=delta(p.vendor_pe_ttm,p.prior_vendor_pe_ttm,ready)
    p['log_implied_eps']=delta(p.raw_close/p.vendor_pe_ttm,p.prior_raw_close/p.prior_vendor_pe_ttm,ready)
    total=ready.copy()
    for prefix in ['', 'prior_']:
        total &= np.isfinite(p[prefix+'cap'])&p[prefix+'cap'].gt(0)&np.isfinite(p[prefix+'total_shares'])&p[prefix+'total_shares'].gt(0)&p[prefix+'share_effective_date'].notna()&p[prefix+'share_effective_date'].le(p[prefix+'date'])&np.isclose(p[prefix+'cap'],p[prefix+'raw_close']*p[prefix+'total_shares'],rtol=1e-10,atol=0)
    p['total_basis_ready']=total;p['log_cap']=delta(p.cap,p.prior_cap,total);p['log_shares']=delta(p.total_shares,p.prior_total_shares,total);p['log_implied_total']=delta(p.cap/p.vendor_pe_ttm,p.prior_cap/p.prior_vendor_pe_ttm,total)
    q=ready&np.isfinite(p.qfq_close)&p.qfq_close.gt(0)&np.isfinite(p.prior_qfq_close)&p.prior_qfq_close.gt(0)&p.close_chain.notna()&~p.close_chain.isin(['','__MISSING__'])&p.close_chain.eq(p.prior_close_chain)
    p['adjusted_basis_ready']=q;p['log_qfq']=delta(p.qfq_close,p.prior_qfq_close,q);p['adjustment_wedge']=p.log_qfq-p.log_raw
    p['shares_changed']=(p.log_shares.abs()>TOL).where(total);p['adjustment_changed']=(p.adjustment_wedge.abs()>TOL).where(q)
    def direction(x):return np.where(x>TOL,1,np.where(x<-TOL,-1,0))
    p['implied_direction_disagreement']=pd.Series(direction(p.log_implied_eps)!=direction(p.log_implied_total),index=p.index).where(total)
    return p

def run():
    out=ROOT/'outputs/r113';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r112/valuation_monthly_coverage.parquet',CACHE/'extension_v2/products/panel.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
    s=pd.read_parquet(paths[0]);q=pd.read_parquet(paths[1],columns=['security_id','month','qfq_close','close_chain']);s=s.merge(q,on=['security_id','month'],how='left',validate='one_to_one')
    ix=pd.DatetimeIndex(pd.read_parquet(paths[2]).index);dates=pd.Series(ix,index=ix.to_period('M')).groupby(level=0).max();dates=dates[dates.index.end_time.normalize()<=ix.max()]
    p=calculate(s,dates);p.to_parquet(out/'stock_basis.parquet',index=False)
    p.assign(year=p.date.dt.year).groupby(['year','status']).size().rename('rows').reset_index().to_csv(out/'annual_coverage.csv',index=False)
    both=p.total_basis_ready&p.adjusted_basis_ready
    p.loc[both].groupby(['shares_changed','adjustment_changed','implied_direction_disagreement']).size().rename('rows').reset_index().to_csv(out/'basis_cross_tab.csv',index=False)
    ready=p.status.eq('raw_identity_ready');total=p.total_basis_ready;adj=p.adjusted_basis_ready
    summary=dict(rows=len(p),raw_ready=int(ready.sum()),total_ready=int(total.sum()),adjusted_ready=int(adj.sum()),both_ready=int(both.sum()),status_counts=p.status.value_counts().to_dict(),share_changes=int(p.shares_changed.eq(True).sum()),adjustment_changes=int(p.adjustment_changed.eq(True).sum()),implied_direction_disagreements=int(p.implied_direction_disagreement.eq(True).sum()),max_raw_identity_error=float((p.log_raw-p.log_pe-p.log_implied_eps).abs().max()),max_total_identity_error=float((p.log_cap-p.log_pe-p.log_implied_total).abs().max()),max_share_identity_error=float((p.log_implied_total-p.log_implied_eps-p.log_shares).abs().max()),abs_wedge_quantiles=p.adjustment_wedge.abs().dropna().quantile([.5,.9,.99,1]).to_dict(),adopted=False,interpretation='algebraic basis audit, not observed earnings or causal attribution')
    js(out/'summary.json',summary)
    paths +=[Path(__file__),ROOT/'protocols/r113.json',ROOT/'src/common.py'];js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},outputs={n:sha(out/n) for n in ['stock_basis.parquet','annual_coverage.csv','basis_cross_tab.csv','summary.json']}));print(summary)
if __name__=='__main__':run()
