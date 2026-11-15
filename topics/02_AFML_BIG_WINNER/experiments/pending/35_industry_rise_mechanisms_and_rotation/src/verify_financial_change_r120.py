"""Independent endpoint, complete population, and aggregation reconstruction."""
import pandas as pd
from common import *
K=KEY+['date']
def same_series(a,b):
    assert np.array_equal(a.isna(),b.isna())
    good=a.notna()
    pd.testing.assert_series_equal(a[good].reset_index(drop=True),b[good].reset_index(drop=True),check_names=False)

def run():
    out=ROOT/'outputs/r120';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    s=pd.read_parquet(out/'stock_changes.parquet')
    cols=['month','date','security_id','clock','join_status','financial_status','ttm_profit','report_period','report_available_at','component_available_at']
    source=pd.read_parquet(ROOT/'outputs/r117/linked_monthly.parquet')
    pd.testing.assert_frame_equal(s[cols],source[cols])
    indexed=source.set_index(['security_id','clock','month'])
    prior=indexed.reindex(pd.MultiIndex.from_arrays([s.security_id,s.clock,s.month-1],names=indexed.index.names)).reset_index(drop=True)
    for c in cols:
        if c not in ['security_id','clock','month']:same_series(s['prior_'+c],prior[c])
    now=source.join_status.eq('financial_snapshot_linked')&source.financial_status.eq('known_ttm')&np.isfinite(source.ttm_profit)&source.report_available_at.le(source.date)&source.component_available_at.le(source.date)
    old=prior.join_status.eq('financial_snapshot_linked')&prior.financial_status.eq('known_ttm')&np.isfinite(prior.ttm_profit)&prior.report_available_at.le(prior.date)&prior.component_available_at.le(prior.date)
    assert np.array_equal(now,s.current_ready) and np.array_equal(old,s.prior_ready)
    status=np.where(prior.date.isna(),'no_exact_prior_month',np.where(~now,'current_financial_unknown',np.where(~old,'prior_financial_unknown','known_pair')))
    assert np.array_equal(status,s.pair_status);known=status=='known_pair'
    expected=np.full(len(s),np.nan);a=source.ttm_profit.to_numpy()[known];b=prior.ttm_profit.to_numpy()[known]
    values=np.zeros(len(a));nz=(abs(a)+abs(b))!=0;values[nz]=2*(a[nz]-b[nz])/(abs(a[nz])+abs(b[nz]));expected[known]=values
    np.testing.assert_allclose(expected,s.change,rtol=1e-12,atol=1e-12,equal_nan=True);assert np.all(abs(values)<=2)
    transition=np.full(len(s),'unknown',dtype=object)
    transition[known]=np.where(source.report_period[known].to_numpy()==prior.report_period[known].to_numpy(),'same_report',np.where(source.report_period[known].to_numpy()>prior.report_period[known].to_numpy(),'advanced_report','regressed_report'))
    assert np.array_equal(transition,s.transition)
    base=pd.read_parquet(ROOT/'outputs/r108/member_ledger.parquet',columns=K+['security_id','origin_month','signal_month','origin_date_expected','unresolved'])
    base=base[base.date.isin(s.date.unique())].merge(pd.DataFrame({'clock':['notice','update']}),how='cross')
    m=pd.read_parquet(out/'member_changes.parquet');pd.testing.assert_frame_equal(m[base.columns],base)
    lookup=s.set_index(['security_id','clock','month']).reindex(pd.MultiIndex.from_frame(base[['security_id','clock','signal_month']].rename(columns={'signal_month':'month'}))).reset_index(drop=True)
    for c in s.columns:
        if c in ['security_id','clock','month']:continue
        dest='stock_date' if c=='date' else c
        same_series(m[dest],lookup[c])
    exact=base.date.eq(lookup.date)&base.origin_date_expected.eq(lookup.prior_date)&base.origin_month.eq(base.signal_month-1)
    assert np.array_equal(exact,m.exact_endpoints) and np.array_equal(exact&lookup.pair_status.eq('known_pair'),m.member_known)
    p=pd.read_parquet(out/'industry_changes.parquet')
    grid=pd.read_parquet(ROOT/'outputs/r108/industry_features.parquet',columns=K+['catalogue_identity','observed_panel_row'])
    grid=grid[grid.date.isin(s.date.unique())].merge(pd.DataFrame({'clock':['notice','update']}),how='cross')
    pd.testing.assert_frame_equal(p[grid.columns],grid)
    pp=p.set_index(K+['clock']);seen=set()
    for key,g in m.groupby(K+['clock'],sort=False):
        row=pp.loc[key];seen.add(key);q=g[g.member_known];den=len(g)+g.unresolved.max() if g.unresolved.notna().all() else np.nan
        st='unknown_denominator' if not np.isfinite(den) else 'too_few_members' if den<5 else 'insufficient_financial_coverage' if len(q)<.8*den else 'eligible_subset'
        strict=st=='eligible_subset' and len(q)==den and g.unresolved.max()==0
        assert row.status==st and row.strict_complete==strict and row.named_members==len(g) and row.known==len(q)
        np.testing.assert_allclose([row.members,row.coverage],[den,len(q)/den if den>0 else np.nan],equal_nan=True)
        for col,expected_count in [('advanced',q.transition.eq('advanced_report').sum()),('same_period',q.transition.eq('same_report').sum()),('regressed',q.transition.eq('regressed_report').sum()),('negative_endpoint',(q.ttm_profit.lt(0)|q.prior_ttm_profit.lt(0)).sum())]:assert row[col]==expected_count
        means=[q.change.mean(),np.sign(q.change).mean(),q.change.ne(0).mean(),q.transition.eq('advanced_report').mean()] if st=='eligible_subset' else [np.nan]*4
        np.testing.assert_allclose(row[['mean_change','net_improvement_breadth','changed_fraction','advanced_fraction']].to_numpy(dtype=float),means,equal_nan=True)
        np.testing.assert_allclose(row.full_population_mean,q.change.mean() if strict else np.nan,equal_nan=True)
    missing=p[~pd.MultiIndex.from_frame(p[K+['clock']]).isin(seen)]
    assert missing.status.eq('no_prior_membership').all() and missing.mean_change.isna().all() and not missing.strict_complete.any()
    summary=p.groupby(['era','level','clock']).agg(rows=('date','size'),eligible=('mean_change','count'),strict=('strict_complete','sum'),mean_coverage=('coverage','mean')).reset_index()
    pd.testing.assert_frame_equal(summary,pd.read_csv(out/'summary.csv'),check_dtype=False)
    cov=p.groupby(['era','level','clock','year','status']).size().rename('rows').reset_index()
    pd.testing.assert_frame_equal(cov,pd.read_csv(out/'coverage.csv'),check_dtype=False)
    sc=s.groupby(['clock','pair_status','transition']).size().rename('rows').reset_index()
    pd.testing.assert_frame_equal(sc,pd.read_csv(out/'stock_coverage.csv'),check_dtype=False)
    wide=p.pivot(index=K,columns='clock',values='status').reset_index();wide['both_eligible']=wide.notice.eq('eligible_subset')&wide['update'].eq('eligible_subset')
    common=wide.groupby(['era','level']).agg(rows=('date','size'),both_eligible=('both_eligible','sum')).reset_index()
    pd.testing.assert_frame_equal(common,pd.read_csv(out/'common_coverage.csv'),check_dtype=False)
    no_pe_gate=int((known&~source.comparison_eligible).sum())
    js(out/'verification.json',dict(status='PASS',stock_rows=len(s),known_pairs=int(known.sum()),member_rows=len(m),industry_rows=len(p),eligible=int(p.mean_change.notna().sum()),strict=int(p.strict_complete.sum()),known_pairs_without_pe_comparison_eligibility=no_pe_gate,negative_endpoint_pairs=int((known&(source.ttm_profit.lt(0)|prior.ttm_profit.lt(0))).sum()),strict_PIT=False,prediction_evaluated=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
