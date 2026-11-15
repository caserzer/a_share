"""Independent closed-form weighted ridge, fold, prediction and metric audit."""
import pandas as pd
from scipy.stats import rankdata,norm
from common import *
K=KEY+['date'];G=['era','level','cohort']
BASE=['mom20','mom60','vol20','dd60','log_members','size_control','market_beta126','residual_vol126','breadth21','breadth63'];ALL=BASE+['leader_spread']
def close(a,b):np.testing.assert_allclose(a,b,rtol=1e-9,atol=1e-11,equal_nan=True)
def run():
    out=ROOT/'outputs/r111';rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['reads'].items():assert sha(p)==h,p
    for n,h in rec['outputs'].items():assert sha(out/n)==h,n
    p=pd.read_parquet(out/'joined_panel.parquet');orig=pd.read_parquet(ROOT/'outputs/r109/joined_panel.parquet');pd.testing.assert_frame_equal(p[orig.columns],orig)
    z=pd.read_parquet(ROOT/'outputs/r110/industry_outcomes.parquet').set_index(K).reindex(pd.MultiIndex.from_frame(p[K]))
    for c in ['catchup','maturity_date','entry_expected','future_status']:pd.testing.assert_series_equal(p[c].reset_index(drop=True),z[c].reset_index(drop=True),check_names=False)
    pred=pd.read_parquet(out/'paired_predictions.parquet');assert not pred.duplicated(K+['cohort']).any()
    models=json.loads((out/'model_parameters.json').read_text());folds=pd.read_csv(out/'fold_ledger.csv');nf=nm=nr=0;maxerror=0
    for (era,level),base in p.groupby(['era','level']):
      for cohort in ['main80','strict100']:
        expected=base.price_ready&np.isfinite(base[BASE]).all(axis=1)&np.isfinite(base.leader_spread)
        if cohort=='strict100':expected &= base.strict_complete.eq(True)
        assert expected.equals(base[cohort]);g=base[expected];rank=pd.DataFrame(index=g.index,columns=ALL,dtype=float)
        for date,h in g.groupby('date'):
            for c in ALL:rank.loc[h.index,c]=(rankdata(h[c])-.5)/len(h)-.5
        for year in range(2020,2027):
            cut=pd.Timestamp(year,1,1);tr=g[(g.date<cut)&(g.maturity_date<cut)&np.isfinite(g.catchup)];te=g[g.date.dt.year==year]
            if not len(te):continue
            nf+=1;reason='insufficient_train_months_or_rows' if len(tr)<300 or tr.date.nunique()<18 else None
            f=folds[(folds.era==era)&(folds.level==level)&(folds.cohort==cohort)&(folds.year==year)];assert len(f)==1;f=f.iloc[0]
            assert [f.n_train,f.train_months,f.n_test,f.known_test]==[len(tr),tr.date.nunique(),len(te),te.catchup.notna().sum()]
            pp=pred[(pred.era==era)&(pred.level==level)&(pred.cohort==cohort)&(pred.year==year)]
            mm=[x for x in models if (x['era'],x['level'],x['cohort'],x['year'])==(era,level,cohort,year)]
            if reason:assert f.status=='skipped' and f.reason==reason and not len(pp) and not len(mm);continue
            assert f.status=='fit' and pd.isna(f.reason) and len(mm)==2
            assert pd.Timestamp(f.fit_max_maturity)==tr.maturity_date.max()<cut
            assert set(map(tuple,pp[K].to_numpy()))==set(map(tuple,te[K].to_numpy()))
            tt=te.set_index(K).reindex(pd.MultiIndex.from_frame(pp[K]));nr+=len(pp)
            for c in ['catchup','maturity_date','entry_expected','future_status']:pd.testing.assert_series_equal(pp[c].reset_index(drop=True),tt[c].reset_index(drop=True),check_names=False)
            for par in mm:
                nm+=1;cols=BASE if par['method']=='controls' else ALL;assert par['columns']==cols
                raw=rank.loc[tr.index,cols].to_numpy();mean=raw.mean(axis=0);scale=raw.std(axis=0);scale[scale==0]=1
                close(mean,par['mean']);close(scale,par['scale']);x=(raw-mean)/scale
                dates,counts=np.unique(tr.date.to_numpy(),return_counts=True);counts=dict(zip(dates,counts));w=np.array([len(tr)/(len(dates)*counts[d]) for d in tr.date.to_numpy()])
                design=np.column_stack([np.ones(len(x)),x]);penalty=np.diag([0]+[10]*len(cols));beta=np.linalg.solve(design.T@(w[:,None]*design)+penalty,design.T@(w*tr.catchup.to_numpy()))
                close(beta,np.r_[par['intercept'],par['coef']])
                indices=te.set_index(K).index.get_indexer(pd.MultiIndex.from_frame(pp[K]));xt=(rank.loc[te.index,cols].to_numpy()[indices]-mean)/scale;values=beta[0]+xt@beta[1:]
                maxerror=max(maxerror,float(np.max(abs(values-pp[par['method']].to_numpy()))));close(values,pp[par['method']])
    assert nf==len(folds) and nm==len(models) and nr==len(pred)
    d=pd.read_csv(out/'date_metrics.csv',parse_dates=['date']);visited=0
    for key,g in pred.groupby(G+['date']):
        v=g[g.catchup.notna()]
        for metric in ['mse_reduction','ic_increment']:
            mask=d.metric.eq(metric)
            for c,val in zip(G+['date'],key):mask &= d[c].eq(val)
            assert mask.sum()==1;r=d[mask].iloc[0];visited+=1;assert r.signals==len(g) and r.known==len(v)
            a=b=delta=np.nan
            if metric=='mse_reduction' and len(v):
                a=np.mean((v.controls.to_numpy()-v.catchup.to_numpy())**2);b=np.mean((v.with_leader.to_numpy()-v.catchup.to_numpy())**2);delta=a-b
            elif metric=='ic_increment' and len(v)>=20 and min(v[c].nunique() for c in ['controls','with_leader','catchup'])>1:
                a=np.corrcoef(rankdata(v.controls),rankdata(v.catchup))[0,1];b=np.corrcoef(rankdata(v.with_leader),rankdata(v.catchup))[0,1];delta=b-a
            close([r.baseline,r.added,r.delta],[a,b,delta])
    assert visited==len(d)
    annual=pd.read_csv(out/'annual_metrics.csv');summary=pd.read_csv(out/'summary.csv')
    for table,keys in [(annual,G+['metric','year']),(summary,G+['metric'])]:
      assert len(table)==d.groupby(keys).ngroups
      for key,g in d.groupby(keys):
        mask=np.ones(len(table),dtype=bool)
        for c,val in zip(keys,key):mask &=table[c].eq(val)
        assert mask.sum()==1;r=table[mask].iloc[0];q=g[g.delta.notna()];x=q.delta.to_numpy();assert r.months==len(x);close(r.mean_delta,q.delta.mean())
        if 'year' in keys:continue
        se=lo=hi=flo=fhi=np.nan
        if len(x)>=2:
            months=np.array([t.year*12+t.month for t in q.date]);dist=abs(months[:,None]-months[None,:]);kernel=np.maximum(0,1-dist/4);u=x-x.mean();se=np.sqrt(max(0,u@kernel@u))/len(x);zv=norm.ppf(1-.05/40)
            lo=x.mean()-1.96*se;hi=x.mean()+1.96*se;flo=x.mean()-zv*se;fhi=x.mean()+zv*se
        close([r.standard_error,r.low95,r.high95,r.family20_low,r.family20_high],[se,lo,hi,flo,fhi])
        ys=q.groupby('year').delta.mean();assert r.years==len(ys) and r.positive_years==ys.gt(0).sum()
        ic=summary[(summary.era==r.era)&(summary.level==r.level)&(summary.cohort==r.cohort)&(summary.metric=='ic_increment')].iloc[0]
        support=r.metric=='mse_reduction' and r.cohort=='main80' and len(x)>=24 and len(ys)>=3 and ys.gt(0).all() and flo>0 and ic.mean_delta>=0
        assert bool(r.historical_support)==bool(support)
    js(out/'verification.json',dict(status='PASS',folds=nf,models=nm,paired_predictions=nr,date_metrics=len(d),max_prediction_error=maxerror,support_groups=int(summary.historical_support.sum()),adopted=False));print(json.loads((out/'verification.json').read_text()))
if __name__=='__main__':run()
