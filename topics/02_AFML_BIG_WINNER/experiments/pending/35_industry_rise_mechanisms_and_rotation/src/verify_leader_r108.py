"""Independent vector reconstruction of all prior ranks and feature coverage."""
import pandas as pd
from common import *
K=KEY+['date']

def run():
    out=ROOT/'outputs/r108';receipt=json.loads((out/'receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    assert 'next_return' not in receipt['stock_columns']
    s=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=receipt['stock_columns']).set_index(['month','security_id'])
    m=pd.read_parquet(out/'member_ledger.parquet');f=pd.read_parquet(out/'industry_features.parquet')
    assert not f.duplicated(K).any() and not m.duplicated(K+['security_id']).any()
    observed=pd.concat([pd.read_parquet(ROOT/f'data/{p}.parquet',columns=K) for p in ['monthly_panel','l1_monthly_panel']],ignore_index=True).drop_duplicates()
    cat=pd.read_csv(ROOT/'outputs/universe_current.csv')[KEY].drop_duplicates();full=cat.merge(observed[['era','level','date']].drop_duplicates(),on=['era','level'])
    grid=pd.concat([full,observed],ignore_index=True).drop_duplicates().sort_values(K).reset_index(drop=True)
    pd.testing.assert_frame_equal(f[K],grid)
    assert f.catalogue_identity.equals(f[KEY].apply(tuple,axis=1).isin(set(map(tuple,cat.to_numpy()))))
    assert f.observed_panel_row.equals(f[K].apply(tuple,axis=1).isin(set(map(tuple,observed.to_numpy()))))
    members=pd.concat([pd.read_parquet(p,columns=['month']+KEY+['security_id','unresolved']) for p in [CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet']],ignore_index=True)
    expected_members=grid.assign(month=grid.date.dt.to_period('M')-1).merge(members,on=['month']+KEY,how='inner')
    fields=K+['security_id'];pd.testing.assert_frame_equal(m[fields+['unresolved']].sort_values(fields).reset_index(drop=True),expected_members[fields+['unresolved']].sort_values(fields).reset_index(drop=True))
    assert (m.origin_month==m.date.dt.to_period('M')-1).all() and (m.signal_month==m.date.dt.to_period('M')).all()
    start=s.reindex(pd.MultiIndex.from_arrays([m.origin_month,m.security_id])).reset_index(drop=True);end=s.reindex(pd.MultiIndex.from_arrays([m.signal_month,m.security_id])).reset_index(drop=True)
    for col in ['date','cap','qfq_close','close_chain','listed','raw_close','total_shares','share_effective_date']:
        pd.testing.assert_series_equal(m['origin_'+col].reset_index(drop=True),start[col],check_names=False,check_dtype=False)
    for src,dest in [('date','signal_date'),('qfq_close','signal_close'),('close_chain','signal_chain'),('listed','signal_listed')]:pd.testing.assert_series_equal(m[dest],end[src],check_names=False,check_dtype=False)
    market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
    dates=pd.Series(market,index=market).groupby(market.to_period('M')).max()
    expected_origin=m.origin_month.map(dates)
    cap_ok=start.listed.eq(True)&np.isfinite(start.cap)&start.cap.gt(0)&start.raw_close.gt(0)&start.total_shares.gt(0)&start.share_effective_date.notna()&start.share_effective_date.le(start.date)&start.date.eq(expected_origin)&start.date.lt(m.date)
    pd.testing.assert_series_equal(cap_ok,m.origin_cap_valid,check_names=False)
    exact=start.date.eq(expected_origin)&end.date.eq(m.date)&start.date.lt(m.date)
    price=start.listed.eq(True)&end.listed.eq(True)&np.isfinite(start.qfq_close)&start.qfq_close.gt(0)&np.isfinite(end.qfq_close)&end.qfq_close.gt(0)
    chain=start.close_chain.notna()&end.close_chain.notna()&~start.close_chain.isin(['','__MISSING__'])&start.close_chain.eq(end.close_chain)
    status=np.where(~exact,'missing_exact_endpoint',np.where(~price,'invalid_endpoint_price_or_listing',np.where(~chain,'missing_or_changed_chain','known')))
    assert (m.return_status==status).all()
    ret=(end.qfq_close/start.qfq_close-1).where(exact&price&chain)
    np.testing.assert_allclose(m.past_return,ret,atol=1e-14,equal_nan=True)
    m=m.copy();m['cap_ok']=cap_ok;m['unresolved_missing']=m.unresolved.isna()
    a=m.groupby(K).agg(members=('security_id','size'),unresolved=('unresolved','max'),cap_known=('cap_ok','sum'),unresolved_missing=('unresolved_missing','sum'))
    a['ranking_status']=np.where(a.unresolved_missing.gt(0)|a.unresolved.ne(0),'unresolved_members',np.where(a.members.lt(5),'too_few_members',np.where(a.cap_known.ne(a.members),'incomplete_prior_cap','rank_ready')))
    ranked=m.sort_values(K+['origin_cap','security_id'],ascending=[True]*len(K)+[False,True]);rank=ranked.groupby(K).cumcount()+1
    ready=ranked.set_index(K).index.map(a.ranking_status.to_dict())=='rank_ready';rank=rank.where(ready)
    rank=rank.reindex(m.index);np.testing.assert_allclose(m.prior_cap_rank,rank,equal_nan=True)
    m['leader_value']=ret.where(rank.le(3));m['follower_value']=ret.where(rank.gt(3))
    stats=m.groupby(K).agg(leader_known=('leader_value','count'),follower_known=('follower_value','count'),leader_return=('leader_value','mean'),follower_return=('follower_value','mean'));a=a.join(stats)
    a['status']=np.where(a.ranking_status.ne('rank_ready'),a.ranking_status,np.where(a.leader_known.lt(3),'leader_return_missing',np.where(a.follower_known.lt(2)|(a.follower_known/(a.members-3)).lt(.8),'follower_coverage_insufficient','historical_feature_available')))
    ready=a.status.eq('historical_feature_available');a['leader_return']=a.leader_return.where(ready);a['follower_return']=a.follower_return.where(ready);a['leader_spread']=a.leader_return-a.follower_return;a['strict_complete']=ready&a.follower_known.eq(a.members-3)
    expected=grid.merge(a.reset_index(),on=K,how='left',validate='one_to_one')
    for c in ['status','ranking_status']:assert f[c].equals(expected[c].fillna('no_prior_month_membership'))
    for c in ['members','unresolved','leader_known','follower_known','leader_return','follower_return','leader_spread']:np.testing.assert_allclose(f[c],expected[c],atol=1e-14,equal_nan=True)
    assert f.strict_complete.equals(expected.strict_complete.eq(True)) and f.available_at_proxy.equals(f.date)
    coverage=f.groupby(['era','level','status']).size().rename('rows').reset_index();pd.testing.assert_frame_equal(pd.read_csv(out/'coverage.csv'),coverage)
    summary=json.loads((out/'summary.json').read_text());assert summary['rows']==len(f) and summary['member_rows']==len(m) and summary['available']==f.leader_spread.notna().sum() and summary['strict_complete']==f.strict_complete.sum()
    assert summary['member_return_status']==m.return_status.value_counts().to_dict()
    js(out/'verification.json',dict(status='PASS',grid_rows=len(f),member_rows=len(m),available=int(f.leader_spread.notna().sum()),strict_complete=int(f.strict_complete.sum()),scope='full catalogue/source union, exact prior members/ranks, all endpoint prices/chains/returns/statuses, no future outcomes'))
    print('PASS',len(f),'industry dates',len(m),'members')

if __name__=='__main__':run()
