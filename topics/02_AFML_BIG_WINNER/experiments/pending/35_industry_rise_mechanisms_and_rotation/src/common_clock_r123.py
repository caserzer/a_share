"""Three fixed ridge models on identical dual-clock industry-date populations."""
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from scipy.stats import norm
from common import *
from financial_folds_r121 import BASE
from versioned_observations import digest_json
K=KEY+['date'];G=['era','level','cohort','horizon']
CONTRASTS={'notice_vs_controls':('controls','notice_model'),'update_vs_controls':('controls','update_model'),'update_vs_notice':('notice_model','update_model')}
def run():
    out=ROOT/'outputs/r123';out.mkdir(exist_ok=True);source=ROOT/'outputs/r121/joined_panel.parquet';p=pd.read_parquet(source)
    a=p[p.clock.eq('notice')].reset_index(drop=True);b=p[p.clock.eq('update')].reset_index(drop=True)
    shared=K+BASE+['price_ready','entry_date','excess20','excess60','maturity20','maturity60']
    pd.testing.assert_frame_equal(a[shared],b[shared])
    q=a[shared].copy()
    for clock,z in [('notice',a),('update',b)]:
        for c in ['mean_change','main80','strict100','known','coverage']:q[clock+'_'+c]=z[c]
    q['main80']=a.main80&b.main80;q['strict100']=a.strict100&b.strict100
    q.to_parquet(out/'common_panel.parquet',index=False)
    q.groupby(['era','level']).agg(rows=('date','size'),notice=('notice_main80','sum'),update=('update_main80','sum'),common=('main80','sum'),strict=('strict100','sum')).reset_index().to_csv(out/'coverage.csv',index=False)
    folds=[];models=[];preds=[]
    for (era,level),base in q.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]];rank=g[BASE+['notice_mean_change','update_mean_change']].copy() if g.empty else g.groupby('date')[BASE+['notice_mean_change','update_mean_change']].transform(centered_rank)
        for h in [20,60]:
          for year in range(2020,2027):
            cut=pd.Timestamp(year,1,1);tr=g[g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)]
            reason='no_test_rows' if te.empty else 'insufficient_train' if len(tr)<300 or tr.date.nunique()<18 else 'eligible'
            rec=dict(era=era,level=level,cohort=cohort,horizon=h,year=year,reason=reason,n_fit=len(tr),fit_months=tr.date.nunique(),n_test=len(te),fit_max_maturity=tr[f'maturity{h}'].max(),fit_identity=digest_json(tr[K].astype(str).to_dict('records')),test_identity=digest_json(te[K].astype(str).to_dict('records')))
            folds.append(rec)
            if reason!='eligible':continue
            f=te[K+['entry_date',f'maturity{h}',f'excess{h}']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'y'}).copy();f['cohort']=cohort;f['horizon']=h;f['year']=year
            for name,cols in [('controls',BASE),('notice_model',BASE+['notice_mean_change']),('update_model',BASE+['update_mean_change'])]:
                scaler=StandardScaler().fit(rank.loc[tr.index,cols]);x=scaler.transform(rank.loc[tr.index,cols]);xt=scaler.transform(rank.loc[te.index,cols]);w=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size'))
                model=Ridge(alpha=10).fit(x,tr[f'excess{h}'],sample_weight=w);f[name]=model.predict(xt)
                models.append(dict(**rec,method=name,columns=cols,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
            preds.append(f)
    ledger=pd.DataFrame(folds);assert len(ledger)==140;ledger.to_csv(out/'fold_ledger.csv',index=False);js(out/'model_parameters.json',models)
    pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False)
    rows=[]
    for key,g in pred.groupby(G+['date']):
      v=g[g.y.notna()]
      for contrast,(old,new) in CONTRASTS.items():
        x=y=np.nan
        if len(v):x=((v[old]-v.y)**2).mean();y=((v[new]-v.y)**2).mean()
        rows.append(dict(zip(G+['date'],key),contrast=contrast,metric='mse_reduction',signals=len(g),known=len(v),baseline=x,added=y,delta=x-y))
        x=y=np.nan
        if len(v)>=20 and min(v[old].nunique(),v[new].nunique(),v.y.nunique())>1:x=v[old].corr(v.y,method='spearman');y=v[new].corr(v.y,method='spearman')
        rows.append(dict(zip(G+['date'],key),contrast=contrast,metric='ic_increment',signals=len(g),known=len(v),baseline=x,added=y,delta=y-x))
    d=pd.DataFrame(rows);d['year']=d.date.dt.year;d.to_csv(out/'date_metrics.csv',index=False)
    d.groupby(G+['contrast','metric','year']).agg(months=('delta','count'),mean_delta=('delta','mean')).reset_index().to_csv(out/'annual.csv',index=False)
    rows=[]
    for key,g in d.groupby(G+['contrast','metric']):
        v=g.dropna(subset=['delta']);n=len(v);mean=v.delta.mean();lag=3 if key[3]==20 else 6;se=lo=hi=flo=fhi=np.nan
        if n>=2:
            u=v.delta.to_numpy()-mean;months=v.date.dt.to_period('M').astype('int64').to_numpy();variance=u@u
            for step in range(1,lag+1):variance+=2*(1-step/(lag+1))*float((u[:,None]*u[None,:])[(months[:,None]-months[None,:])==step].sum())
            se=np.sqrt(max(0,variance))/n;lo=mean-1.96*se;hi=mean+1.96*se;z=norm.ppf(1-.05/24);flo=mean-z*se;fhi=mean+z*se
        yr=v.groupby('year').delta.mean();rows.append(dict(zip(G+['contrast','metric'],key),months=n,mean_delta=mean,se=se,low95=lo,high95=hi,family12_low=flo,family12_high=fhi,years=len(yr),positive_years=int(yr.gt(0).sum())))
    summary=pd.DataFrame(rows);summary['historical_support']=False
    for i,x in summary[summary.metric.eq('mse_reduction')].iterrows():
        ic=summary[(summary.horizon==x.horizon)&(summary.contrast==x.contrast)&summary.metric.eq('ic_increment')].iloc[0]
        summary.loc[i,'historical_support']=x.horizon==20 and x.months>=24 and x.years>=3 and x.positive_years==x.years and x.family12_low>0 and np.isfinite(ic.mean_delta) and ic.mean_delta>=0
    summary.to_csv(out/'summary.csv',index=False)
    reads=[source,Path(__file__),ROOT/'protocols/r123.json',ROOT/'src/common.py',ROOT/'src/financial_folds_r121.py',ROOT/'src/versioned_observations.py']
    names=['common_panel.parquet','coverage.csv','fold_ledger.csv','model_parameters.json','predictions.parquet','date_metrics.csv','annual.csv','summary.csv']
    js(out/'receipt.json',dict(reads={str(x):sha(x) for x in reads},outputs={n:sha(out/n) for n in names},folds=len(folds),eligible=int(ledger.reason.eq('eligible').sum()),models=len(models),predictions=len(pred),known=int(pred.y.notna().sum()),unknown=int(pred.y.isna().sum()),adopted=False))
    print(ledger[ledger.reason.eq('eligible')].to_string(index=False));print(summary.to_string(index=False))
if __name__=='__main__':run()
