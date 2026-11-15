"""Prior-month ranked size leaders and contemporaneous completed-month spread."""
import pandas as pd
from common import *
STOCK=['month','date','security_id','qfq_close','close_chain','raw_close','total_shares','share_effective_date','cap','listed']

def aggregate(g):
    n=len(g);u=g.unresolved.max();r=dict(members=n,unresolved=u,ranking_status='rank_ready',leader_known=0,follower_known=0,leader_return=np.nan,follower_return=np.nan,leader_spread=np.nan,strict_complete=False)
    if g.unresolved.isna().any() or u!=0:r['ranking_status']='unresolved_members'
    elif n<5:r['ranking_status']='too_few_members'
    elif not g.origin_cap_valid.all():r['ranking_status']='incomplete_prior_cap'
    if r['ranking_status']!='rank_ready':r['status']=r['ranking_status'];return r,pd.Series(np.nan,index=g.index)
    order=g.sort_values(['origin_cap','security_id'],ascending=[False,True]).index
    rank=pd.Series(np.arange(1,n+1),index=order).reindex(g.index)
    leaders=g[rank.le(3)];followers=g[rank.gt(3)]
    lk=int(leaders.past_return.notna().sum());fk=int(followers.past_return.notna().sum());r.update(leader_known=lk,follower_known=fk)
    if lk<3:r['status']='leader_return_missing'
    elif fk<2 or fk/(n-3)<.8:r['status']='follower_coverage_insufficient'
    else:
        lr=float(leaders.past_return.mean());fr=float(followers.past_return.mean())
        r.update(status='historical_feature_available',leader_return=lr,follower_return=fr,leader_spread=lr-fr,strict_complete=fk==n-3)
    return r,rank

def prepare_members(stocks,members,grid,calendar):
    if stocks.duplicated(['month','security_id']).any():raise ValueError('duplicate stock month')
    if members.duplicated(['month']+KEY+['security_id']).any():raise ValueError('duplicate membership')
    s=stocks[STOCK].copy();m=members[['month']+KEY+['security_id','unresolved']].rename(columns={'month':'origin_month'})
    m['signal_month']=m.origin_month+1
    dates=pd.Series(pd.DatetimeIndex(calendar),index=pd.DatetimeIndex(calendar));ends=dates.groupby(dates.index.to_period('M')).max()
    m['date']=m.signal_month.map(ends);m['origin_date_expected']=m.origin_month.map(ends)
    m=m.merge(grid[KEY+['date']],on=KEY+['date'],how='inner',validate='many_to_one')
    origin=s.rename(columns={c:'origin_'+c for c in STOCK if c!='security_id'})
    m=m.merge(origin,on=['origin_month','security_id'],how='left',validate='many_to_one')
    target=s[['month','date','security_id','qfq_close','close_chain','listed']].rename(columns={'month':'signal_month','date':'signal_date','qfq_close':'signal_close','close_chain':'signal_chain','listed':'signal_listed'})
    m=m.merge(target,on=['signal_month','security_id'],how='left',validate='many_to_one')
    m['origin_cap_valid']=m.origin_listed.eq(True)&np.isfinite(m.origin_cap)&m.origin_cap.gt(0)&m.origin_raw_close.gt(0)&m.origin_total_shares.gt(0)&m.origin_share_effective_date.notna()&m.origin_share_effective_date.le(m.origin_date)&m.origin_date.eq(m.origin_date_expected)&m.origin_date.lt(m.date)
    dates_ok=m.origin_date.eq(m.origin_date_expected)&m.signal_date.eq(m.date)&m.origin_date.lt(m.date)
    price_ok=m.origin_listed.eq(True)&m.signal_listed.eq(True)&np.isfinite(m.origin_qfq_close)&m.origin_qfq_close.gt(0)&np.isfinite(m.signal_close)&m.signal_close.gt(0)
    chain_ok=m.origin_close_chain.notna()&m.signal_chain.notna()&m.origin_close_chain.ne('')&m.origin_close_chain.ne('__MISSING__')&m.origin_close_chain.eq(m.signal_chain)
    m['return_status']=np.select([~dates_ok,~price_ok,~chain_ok],['missing_exact_endpoint','invalid_endpoint_price_or_listing','missing_or_changed_chain'],default='known')
    m['past_return']=(m.signal_close/m.origin_qfq_close-1).where(m.return_status.eq('known'))
    return m

def run():
    out=ROOT/'outputs/r108';out.mkdir(exist_ok=True)
    paths=[CACHE/'extension_v2/products/panel.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'outputs/universe_current.csv',CACHE/'forecast_v5/CSI_ALL.parquet']
    stocks=pd.read_parquet(paths[0],columns=STOCK);members=pd.concat([pd.read_parquet(p,columns=['month']+KEY+['security_id','unresolved']) for p in paths[1:3]],ignore_index=True)
    observed=pd.concat([pd.read_parquet(p,columns=KEY+['date']) for p in paths[3:5]],ignore_index=True).drop_duplicates()
    catalog=pd.read_csv(paths[5])[KEY].drop_duplicates();dates=observed[['era','level','date']].drop_duplicates()
    full=catalog.merge(dates,on=['era','level'],validate='many_to_many');grid=pd.concat([full,observed],ignore_index=True).drop_duplicates().sort_values(KEY+['date']).reset_index(drop=True)
    grid['catalogue_identity']=grid[KEY].apply(tuple,axis=1).isin(set(map(tuple,catalog.to_numpy())))
    grid['observed_panel_row']=grid[KEY+['date']].apply(tuple,axis=1).isin(set(map(tuple,observed.to_numpy())))
    ledger=prepare_members(stocks,members,grid,pd.read_parquet(paths[6]).index);rows=[];ledger['prior_cap_rank']=np.nan
    for key,g in ledger.groupby(KEY+['date'],sort=False):
        rec,rank=aggregate(g);ledger.loc[g.index,'prior_cap_rank']=rank;rows.append(dict(zip(KEY+['date'],key),**rec))
    result=grid.merge(pd.DataFrame(rows),on=KEY+['date'],how='left',validate='one_to_one')
    result['status']=result.status.fillna('no_prior_month_membership');result['ranking_status']=result.ranking_status.fillna('no_prior_month_membership');result['strict_complete']=result.strict_complete.fillna(False).astype(bool)
    result['available_at_proxy']=result.date;result['quality']='Historical-proxy; not initial-publication PIT'
    ledger.to_parquet(out/'member_ledger.parquet',index=False);result.to_parquet(out/'industry_features.parquet',index=False)
    result.groupby(['era','level','status']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    summary=dict(rows=len(result),observed_rows=int(result.observed_panel_row.sum()),catalogue_rows=int(result.catalogue_identity.sum()),available=int(result.leader_spread.notna().sum()),strict_complete=int(result.strict_complete.sum()),member_rows=len(ledger),member_return_status=ledger.return_status.value_counts().to_dict(),no_future_outcomes_read=True)
    js(out/'summary.json',summary)
    paths += [Path(__file__),ROOT/'protocols/r108.json',ROOT/'src/common.py']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},stock_columns=STOCK,outputs={n:sha(out/n) for n in ['member_ledger.parquet','industry_features.parquet','coverage.csv','summary.json']}));print(summary)

if __name__=='__main__':run()
