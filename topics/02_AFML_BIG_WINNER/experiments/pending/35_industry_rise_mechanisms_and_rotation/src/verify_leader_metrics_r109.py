"""Independent all-date paired scores, selection and calendar intervals."""
import pandas as pd
from scipy.stats import rankdata,norm
from common import *
G=['era','level','cohort','task','horizon']

def close(a,b):np.testing.assert_allclose(a,b,atol=1e-12,rtol=1e-10,equal_nan=True)

def run():
    out=ROOT/'outputs/r109';receipt=json.loads((out/'evaluation_receipt.json').read_text())
    for p,h in receipt['reads'].items():assert sha(p)==h
    for p,h in receipt['outputs'].items():assert sha(out/p)==h
    original=pd.read_parquet(out/'predictions.parquet');p=pd.read_parquet(out/'paired_predictions.parquet');d=pd.read_csv(out/'paired_date_metrics.csv',parse_dates=['date']);s=pd.read_csv(out/'summary.csv');annual=pd.read_csv(out/'annual_metrics.csv')
    keys=KEY+['date','cohort','task','horizon','year']
    for method,suffix in [('controls','base'),('with_leader','leader')]:
        source=original[original.method.eq(method)].sort_values(keys).reset_index(drop=True);paired=p.sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(paired[keys],source[keys]);close(paired['prediction_'+suffix],source.prediction);close(paired['decision_'+suffix],source.decision)
        for c in ['entry_date','maturity','excess','y','strict_complete']:pd.testing.assert_series_equal(paired[c],source[c],check_names=False)
    indexed=d.set_index(G+['date']);assert indexed.index.is_unique and set(indexed.index)==set(p.groupby(G+['date']).groups)
    for key,g in p.groupby(G+['date']):
        r=indexed.loc[key];v=g[g.y.notna()];k=max(1,int(np.ceil(len(g)/5)))
        old={x.industry_code for x in sorted(g.itertuples(),key=lambda x:(-x.prediction_base,x.industry_code))[:k]};new={x.industry_code for x in sorted(g.itertuples(),key=lambda x:(-x.prediction_leader,x.industry_code))[:k]}
        assert (r.n_signal,r.n_mature,r.selected,r.shared_selected)==(len(g),len(v),k,len(old&new))
        if not len(v):assert pd.isna(r.delta) and pd.isna(r.mse_reduction);continue
        y=v.y.to_numpy();bo=-np.mean((v.prediction_base-y)**2);bn=-np.mean((v.prediction_leader-y)**2);close(r.mse_reduction,bn-bo)
        if key[3]=='return':
            bo=bn=np.nan
            if len(v)>=20 and v.prediction_base.nunique()>1 and v.prediction_leader.nunique()>1:bo=np.corrcoef(rankdata(v.prediction_base),rankdata(y))[0,1];bn=np.corrcoef(rankdata(v.prediction_leader),rankdata(y))[0,1]
        else:
            def loss(x):
                x=np.clip(np.asarray(x),1e-15,1-1e-15);return -np.mean(np.where(y==1,np.log(x),np.log1p(-x)))
            close(r.logloss_reduction,loss(v.prediction_base)-loss(v.prediction_leader))
        close([r.baseline_utility,r.leader_utility,r.delta],[bo,bn,bn-bo])
    assert len(s)==d.groupby(G).ngroups and len(annual)==d.assign(year=d.date.dt.year).groupby(G+['year']).ngroups
    for row in annual.to_dict('records'):
        g=d[d.date.dt.year.eq(row['year'])]
        for k in G:g=g[g[k].eq(row[k])]
        assert row['months']==g.delta.notna().sum();close([row['mean_delta'],row['mean_mse_reduction'],row['mean_logloss_reduction']],[g.delta.mean(),g.mse_reduction.mean(),g.logloss_reduction.mean()])
    for row in s.to_dict('records'):
        g=d
        for k in G:g=g[g[k].eq(row[k])]
        v=g.dropna(subset=['delta']);x=v.delta.to_numpy();u=x-x.mean();months=v.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if row['horizon']==20 else 6
        kernel=np.maximum(1-np.abs(months[:,None]-months[None,:])/(lag+1),0);se=np.sqrt(max(float(u@kernel@u),0))/len(x);z=norm.ppf(1-.05/120)
        close(row['mean_delta'],x.mean())
        bounds=[se,x.mean()-1.96*se,x.mean()+1.96*se,x.mean()-z*se,x.mean()+z*se] if len(x)>=2 else [np.nan]*5
        close([row['standard_error'],row['low95'],row['high95'],row['family60_low'],row['family60_high']],bounds)
        years=v.groupby(v.date.dt.year).delta.mean();assert (row['months'],row['positive_years'],row['evaluated_years'])==(len(x),years.gt(0).sum(),len(years))
        support=row['cohort']=='main80' and row['horizon']==20 and len(x)>=24 and len(years)>=3 and years.gt(0).all() and x.mean()-z*se>0
        assert row['historical_support']==support and not row['adopted']
        close([row['mean_mse_reduction'],row['mean_logloss_reduction']],[g.mse_reduction.mean(),g.logloss_reduction.mean()]);assert row['selected']==g.selected.sum() and row['shared_selected']==g.shared_selected.sum()
    c=pd.read_parquet(out/'coverage.parquet').groupby(['era','level']).agg(catalogue_union_rows=('date','size'),original_panel_rows=('observed_panel_row','sum'),baseline_ready=('baseline_ready','sum'),main80=('main80','sum'),strict100=('strict100','sum')).reset_index();pd.testing.assert_frame_equal(pd.read_csv(out/'coverage_summary.csv'),c)
    result=dict(status='PASS',paired_rows=len(p),dates=len(d),groups=len(s),annual_rows=len(annual),support_groups=int(s.historical_support.sum()),positive_family_groups=int(s.family60_low.gt(0).sum()),negative_family_groups=int(s.family60_high.lt(0).sum()),adopted=False);js(out/'metric_verification.json',result);print(result)

if __name__=='__main__':run()
