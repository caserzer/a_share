"""Independent paired metrics, annual aggregation and calendar covariance."""
import pandas as pd
from scipy.stats import rankdata,norm
from common import *
G=['era','level','cohort','task','horizon']

def close(a,b):np.testing.assert_allclose(a,b,atol=1e-12,rtol=1e-10,equal_nan=True)

def run():
    out=ROOT/'outputs/r106';r=json.loads((out/'evaluation_receipt.json').read_text())
    assert r['prediction_sha256']==sha(out/'paired_predictions.parquet') and r['code_sha256']==sha(ROOT/'src/evaluate_precision_r106.py')
    for p,h in r['outputs'].items():assert sha(out/p)==h
    p=pd.read_parquet(out/'paired_predictions.parquet');d=pd.read_csv(out/'paired_date_metrics.csv',parse_dates=['date']);a=pd.read_csv(out/'annual_metrics.csv');s=pd.read_csv(out/'summary.csv')
    indexed=d.set_index(G+['date']);assert indexed.index.is_unique
    assert set(indexed.index)==set(p.groupby(G+['date']).groups)
    for key,g in p.groupby(G+['date']):
        row=indexed.loc[key];v=g[g.y.notna()];n=len(v);k=max(1,int(np.ceil(len(g)/5)))
        old={x.industry_code for x in sorted(g.itertuples(),key=lambda x:(-x.prediction,x.industry_code))[:k]}
        new={x.industry_code for x in sorted(g.itertuples(),key=lambda x:(-x.unique_prediction,x.industry_code))[:k]}
        assert (row.n_signal,row.n_mature,row.selected,row.shared_selected)==(len(g),n,k,len(old&new))
        if key[3]=='return':
            bo=bn=np.nan
            if n>=20 and v.prediction.nunique()>1 and v.unique_prediction.nunique()>1:
                bo=np.corrcoef(rankdata(v.prediction),rankdata(v.y))[0,1];bn=np.corrcoef(rankdata(v.unique_prediction),rankdata(v.y))[0,1]
            close([row.baseline_utility,row.unique_utility,row.delta],[bo,bn,bn-bo]);assert pd.isna(row.logloss_reduction)
        elif n:
            y=v.y.to_numpy();bo=-np.average((v.prediction-y)**2);bn=-np.average((v.unique_prediction-y)**2)
            def loss(z):
                z=np.clip(np.asarray(z),1e-15,1-1e-15);return -np.sum(np.where(y==1,np.log(z),np.log1p(-z)))/n
            close([row.baseline_utility,row.unique_utility,row.delta,row.logloss_reduction,row.frozen_calibration_brier_reduction],[bo,bn,bn-bo,loss(v.prediction)-loss(v.unique_prediction),-bo-np.mean((v.unique_frozen_calibration_prediction-y)**2)])
        else:assert pd.isna(row.delta)
    assert len(s)==d.groupby(G).ngroups and len(a)==d.assign(year=d.date.dt.year).groupby(G+['year']).ngroups
    for row in a.to_dict('records'):
        g=d[d.date.dt.year.eq(row['year'])]
        for k in G:g=g[g[k].eq(row[k])]
        assert row['months']==g.delta.notna().sum();close([row['mean_delta'],row['mean_logloss_reduction']],[g.delta.mean(),g.logloss_reduction.mean()])
        assert (row['selected'],row['shared_selected'])==(g.selected.sum(),g.shared_selected.sum())
    for row in s.to_dict('records'):
        g=d
        for k in G:g=g[g[k].eq(row[k])]
        v=g.dropna(subset=['delta']);x=v.delta.to_numpy();u=x-x.mean();months=v.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if row['horizon']==20 else 6
        kernel=np.maximum(1-np.abs(months[:,None]-months[None,:])/(lag+1),0);se=np.sqrt(max(float(u@kernel@u),0))/len(x)
        z=norm.ppf(1-.05/120)
        close([row['mean_delta'],row['standard_error'],row['low95'],row['high95'],row['family60_low'],row['family60_high']],[x.mean(),se,x.mean()-1.96*se,x.mean()+1.96*se,x.mean()-z*se,x.mean()+z*se])
        annual=v.groupby(v.date.dt.year).delta.mean();assert (row['positive_years'],row['evaluated_years'],row['months'])==(annual.gt(0).sum(),len(annual),len(x))
        close([row['mean_logloss_reduction'],row['mean_frozen_calibration_brier_reduction']],[g.logloss_reduction.mean(),g.frozen_calibration_brier_reduction.mean()])
        assert row['selected']==g.selected.sum() and row['shared_selected']==g.shared_selected.sum()
    result=dict(status='PASS',date_rows=len(d),groups=len(s),annual_rows=len(a),positive_family_intervals=int(s.family60_low.gt(0).sum()),negative_family_intervals=int(s.family60_high.lt(0).sum()),selected=int(d.selected.sum()),shared_selected=int(d.shared_selected.sum()),adopted=False)
    js(out/'metric_verification.json',result);print(result)

if __name__=='__main__':run()
