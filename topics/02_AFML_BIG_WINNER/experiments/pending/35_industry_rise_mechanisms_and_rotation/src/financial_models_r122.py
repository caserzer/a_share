"""Matched fixed ridge comparison of financial change, with date-level uncertainty."""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from scipy.stats import norm
from common import *
from financial_folds_r121 import BASE
from versioned_observations import digest_json
K=KEY+['date'];G=['era','level','clock','cohort','horizon']
def run():
    out=ROOT/'outputs/r122';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r121/joined_panel.parquet',ROOT/'outputs/r121/fold_ledger.csv']
    p=pd.read_parquet(paths[0]);folds=pd.read_csv(paths[1]);eligible=folds[folds.status.eq('eligible')]
    assert len(eligible)==7 and eligible.task.eq('return').all()
    models=[];preds=[]
    for fold in eligible.to_dict('records'):
        g=p[(p.era==fold['era'])&(p.level==fold['level'])&(p.clock==fold['clock'])&p[fold['cohort']]].copy()
        cols=BASE+['mean_change'];ranks=g.groupby('date')[cols].transform(centered_rank)
        h=fold['horizon'];year=fold['year'];cut=pd.Timestamp(year,1,1)
        tr=g[g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)]
        assert digest_json(tr[K].astype(str).to_dict('records'))==fold['fit_identity_sha256'] and digest_json(te[K].astype(str).to_dict('records'))==fold['test_identity_sha256']
        f=te[K+['clock','entry_date',f'maturity{h}',f'excess{h}','mean_change']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'y'}).copy();f['cohort']=fold['cohort'];f['horizon']=h;f['year']=year
        for method,columns in [('controls',BASE),('with_financial',cols)]:
            scaler=StandardScaler().fit(ranks.loc[tr.index,columns]);x=scaler.transform(ranks.loc[tr.index,columns]);xt=scaler.transform(ranks.loc[te.index,columns])
            weights=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size'))
            model=Ridge(alpha=10).fit(x,tr[f'excess{h}'],sample_weight=weights);f[method]=model.predict(xt)
            models.append(dict(**{k:fold[k] for k in ['era','level','clock','cohort','horizon','year','fit_identity_sha256','test_identity_sha256']},method=method,columns=columns,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_),n_fit=len(tr),n_test=len(te)))
        preds.append(f)
    pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'paired_predictions.parquet',index=False);js(out/'model_parameters.json',models)
    rows=[]
    for key,g in pred.groupby(G+['date']):
        v=g[g.y.notna()];a=b=np.nan
        if len(v):a=((v.controls-v.y)**2).mean();b=((v.with_financial-v.y)**2).mean()
        rows.append(dict(zip(G+['date'],key),metric='mse_reduction',signals=len(g),known=len(v),baseline=a,added=b,delta=a-b))
        a=b=np.nan
        if len(v)>=20 and v.y.nunique()>1 and v.controls.nunique()>1 and v.with_financial.nunique()>1:a=v.controls.corr(v.y,method='spearman');b=v.with_financial.corr(v.y,method='spearman')
        rows.append(dict(zip(G+['date'],key),metric='ic_increment',signals=len(g),known=len(v),baseline=a,added=b,delta=b-a))
    d=pd.DataFrame(rows);d['year']=d.date.dt.year;d.to_csv(out/'date_metrics.csv',index=False)
    d.groupby(G+['metric','year']).agg(months=('delta','count'),mean_delta=('delta','mean')).reset_index().to_csv(out/'annual_metrics.csv',index=False)
    rows=[]
    for key,g in d.groupby(G+['metric']):
        q=g[g.delta.notna()];x=q.delta.to_numpy();n=len(x);se=lo=hi=flo=fhi=np.nan
        lag=3 if key[-2]==20 else 6
        if n>=2:
            u=x-x.mean();months=q.date.dt.to_period('M').astype('int64').to_numpy();v=u@u
            for step in range(1,lag+1):v+=2*(1-step/(lag+1))*float((u[:,None]*u[None,:])[(months[:,None]-months[None,:])==step].sum())
            se=np.sqrt(max(0,v))/n;lo=x.mean()-1.96*se;hi=x.mean()+1.96*se;z=norm.ppf(1-.05/16);flo=x.mean()-z*se;fhi=x.mean()+z*se
        yr=q.groupby('year').delta.mean()
        rows.append(dict(zip(G+['metric'],key),months=n,mean_delta=q.delta.mean(),standard_error=se,low95=lo,high95=hi,family8_low=flo,family8_high=fhi,years=len(yr),positive_years=int(yr.gt(0).sum()),hac_lag=lag))
    summary=pd.DataFrame(rows);summary['historical_support']=False
    for i,row in summary[summary.metric.eq('mse_reduction')].iterrows():
        ic=summary[(summary.clock==row.clock)&(summary.horizon==row.horizon)&summary.metric.eq('ic_increment')].iloc[0]
        summary.loc[i,'historical_support']=row.horizon==20 and row.months>=24 and row.years>=3 and row.positive_years==row.years and row.family8_low>0 and np.isfinite(ic.mean_delta) and ic.mean_delta>=0
    summary.to_csv(out/'summary.csv',index=False)
    paths +=[Path(__file__),ROOT/'protocols/r122.json',ROOT/'src/common.py',ROOT/'src/financial_folds_r121.py',ROOT/'src/versioned_observations.py']
    names=['paired_predictions.parquet','model_parameters.json','date_metrics.csv','annual_metrics.csv','summary.csv']
    js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},outputs={n:sha(out/n) for n in names},models=len(models),paired_rows=len(pred),known=int(pred.y.notna().sum()),unknown=int(pred.y.isna().sum()),historical_support_groups=int(summary.historical_support.sum()),adopted=False))
    print(summary.to_string(index=False));print('paired',len(pred),'known',pred.y.notna().sum())
if __name__=='__main__':run()
