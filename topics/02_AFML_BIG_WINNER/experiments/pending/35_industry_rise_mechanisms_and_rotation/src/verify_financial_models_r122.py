"""Independent normal-equation predictions and calendar-HAC metric reconstruction."""
import pandas as pd
from scipy.stats import norm
from common import *
from versioned_observations import digest_json
K=KEY+['date'];G=['era','level','clock','cohort','horizon']
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']
def run():
    out=ROOT/'outputs/r122';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    panel=pd.read_parquet(ROOT/'outputs/r121/joined_panel.parquet');folds=pd.read_csv(ROOT/'outputs/r121/fold_ledger.csv');folds=folds[folds.status.eq('eligible')]
    models=json.loads((out/'model_parameters.json').read_text());assert len(models)==2*len(folds)==14
    pred=pd.read_parquet(out/'paired_predictions.parquet');expected=[];errors=[]
    for f in folds.to_dict('records'):
        g=panel[(panel.era==f['era'])&(panel.level==f['level'])&(panel.clock==f['clock'])&panel[f['cohort']]]
        cols=BASE+['mean_change'];r=g.groupby('date')[cols].rank(method='average')
        r=(r-.5).div(g.groupby('date').date.transform('size'),axis=0)-.5
        h=f['horizon'];cut=pd.Timestamp(f['year'],1,1)
        tr=g[g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(f['year'])]
        z=te[K+['clock','entry_date',f'maturity{h}',f'excess{h}','mean_change']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'y'}).copy();z['cohort']=f['cohort'];z['horizon']=h;z['year']=f['year']
        for method,columns in [('controls',BASE),('with_financial',cols)]:
            matches=[m for m in models if all(m[k]==f[k] for k in G+['year']) and m['method']==method];assert len(matches)==1;m=matches[0]
            assert m['columns']==columns and m['n_fit']==len(tr) and m['n_test']==len(te)
            assert m['fit_identity_sha256']==digest_json(tr[K].astype(str).to_dict('records')) and m['test_identity_sha256']==digest_json(te[K].astype(str).to_dict('records'))
            x=r.loc[tr.index,columns].to_numpy();xt=r.loc[te.index,columns].to_numpy()
            mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1
            np.testing.assert_allclose(m['mean'],mean,atol=1e-14);np.testing.assert_allclose(m['scale'],scale,atol=1e-14)
            x=(x-mean)/scale;xt=(xt-mean)/scale;w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy())
            design=np.column_stack([np.ones(len(x)),x]);pen=np.diag([0]+[10]*len(columns))
            beta=np.linalg.solve(design.T@(w[:,None]*design)+pen,design.T@(w*tr[f'excess{h}'].to_numpy()))
            np.testing.assert_allclose([m['intercept']]+m['coef'],beta,atol=1e-12,rtol=1e-10)
            z[method]=np.column_stack([np.ones(len(xt)),xt])@beta
        expected.append(z)
    e=pd.concat(expected,ignore_index=True)
    pd.testing.assert_frame_equal(pred.drop(columns=['controls','with_financial']),e.drop(columns=['controls','with_financial']))
    np.testing.assert_allclose(pred[['controls','with_financial']],e[['controls','with_financial']],atol=1e-12,rtol=1e-10)
    error=float(np.max(np.abs(pred[['controls','with_financial']].to_numpy()-e[['controls','with_financial']].to_numpy())))
    dates=[]
    for key,g in pred.groupby(G+['date']):
        q=g[g.y.notna()]
        a=np.mean(np.square(q.controls-q.y)) if len(q) else np.nan;b=np.mean(np.square(q.with_financial-q.y)) if len(q) else np.nan
        dates.append(dict(zip(G+['date'],key),metric='mse_reduction',signals=len(g),known=len(q),baseline=a,added=b,delta=a-b))
        a=b=np.nan
        if len(q)>=20 and min(q.y.nunique(),q.controls.nunique(),q.with_financial.nunique())>1:
            target=q.y.rank();a=q.controls.rank().corr(target);b=q.with_financial.rank().corr(target)
        dates.append(dict(zip(G+['date'],key),metric='ic_increment',signals=len(g),known=len(q),baseline=a,added=b,delta=b-a))
    d=pd.DataFrame(dates);d['year']=d.date.dt.year
    pd.testing.assert_frame_equal(pd.read_csv(out/'date_metrics.csv',parse_dates=['date']),d,check_dtype=False,atol=1e-12)
    annual=d.groupby(G+['metric','year']).agg(months=('delta','count'),mean_delta=('delta','mean')).reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(out/'annual_metrics.csv'),annual,check_dtype=False,atol=1e-12)
    records=[]
    for key,g in d.groupby(G+['metric']):
        q=g.dropna(subset=['delta']);n=len(q);avg=q.delta.mean();lag=3 if key[-2]==20 else 6
        se=lo=hi=flo=fhi=np.nan
        if n>=2:
            residual={date.to_period('M').ordinal:float(value-avg) for date,value in zip(q.date,q.delta)}
            variance=sum(v*v for v in residual.values())
            for k in range(1,lag+1):variance+=2*(1-k/(lag+1))*sum(v*residual.get(month-k,0) for month,v in residual.items())
            se=np.sqrt(max(variance,0))/n;lo=avg-1.96*se;hi=avg+1.96*se;critical=norm.isf(.05/(2*8));flo=avg-critical*se;fhi=avg+critical*se
        years=q.groupby('year').delta.mean()
        records.append(dict(zip(G+['metric'],key),months=n,mean_delta=avg,standard_error=se,low95=lo,high95=hi,family8_low=flo,family8_high=fhi,years=len(years),positive_years=int((years>0).sum()),hac_lag=lag,historical_support=False))
    summary=pd.DataFrame(records)
    for i,x in summary[summary.metric.eq('mse_reduction')].iterrows():
        ic=summary[(summary.clock==x.clock)&(summary.horizon==x.horizon)&summary.metric.eq('ic_increment')].iloc[0]
        summary.loc[i,'historical_support']=x.horizon==20 and x.months>=24 and x.years>=3 and x.positive_years==x.years and x.family8_low>0 and np.isfinite(ic.mean_delta) and ic.mean_delta>=0
    pd.testing.assert_frame_equal(pd.read_csv(out/'summary.csv'),summary,check_dtype=False,atol=1e-12)
    assert rec['paired_rows']==len(pred) and rec['known']==int(pred.y.notna().sum()) and rec['unknown']==int(pred.y.isna().sum())
    js(out/'verification.json',dict(status='PASS',models=len(models),eligible_folds=len(folds),paired_rows=len(pred),known=int(pred.y.notna().sum()),unknown=int(pred.y.isna().sum()),max_normal_equation_prediction_error=error,date_metric_rows=len(d),support_groups=int(summary.historical_support.sum()),strict_PIT=False,adopted=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
