"""Independent common-population, ridge, and paired uncertainty verification."""
import pandas as pd
from scipy.stats import norm
from common import *
from versioned_observations import digest_json
K=KEY+['date'];G=['era','level','cohort','horizon']
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63']
def run():
    out=ROOT/'outputs/r123';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    s=pd.read_parquet(ROOT/'outputs/r121/joined_panel.parquet');a=s[s.clock.eq('notice')].reset_index(drop=True);b=s[s.clock.eq('update')].reset_index(drop=True)
    shared=K+BASE+['price_ready','entry_date','excess20','excess60','maturity20','maturity60'];pd.testing.assert_frame_equal(a[shared],b[shared])
    q=pd.read_parquet(out/'common_panel.parquet');pd.testing.assert_frame_equal(q[shared],a[shared])
    for clock,z in [('notice',a),('update',b)]:
        for c in ['mean_change','main80','strict100','known','coverage']:pd.testing.assert_series_equal(q[clock+'_'+c],z[c],check_names=False)
    assert q.main80.equals(a.main80&b.main80) and q.strict100.equals(a.strict100&b.strict100)
    cov=q.groupby(['era','level']).agg(rows=('date','size'),notice=('notice_main80','sum'),update=('update_main80','sum'),common=('main80','sum'),strict=('strict100','sum')).reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(out/'coverage.csv'),cov,check_dtype=False)
    models=json.loads((out/'model_parameters.json').read_text());folds=[];predictions=[]
    for (era,level),base in q.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        g=base[base[cohort]];cols=BASE+['notice_mean_change','update_mean_change']
        ranks=(g.groupby('date')[cols].rank(method='average')-.5).div(g.groupby('date').date.transform('size'),axis=0)-.5
        for h in [20,60]:
          for year in range(2020,2027):
            cutoff=pd.Timestamp(year,1,1);tr=g[(g.date<cutoff)&(g[f'maturity{h}']<cutoff)&g[f'excess{h}'].notna()];te=g[g.date.dt.year==year]
            reason='no_test_rows' if not len(te) else 'insufficient_train' if len(tr)<300 or tr.date.nunique()<18 else 'eligible'
            record=dict(era=era,level=level,cohort=cohort,horizon=h,year=year,reason=reason,n_fit=len(tr),fit_months=tr.date.nunique(),n_test=len(te),fit_max_maturity=tr[f'maturity{h}'].max(),fit_identity=digest_json(tr[K].astype(str).to_dict('records')),test_identity=digest_json(te[K].astype(str).to_dict('records')));folds.append(record)
            mm=[m for m in models if all(m[k]==record[k] for k in G+['year'])]
            if reason!='eligible':assert not mm;continue
            assert len(mm)==3 and {m['method'] for m in mm}=={'controls','notice_model','update_model'}
            f=te[K+['entry_date',f'maturity{h}',f'excess{h}']].rename(columns={f'maturity{h}':'maturity',f'excess{h}':'y'}).copy();f['cohort']=cohort;f['horizon']=h;f['year']=year
            for m in mm:
                for k,v in record.items():assert m[k]==str(v) if isinstance(v,pd.Timestamp) else m[k]==v
                columns=BASE+([] if m['method']=='controls' else [m['method'].replace('_model','_mean_change')]);assert m['columns']==columns
                x=ranks.loc[tr.index,columns].to_numpy();xt=ranks.loc[te.index,columns].to_numpy();mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1
                np.testing.assert_allclose(mean,m['mean'],atol=1e-14);np.testing.assert_allclose(scale,m['scale'],atol=1e-14)
                x=np.column_stack([np.ones(len(x)),(x-mean)/scale]);xt=np.column_stack([np.ones(len(xt)),(xt-mean)/scale])
                weights=len(tr)/(tr.date.nunique()*tr.groupby('date').date.transform('size').to_numpy())
                beta=np.linalg.solve(x.T@(weights[:,None]*x)+np.diag([0]+[10]*len(columns)),x.T@(weights*tr[f'excess{h}'].to_numpy()))
                np.testing.assert_allclose(beta,[m['intercept']]+m['coef'],atol=1e-12);f[m['method']]=xt@beta
            predictions.append(f)
    ledger=pd.DataFrame(folds);pd.testing.assert_frame_equal(pd.read_csv(out/'fold_ledger.csv',parse_dates=['fit_max_maturity']),ledger,check_dtype=False)
    pred=pd.read_parquet(out/'predictions.parquet');exp=pd.concat(predictions,ignore_index=True)
    methods=['controls','notice_model','update_model']
    pd.testing.assert_frame_equal(pred.drop(columns=methods),exp.drop(columns=methods));np.testing.assert_allclose(pred[methods],exp[methods],atol=1e-12)
    maxerr=float(np.max(abs(pred[methods].to_numpy()-exp[methods].to_numpy())))
    contrasts={'notice_vs_controls':('controls','notice_model'),'update_vs_controls':('controls','update_model'),'update_vs_notice':('notice_model','update_model')};rows=[]
    for key,g in pred.groupby(G+['date']):
      v=g.dropna(subset=['y'])
      for contrast,(old,new) in contrasts.items():
        x=float(np.square(v[old]-v.y).mean()) if len(v) else np.nan;y=float(np.square(v[new]-v.y).mean()) if len(v) else np.nan
        rows.append(dict(zip(G+['date'],key),contrast=contrast,metric='mse_reduction',signals=len(g),known=len(v),baseline=x,added=y,delta=x-y))
        x=y=np.nan
        if len(v)>=20 and min(v[old].nunique(),v[new].nunique(),v.y.nunique())>1:x=v[old].rank().corr(v.y.rank());y=v[new].rank().corr(v.y.rank())
        rows.append(dict(zip(G+['date'],key),contrast=contrast,metric='ic_increment',signals=len(g),known=len(v),baseline=x,added=y,delta=y-x))
    d=pd.DataFrame(rows);d['year']=d.date.dt.year
    pd.testing.assert_frame_equal(pd.read_csv(out/'date_metrics.csv',parse_dates=['date']),d,check_dtype=False,atol=1e-12)
    annual=d.groupby(G+['contrast','metric','year']).agg(months=('delta','count'),mean_delta=('delta','mean')).reset_index()
    pd.testing.assert_frame_equal(pd.read_csv(out/'annual.csv'),annual,check_dtype=False,atol=1e-12)
    rows=[]
    for key,g in d.groupby(G+['contrast','metric']):
        v=g.dropna(subset=['delta']);n=len(v);mean=v.delta.mean();lag=3 if key[3]==20 else 6;se=lo=hi=flo=fhi=np.nan
        if n>=2:
            residual={date.to_period('M').ordinal:float(value-mean) for date,value in zip(v.date,v.delta)}
            variance=sum(x*x for x in residual.values())
            for k in range(1,lag+1):variance+=2*(1-k/(lag+1))*sum(x*residual.get(t-k,0) for t,x in residual.items())
            se=np.sqrt(max(variance,0))/n;lo=mean-1.96*se;hi=mean+1.96*se;z=norm.isf(.05/24);flo=mean-z*se;fhi=mean+z*se
        yr=v.groupby('year').delta.mean();rows.append(dict(zip(G+['contrast','metric'],key),months=n,mean_delta=mean,se=se,low95=lo,high95=hi,family12_low=flo,family12_high=fhi,years=len(yr),positive_years=int(yr.gt(0).sum()),historical_support=False))
    summary=pd.DataFrame(rows)
    for i,x in summary[summary.metric.eq('mse_reduction')].iterrows():
        ic=summary[(summary.horizon==x.horizon)&(summary.contrast==x.contrast)&summary.metric.eq('ic_increment')].iloc[0]
        summary.loc[i,'historical_support']=x.horizon==20 and x.months>=24 and x.years>=3 and x.positive_years==x.years and x.family12_low>0 and np.isfinite(ic.mean_delta) and ic.mean_delta>=0
    pd.testing.assert_frame_equal(pd.read_csv(out/'summary.csv'),summary,check_dtype=False,atol=1e-12)
    previous_path=ROOT/'outputs/r122/paired_predictions.parquet'
    previous=pd.read_parquet(previous_path);previous=previous[previous.clock.eq('update')]
    compare=pred.merge(previous,on=K+['cohort','horizon','year'],how='outer',suffixes=('_common','_previous'),indicator=True,validate='one_to_one')
    assert compare._merge.eq('both').all()
    np.testing.assert_allclose(compare.controls_common,compare.controls_previous,atol=1e-12)
    np.testing.assert_allclose(compare.update_model,compare.with_financial,atol=1e-12)
    js(out/'verification.json',dict(previous_update_predictions_sha256=sha(previous_path),previous_update_predictions_reproduced=True,status='PASS',folds=len(folds),models=len(models),predictions=len(pred),known=int(pred.y.notna().sum()),unknown=int(pred.y.isna().sum()),max_prediction_error=maxerr,date_rows=len(d),support_groups=int(summary.historical_support.sum()),strict_PIT=False))
    print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
