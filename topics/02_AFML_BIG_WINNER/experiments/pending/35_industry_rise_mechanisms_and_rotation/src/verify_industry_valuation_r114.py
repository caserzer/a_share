"""Independent member joins, denominators, basis means and summaries."""
import pandas as pd
from common import *
K=KEY+['date']
B={'raw':['log_raw','log_pe','log_implied_eps'],'total':['log_cap','log_pe','log_implied_total','log_implied_eps','log_shares'],'adjusted':['log_qfq','log_raw','log_pe','log_implied_eps','adjustment_wedge']}
def close(a,b):np.testing.assert_allclose(a,b,rtol=1e-10,atol=1e-12,equal_nan=True)
def run():
    out=ROOT/'outputs/r114';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    m=pd.read_parquet(out/'member_basis.parquet');old=pd.read_parquet(ROOT/'outputs/r108/member_ledger.parquet',columns=K+['security_id','origin_month','signal_month','unresolved']);pd.testing.assert_frame_equal(m[old.columns],old)
    assert (m.origin_month+1==m.signal_month).all()
    stock=pd.read_parquet(ROOT/'outputs/r113/stock_basis.parquet').set_index(['security_id','month']);z=stock.reindex(pd.MultiIndex.from_arrays([m.security_id,m.signal_month])).reset_index(drop=True)
    pd.testing.assert_series_equal(m.stock_date,z.date,check_names=False);assert m.exact_stock_date.equals(m.date.eq(z.date))
    for c in ['status','total_basis_ready','adjusted_basis_ready']:
        a=m[c];b=z[c];assert a.isna().equals(b.isna());pd.testing.assert_series_equal(a[a.notna()],b[b.notna()],check_names=False)
    for c in set(x for cols in B.values() for x in cols):close(m[c],z[c].where(m.exact_stock_date))
    p=pd.read_parquet(out/'industry_basis.parquet');grid=pd.read_parquet(ROOT/'outputs/r108/industry_features.parquet')[K+['catalogue_identity','observed_panel_row']]
    assert len(p)==3*len(grid) and not p.duplicated(K+['basis']).any()
    for basis in B:pd.testing.assert_frame_equal(p[p.basis==basis][grid.columns].reset_index(drop=True),grid)
    lookup=p.set_index(K+['basis']);visited=set();max_error=0.
    for key,g in m.groupby(K,sort=False):
      for basis,cols in B.items():
        row=lookup.loc[(*key,basis)];visited.add((*key,basis));n=len(g);u=g.unresolved.max();den=n+u if g.unresolved.notna().all() else np.nan
        valid=g.status.eq('raw_identity_ready') if basis=='raw' else g[{'total':'total_basis_ready','adjusted':'adjusted_basis_ready'}[basis]].eq(True)
        valid &= np.isfinite(g[cols]).all(axis=1);v=g[valid];count=len(v)
        status='unknown_member_denominator' if not np.isfinite(den) else 'too_few_members' if den<5 else 'insufficient_positive_basis_coverage' if count<.8*den else 'eligible_subset'
        assert row.status==status and row.named_members==n and row.known==count;close([row.members,row.unresolved,row.coverage],[den,u,count/den if np.isfinite(den) and den>0 else np.nan])
        strict=status=='eligible_subset' and u==0 and count==den;assert row.strict_complete==strict
        fields=['mean_'+c for c in cols]+['mean_log_growth','covered_geometric_growth','covered_arithmetic_growth','full_basket_arithmetic','jensen_gap']
        if status!='eligible_subset':assert row[fields].isna().all();continue
        means=[sum(v[c])/count for c in cols];close(row[['mean_'+c for c in cols]].to_numpy(dtype=float),means)
        primary=v[cols[0]].to_numpy();arith=np.exp(primary).sum()/count-1;geom=np.exp(primary.mean())-1;gap=np.log(1+arith)-primary.mean();assert gap>=-1e-12
        close(row[['mean_log_growth','covered_geometric_growth','covered_arithmetic_growth','full_basket_arithmetic','jensen_gap']].to_numpy(dtype=float),[primary.mean(),geom,arith,arith if strict else np.nan,gap])
        error=abs(means[0]-means[1]-means[2]) if basis in ['raw','total'] else abs(means[0]-means[2]-means[3]-means[4]);max_error=max(max_error,error);assert error<1e-12
        if basis=='total':assert abs(means[2]-means[3]-means[4])<1e-12
    absent=[key not in visited for key in lookup.index];assert lookup.loc[absent,'status'].eq('no_prior_membership').all();assert lookup.loc[absent,'full_basket_arithmetic'].isna().all()
    coverage=pd.read_csv(out/'coverage.csv').set_index(['era','level','basis','status','strict_complete'])['rows'];expected=p.groupby(['era','level','basis','status','strict_complete']).size();pd.testing.assert_series_equal(coverage.sort_index(),expected.sort_index(),check_names=False)
    d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);count=0
    for scope in ['covered80','strict100']:
      q=p[p.status.eq('eligible_subset')&(p.strict_complete if scope=='strict100' else True)]
      for key,g in q.groupby(['era','level','basis','date']):
        mask=d.scope.eq(scope)
        for c,val in zip(['era','level','basis','date'],key):mask &= d[c].eq(val)
        assert mask.sum()==1;row=d[mask].iloc[0];count+=1;assert row.industries==len(g)
        for a,b in [('mean_log_growth','mean_log_growth'),('arithmetic_growth','covered_arithmetic_growth'),('geometric_growth','covered_geometric_growth'),('jensen_gap','jensen_gap')]:close(row[a],np.mean(g[b]))
    assert count==len(d);summary=pd.read_csv(out/'summary.csv');assert len(summary)==d.groupby(['era','level','basis','scope']).ngroups
    for key,g in d.groupby(['era','level','basis','scope']):
        mask=np.ones(len(summary),bool)
        for c,val in zip(['era','level','basis','scope'],key):mask &= summary[c].eq(val)
        assert mask.sum()==1;row=summary[mask].iloc[0];assert row.months==len(g)
        for a,b in [('mean_log_growth','mean_log_growth'),('arithmetic_growth','arithmetic_growth'),('geometric_growth','geometric_growth'),('mean_jensen_gap','jensen_gap')]:close(row[a],np.mean(g[b]))
    assert rec['member_rows']==len(m) and rec['industry_basis_rows']==len(p) and rec['eligible']==p.status.eq('eligible_subset').sum() and rec['strict_complete']==p.strict_complete.sum()
    js(out/'verification.json',dict(status='PASS',member_rows=len(m),industry_basis_rows=len(p),eligible=rec['eligible'],strict_complete=rec['strict_complete'],max_mean_identity_error=max_error,date_rows=len(d),economic_or_predictive_validation=False));print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
