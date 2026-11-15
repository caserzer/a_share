"""Fixed delayed catch-up target: matched rolling ridge increment."""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from scipy.stats import norm
from common import *
from leader_models_r109 import BASE,ALL
K=KEY+['date'];G=['era','level','cohort']
def run():
    out=ROOT/'outputs/r111';out.mkdir(exist_ok=True)
    paths=[ROOT/'outputs/r109/joined_panel.parquet',ROOT/'outputs/r110/industry_outcomes.parquet']
    p=pd.read_parquet(paths[0]);z=pd.read_parquet(paths[1])[K+['catchup','maturity_date','entry_expected','future_status']]
    p=p.merge(z,on=K,how='left',validate='one_to_one');p.to_parquet(out/'joined_panel.parquet',index=False)
    preds=[];models=[];folds=[]
    for (era,level),base in p.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]];rank=g.groupby('date')[ALL].transform(centered_rank)
        for year in range(2020,2027):
          cutoff=pd.Timestamp(year,1,1);tr=g[(g.date<cutoff)&(g.maturity_date<cutoff)&g.catchup.notna()];te=g[g.date.dt.year.eq(year)]
          if not len(te):continue
          reason='insufficient_train_months_or_rows' if tr.date.nunique()<18 or len(tr)<300 else None
          rec=dict(era=era,level=level,cohort=cohort,year=year,n_train=len(tr),train_months=tr.date.nunique(),n_test=len(te),known_test=int(te.catchup.notna().sum()),fit_max_maturity=tr.maturity_date.max(),status='skipped' if reason else 'fit',reason=reason)
          folds.append(rec)
          if reason:continue
          f=te[K+['catchup','maturity_date','entry_expected','future_status']].copy();f['cohort']=cohort;f['year']=year
          for method,cols in [('controls',BASE),('with_leader',ALL)]:
            scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols]);counts=tr.groupby('date').date.transform('size');w=len(tr)/(tr.date.nunique()*counts)
            model=Ridge(alpha=10).fit(x,tr.catchup,sample_weight=w);f[method]=model.predict(xt)
            models.append(dict(rec,method=method,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
          preds.append(f)
    pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'paired_predictions.parquet',index=False);js(out/'model_parameters.json',models);pd.DataFrame(folds).to_csv(out/'fold_ledger.csv',index=False)
    rows=[]
    for key,g in pred.groupby(G+['date']):
        v=g[g.catchup.notna()];a=b=delta=np.nan
        if len(v):a=((v.controls-v.catchup)**2).mean();b=((v.with_leader-v.catchup)**2).mean();delta=a-b
        rows.append(dict(zip(G+['date'],key),metric='mse_reduction',signals=len(g),known=len(v),baseline=a,added=b,delta=delta))
        a=b=delta=np.nan
        if len(v)>=20 and v.catchup.nunique()>1 and v.controls.nunique()>1 and v.with_leader.nunique()>1:a=v.controls.corr(v.catchup,method='spearman');b=v.with_leader.corr(v.catchup,method='spearman');delta=b-a
        rows.append(dict(zip(G+['date'],key),metric='ic_increment',signals=len(g),known=len(v),baseline=a,added=b,delta=delta))
    d=pd.DataFrame(rows);d['year']=d.date.dt.year;d.to_csv(out/'date_metrics.csv',index=False)
    annual=d.groupby(G+['metric','year']).agg(months=('delta','count'),mean_delta=('delta','mean')).reset_index();annual.to_csv(out/'annual_metrics.csv',index=False)
    rows=[]
    for key,g in d.groupby(G+['metric']):
        q=g[g.delta.notna()];x=q.delta.to_numpy();n=len(x);se=lo=hi=flo=fhi=np.nan
        if n>=2:
            u=x-x.mean();months=q.date.dt.to_period('M').astype('int64').to_numpy();v=u@u
            for step in range(1,4):v+=2*(1-step/4)*float((u[:,None]*u[None,:])[(months[:,None]-months[None,:])==step].sum())
            se=np.sqrt(max(0,v))/n;lo=x.mean()-1.96*se;hi=x.mean()+1.96*se;z=norm.ppf(1-.05/40);flo=x.mean()-z*se;fhi=x.mean()+z*se
        yr=q.groupby('year').delta.mean();rows.append(dict(zip(G+['metric'],key),months=n,mean_delta=q.delta.mean(),standard_error=se,low95=lo,high95=hi,family20_low=flo,family20_high=fhi,years=len(yr),positive_years=int(yr.gt(0).sum())))
    summary=pd.DataFrame(rows);summary['historical_support']=False
    for i,row in summary[summary.metric.eq('mse_reduction')].iterrows():
        ic=summary[(summary.era==row.era)&(summary.level==row.level)&(summary.cohort==row.cohort)&summary.metric.eq('ic_increment')].iloc[0]
        summary.loc[i,'historical_support']=row.cohort=='main80' and row.months>=24 and row.years>=3 and row.positive_years==row.years and row.family20_low>0 and ic.mean_delta>=0
    summary.to_csv(out/'summary.csv',index=False)
    paths +=[Path(__file__),ROOT/'protocols/r111.json',ROOT/'src/common.py',ROOT/'src/leader_models_r109.py']
    js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},outputs={x.name:sha(x) for x in out.iterdir() if x.suffix in ['.parquet','.csv'] or x.name=='model_parameters.json'},models=len(models),predictions=len(pred),adopted=False))
    print(summary.to_string(index=False))
if __name__=='__main__':run()
