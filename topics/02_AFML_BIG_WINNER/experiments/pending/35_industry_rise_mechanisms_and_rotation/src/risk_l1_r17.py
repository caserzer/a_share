"""Synthetic L1 risk diagnostics; nominal membership is not stock replication."""
import pandas as pd
from common import *

def run():
    out=ROOT/'outputs/r17';hold=pd.read_parquet(out/'holdings.parquet');intervals=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit'])
    d=pd.read_parquet(ROOT/'data/l1_daily.parquet');price=d.pivot(index='date',columns='industry_code',values='nav')
    market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;price=price.reindex(market.index);returns=price.pct_change(fill_method=None)
    members=pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=['month','industry_code','security_id','unresolved'])
    risk=[];membership=[]
    for key,h in hold.groupby(['method','origin']):
        codes=h.industry_code.tolist();weights=h.set_index('industry_code').weight;origin=key[1]
        past=returns.loc[:origin,codes].tail(63).dropna();n=len(past)
        corr=past.corr().to_numpy();off=corr[np.triu_indices(len(codes),1)]
        w=weights.reindex(codes).to_numpy();prior_vol=np.sqrt(w@past.cov().to_numpy()@w*252) if n>=42 else np.nan
        rec=intervals[(intervals.method==key[0])&(intervals.origin==origin)].iloc[0]
        record=dict(method=key[0],origin=origin,selected=len(codes),target_hhi=float(w@w),prior_observations=n,prior_vol=prior_vol,
            prior_mean_correlation=float(np.mean(off)) if n>=42 else np.nan,interval_status=rec.status)
        if rec.status=='valid':
            path=price.loc[rec.entry:rec.exit,codes];a=path/path.iloc[0];value=a.mul(w,axis=1);drift=value.div(value.sum(axis=1),axis=0)
            record.update(max_drifted_industry_weight=drift.max().max(),max_drifted_hhi=(drift**2).sum(axis=1).max())
        risk.append(record)
        m=members[(members.month==origin.to_period('M'))&members.industry_code.isin(codes)]
        stock=[];unknown=0.
        for code,weight in weights.items():
            g=m[m.industry_code==code];known=g.security_id.nunique();unresolved=int(g.unresolved.max()) if len(g) else 0
            if not known:unknown+=weight;continue
            denominator=known+unresolved;unknown+=weight*unresolved/denominator
            stock.extend((sid,weight/denominator) for sid in g.security_id.drop_duplicates())
        stock=pd.DataFrame(stock,columns=['security_id','weight']);aggregated=stock.groupby('security_id').weight.sum()
        membership.append(dict(method=key[0],origin=origin,known_stock_count=len(aggregated),known_nominal_weight=aggregated.sum(),unresolved_nominal_weight=unknown,
            duplicate_member_entries=len(stock)-len(aggregated),max_known_stock_weight=aggregated.max(),known_stock_hhi=(aggregated**2).sum()))
    pd.DataFrame(risk).to_csv(out/'risk_by_origin.csv',index=False);pd.DataFrame(membership).to_csv(out/'membership_concentration.csv',index=False)
    daily=pd.read_parquet(out/'daily_returns.parquet');annual=[];monthly=[];tails=[]
    for method,g in daily.groupby('method'):
        for cost in ['gross','net20','net50']:
            if not g.whole_path_valid.all():continue
            for year,v in g.groupby(g.date.dt.year):annual.append(dict(method=method,cost=cost,year=year,days=len(v),return_value=(1+v[cost]).prod()-1,market_return=(1+v.benchmark).prod()-1))
            for month,v in g.groupby(g.date.dt.to_period('M')):monthly.append(dict(method=method,cost=cost,month=str(month),return_value=(1+v[cost]).prod()-1,market_return=(1+v.benchmark).prod()-1))
            q=g[cost].quantile(.05);tails.append(dict(method=method,cost=cost,days=len(g),daily_q05=q,daily_bottom5_mean=g.loc[g[cost]<=q,cost].mean(),negative_market_days=int(g.benchmark.lt(0).sum()),mean_on_negative_market_days=g.loc[g.benchmark.lt(0),cost].mean(),min_day=g[cost].min()))
    pd.DataFrame(annual).to_csv(out/'annual.csv',index=False);pd.DataFrame(monthly).to_csv(out/'monthly.csv',index=False);pd.DataFrame(tails).to_csv(out/'tail_risk.csv',index=False)
    js(out/'risk_receipt.json',dict(code_sha256=sha(__file__),holdings_sha256=sha(out/'holdings.parquet'),membership_source_sha256=sha(ROOT/'data/l1_assignments.parquet'),rows=len(risk),
        limitation='nominal membership weights include unresolved share, not actual price-covered basket weights or executable holdings; internal stock turnover unpriced'))
    print('R17 risk origins',len(risk))
if __name__=='__main__':run()
