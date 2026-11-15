"""Consecutive financial TTM changes, keeping loss makers and the full denominator."""
import pandas as pd
from common import *
K=KEY+['date']
COLS=['month','date','security_id','clock','join_status','financial_status','ttm_profit','report_period','report_available_at','component_available_at']
def bounded_change(now,old):
    now=np.asarray(now,dtype=float);old=np.asarray(old,dtype=float);den=np.abs(now)+np.abs(old)
    return np.divide(2*(now-old),den,out=np.zeros_like(den),where=den!=0)
def aggregate(g):
    n=len(g);u=g.unresolved.max();den=n+u if g.unresolved.notna().all() else np.nan
    valid=g.member_known.eq(True);q=g.loc[valid];known=len(q)
    status='eligible_subset'
    if not np.isfinite(den):status='unknown_denominator'
    elif den<5:status='too_few_members'
    elif known<.8*den:status='insufficient_financial_coverage'
    ok=status=='eligible_subset';strict=ok and known==den and u==0
    return dict(named_members=n,unresolved=u,members=den,known=known,coverage=known/den if den>0 else np.nan,status=status,strict_complete=strict,
        advanced=int(q.transition.eq('advanced_report').sum()),same_period=int(q.transition.eq('same_report').sum()),regressed=int(q.transition.eq('regressed_report').sum()),
        negative_endpoint=int((q.ttm_profit.lt(0)|q.prior_ttm_profit.lt(0)).sum()),
        mean_change=q.change.mean() if ok else np.nan,
        net_improvement_breadth=np.sign(q.change).mean() if ok else np.nan,
        changed_fraction=q.change.ne(0).mean() if ok else np.nan,
        advanced_fraction=q.transition.eq('advanced_report').mean() if ok else np.nan,
        full_population_mean=q.change.mean() if strict else np.nan)
def run():
    out=ROOT/'outputs/r120';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r117/linked_monthly.parquet',ROOT/'outputs/r108/member_ledger.parquet',ROOT/'outputs/r108/industry_features.parquet']
    s=pd.read_parquet(paths[0],columns=COLS)
    assert not s.duplicated(['security_id','clock','month']).any()
    old=s.rename(columns={c:'prior_'+c for c in COLS if c not in ['security_id','clock','month']}).copy();old['month']=old.month+1
    s=s.merge(old,on=['security_id','clock','month'],how='left',validate='one_to_one')
    def ready(prefix):
        return s[prefix+'join_status'].eq('financial_snapshot_linked')&s[prefix+'financial_status'].eq('known_ttm')&np.isfinite(s[prefix+'ttm_profit'])&s[prefix+'report_available_at'].le(s[prefix+'date'])&s[prefix+'component_available_at'].le(s[prefix+'date'])
    s['current_ready']=ready('');s['prior_ready']=ready('prior_')
    s['pair_status']=np.select([s.prior_date.isna(),~s.current_ready,~s.prior_ready],['no_exact_prior_month','current_financial_unknown','prior_financial_unknown'],default='known_pair')
    valid=s.pair_status.eq('known_pair');s['change']=np.nan;s.loc[valid,'change']=bounded_change(s.loc[valid,'ttm_profit'],s.loc[valid,'prior_ttm_profit'])
    s['transition']='unknown';s.loc[valid,'transition']=np.select([s.loc[valid,'report_period'].eq(s.loc[valid,'prior_report_period']),s.loc[valid,'report_period'].gt(s.loc[valid,'prior_report_period'])],['same_report','advanced_report'],default='regressed_report')
    s.to_parquet(out/'stock_changes.parquet',index=False)
    m=pd.read_parquet(paths[1],columns=K+['security_id','origin_month','signal_month','origin_date_expected','unresolved'])
    m=m[m.date.isin(s.date.unique())].merge(pd.DataFrame({'clock':['notice','update']}),how='cross')
    m=m.merge(s.rename(columns={'date':'stock_date','month':'signal_month'}),on=['security_id','clock','signal_month'],how='left',validate='many_to_one')
    m['exact_endpoints']=m.date.eq(m.stock_date)&m.origin_date_expected.eq(m.prior_date)&m.origin_month.eq(m.signal_month-1)
    m['member_known']=m.exact_endpoints&m.pair_status.eq('known_pair')
    m.to_parquet(out/'member_changes.parquet',index=False)
    grid=pd.read_parquet(paths[2],columns=K+['catalogue_identity','observed_panel_row']);grid=grid[grid.date.isin(s.date.unique())]
    rows=[dict(zip(K+['clock'],key),**aggregate(g)) for key,g in m.groupby(K+['clock'],sort=False)]
    p=grid.merge(pd.DataFrame({'clock':['notice','update']}),how='cross').merge(pd.DataFrame(rows),on=K+['clock'],how='left',validate='one_to_one')
    p['status']=p.status.fillna('no_prior_membership');p['strict_complete']=p.strict_complete.eq(True);p['year']=p.date.dt.year
    p.to_parquet(out/'industry_changes.parquet',index=False)
    p.groupby(['era','level','clock','year','status']).size().rename('rows').reset_index().to_csv(out/'coverage.csv',index=False)
    summary=p.groupby(['era','level','clock']).agg(rows=('date','size'),eligible=('mean_change','count'),strict=('strict_complete','sum'),mean_coverage=('coverage','mean')).reset_index();summary.to_csv(out/'summary.csv',index=False)
    s.groupby(['clock','pair_status','transition']).size().rename('rows').reset_index().to_csv(out/'stock_coverage.csv',index=False)
    common=p.pivot(index=K,columns='clock',values='status').reset_index();common['both_eligible']=common.notice.eq('eligible_subset')&common['update'].eq('eligible_subset')
    common.groupby(['era','level']).agg(rows=('date','size'),both_eligible=('both_eligible','sum')).reset_index().to_csv(out/'common_coverage.csv',index=False)
    paths +=[Path(__file__),ROOT/'protocols/r120.json',ROOT/'src/common.py']
    names=['stock_changes.parquet','member_changes.parquet','industry_changes.parquet','coverage.csv','summary.csv','stock_coverage.csv','common_coverage.csv']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={n:sha(out/n) for n in names},stock_rows=len(s),member_rows=len(m),industry_rows=len(p),known_pairs=int(valid.sum()),eligible=int(p.mean_change.notna().sum()),strict=int(p.strict_complete.sum()),pe_filter=False,strict_PIT=False))
    print(summary.to_string(index=False));print('known stock pairs',int(valid.sum()));print(common.groupby(['era','level']).both_eligible.sum().to_string())
if __name__=='__main__':run()
