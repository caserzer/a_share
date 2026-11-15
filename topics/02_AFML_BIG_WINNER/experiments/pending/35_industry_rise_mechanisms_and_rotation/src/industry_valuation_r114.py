"""Fixed prior members, common-basis log identities and separate basket means."""
import pandas as pd
from common import *
K=KEY+['date']
BASIS={'raw':('status',['log_raw','log_pe','log_implied_eps']),'total':('total_basis_ready',['log_cap','log_pe','log_implied_total','log_implied_eps','log_shares']),'adjusted':('adjusted_basis_ready',['log_qfq','log_raw','log_pe','log_implied_eps','adjustment_wedge'])}
def aggregate(g,basis):
    flag,cols=BASIS[basis];valid=g[flag].eq('raw_identity_ready') if basis=='raw' else g[flag].eq(True)
    valid &= np.isfinite(g[cols]).all(axis=1);v=g.loc[valid,cols];known=len(v);u=g.unresolved.max();den=len(g)+u if g.unresolved.notna().all() else np.nan
    status='eligible_subset'
    if not np.isfinite(den):status='unknown_member_denominator'
    elif den<5:status='too_few_members'
    elif known<.8*den:status='insufficient_positive_basis_coverage'
    eligible=status=='eligible_subset';strict=eligible and u==0 and known==den
    r=dict(named_members=len(g),unresolved=u,members=den,known=known,coverage=known/den if np.isfinite(den) and den>0 else np.nan,status=status,strict_complete=strict)
    for col in cols:r['mean_'+col]=float(v[col].mean()) if eligible else np.nan
    primary=cols[0];mean=float(v[primary].mean()) if eligible else np.nan
    arithmetic=float(np.expm1(v[primary]).mean()) if eligible else np.nan
    r.update(mean_log_growth=mean,covered_geometric_growth=np.expm1(mean),covered_arithmetic_growth=arithmetic,full_basket_arithmetic=arithmetic if strict else np.nan,jensen_gap=np.log1p(arithmetic)-mean if eligible else np.nan)
    return r

def run():
    out=ROOT/'outputs/r114';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r108/member_ledger.parquet',ROOT/'outputs/r108/industry_features.parquet',ROOT/'outputs/r113/stock_basis.parquet']
    m=pd.read_parquet(paths[0],columns=K+['security_id','origin_month','signal_month','unresolved'])
    stock=pd.read_parquet(paths[2]);cols=list(dict.fromkeys(['security_id','month','date','status','total_basis_ready','adjusted_basis_ready']+[x for _,v in BASIS.values() for x in v]));z=stock[cols].rename(columns={'month':'signal_month','date':'stock_date'})
    m=m.merge(z,on=['security_id','signal_month'],how='left',validate='many_to_one');m['exact_stock_date']=m.date.eq(m.stock_date)
    for col in list(dict.fromkeys(x for _,v in BASIS.values() for x in v)):m.loc[~m.exact_stock_date,col]=np.nan
    m.to_parquet(out/'member_basis.parquet',index=False)
    grid=pd.read_parquet(paths[1])[K+['catalogue_identity','observed_panel_row']];rows=[]
    for key,g in m.groupby(K,sort=False):
        for basis in BASIS:rows.append(dict(zip(K,key),basis=basis,**aggregate(g,basis)))
    p=grid.merge(pd.DataFrame({'basis':list(BASIS)}),how='cross').merge(pd.DataFrame(rows),on=K+['basis'],how='left',validate='one_to_one');p['status']=p.status.fillna('no_prior_membership');p['strict_complete']=p.strict_complete.eq(True)
    p.to_parquet(out/'industry_basis.parquet',index=False)
    p.groupby(['era','level','basis','status','strict_complete']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    dates=[]
    for scope in ['covered80','strict100']:
        q=p[p.status.eq('eligible_subset') & (p.strict_complete if scope=='strict100' else True)]
        for key,g in q.groupby(['era','level','basis','date']):dates.append(dict(zip(['era','level','basis','date'],key),scope=scope,industries=len(g),mean_log_growth=g.mean_log_growth.mean(),arithmetic_growth=g.covered_arithmetic_growth.mean(),geometric_growth=g.covered_geometric_growth.mean(),jensen_gap=g.jensen_gap.mean()))
    d=pd.DataFrame(dates);d.to_csv(out/'date_metrics.csv',index=False)
    summary=d.groupby(['era','level','basis','scope']).agg(months=('date','size'),mean_log_growth=('mean_log_growth','mean'),arithmetic_growth=('arithmetic_growth','mean'),geometric_growth=('geometric_growth','mean'),mean_jensen_gap=('jensen_gap','mean')).reset_index();summary.to_csv(out/'summary.csv',index=False)
    paths +=[Path(__file__),ROOT/'protocols/r114.json',ROOT/'src/common.py'];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={n:sha(out/n) for n in ['member_basis.parquet','industry_basis.parquet','coverage.csv','date_metrics.csv','summary.csv']},member_rows=len(m),industry_basis_rows=len(p),eligible=int(p.status.eq('eligible_subset').sum()),strict_complete=int(p.strict_complete.sum()),adopted=False))
    print(p.groupby(['era','level','basis']).agg(rows=('date','size'),eligible=('mean_log_growth','count'),strict=('strict_complete','sum')).to_string());print(summary.to_string(index=False))
if __name__=='__main__':run()
