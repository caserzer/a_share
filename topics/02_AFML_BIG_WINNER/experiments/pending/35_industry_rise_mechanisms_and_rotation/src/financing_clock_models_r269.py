from common import *
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from scipy.stats import norm
from train_r02 import F,sample_weights
from regime_core_r196 import arrays
BASE=F+['size_control'];METHODS={'FS':BASE,'FSE':BASE+['financing_intensity'],'FSC':BASE+['cap_component'],'FSCB':BASE+['cap_component','balance_component'],'FSEC':BASE+['financing_intensity','cap_component'],'FSECB':BASE+['financing_intensity','cap_component','balance_component']}
COMPS=[('FSE','FS'),('FSCB','FSC'),('FSECB','FSEC'),('FSEC','FSE')]

def run():
 import sys
 clock=sys.argv[1];assert clock in ['signal','snapshot'];out=ROOT/'outputs/r269'/clock;out.mkdir(parents=True,exist_ok=True);paths=['outputs/r262/panel.parquet','outputs/r268/industry_pairs.parquet']
 p=pd.read_parquet(ROOT/paths[0]).drop(columns=['balance_component','cap_component']);c=pd.read_parquet(ROOT/paths[1]);c=c[c.qualified].rename(columns={'current_date':'date',clock+'_balance':'balance_component',clock+'_cap':'cap_component'});p=p.merge(c[KEY+['date','balance_component','cap_component']],on=KEY+['date'],how='inner',validate='one_to_one');p['matched']=p[METHODS['FSECB']].notna().all(axis=1)&p.regime.notna();p.groupby(['era','level']).matched.agg(['size','sum']).to_csv(out/'coverage.csv');p=p[p.matched].copy();p.to_parquet(out/'panel.parquet',index=False);models=[];preds=[];ledger=[]
 for (era,level),g in p.groupby(['era','level']):
  ranks=g.groupby('date')[METHODS['FSECB']].transform(centered_rank)
  for h in [20,60]:
   for year in sorted(g.date.dt.year.unique()):
    cutoff=pd.Timestamp(year,1,1);tr=g[g.date.lt(cutoff)&g[f'maturity{h}'].lt(cutoff)&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)];ok=len(tr)>=300 and tr.date.nunique()>=18;rec=dict(era=era,level=level,horizon=h,year=int(year),train_rows=len(tr),train_dates=tr.date.nunique(),test_rows=len(te),status='fit' if ok else 'skip');ledger.append(rec)
    if not ok:continue
    for name,cols in METHODS.items():
     scale=StandardScaler().fit(ranks.loc[tr.index,cols]);tx=arrays(scale.transform(ranks.loc[tr.index,cols]),tr.regime);ex=arrays(scale.transform(ranks.loc[te.index,cols]),te.regime)
     for variant in ['base','state','interaction']:
      fit=Ridge(alpha=10).fit(tx[variant],tr[f'excess{h}'],sample_weight=sample_weights(tr));q=te[KEY+['date',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'target',f'maturity{h}':'maturity'});q=q.assign(method=name,variant=variant,horizon=h,year=year,prediction=fit.predict(ex[variant]));preds.append(q)
      models.append(dict(rec,method=name,variant=variant,columns=cols,mean=scale.mean_.tolist(),scale=scale.scale_.tolist(),coef=fit.coef_.tolist(),intercept=float(fit.intercept_),fit_max_maturity=tr[f'maturity{h}'].max()))
 pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',models);js(out/'fold_ledger.json',ledger);metrics=[]
 for key,g in pred.groupby(['era','level','horizon','variant','method','date']):
  v=g[g.target.notna()];ic=v.prediction.corr(v.target,method='spearman') if len(v)>=5 and v.prediction.nunique()>1 and v.target.nunique()>1 else np.nan;metrics.append(dict(zip(['era','level','horizon','variant','method','date'],key),ic=ic,mse=((v.prediction-v.target)**2).mean(),known=len(v),unknown=len(g)-len(v)))
 metrics=pd.DataFrame(metrics);metrics.to_parquet(out/'metrics.parquet',index=False);summ=[];daily=[]
 for era,level in [('SW2014','L2'),('SW2014','L3'),('SW2021','L1'),('SW2021','L2'),('SW2021','L3')]:
  for h in [20,60]:
   for variant in ['base','state','interaction']:
    g=metrics[metrics.era.eq(era)&metrics.level.eq(level)&metrics.horizon.eq(h)&metrics.variant.eq(variant)]
    for aa,bb in COMPS:
     ident=dict(era=era,level=level,horizon=h,variant=variant,comparison=aa+'-'+bb)
     if g.empty:summ.append(dict(ident,status='no_fit',historical_support=False));continue
     w=g.pivot(index='date',columns='method',values='ic');delta=(w[aa]-w[bb]).dropna();ms=g.pivot(index='date',columns='method',values='mse');years=delta.groupby(delta.index.year).mean();n=len(delta);se=np.nan
     if n>=2:
      u=pd.Series(delta.to_numpy()-delta.mean(),index=delta.index.to_period('M').astype('int64'));var=float((u*u).sum());lag=3 if h==20 else 6
      for k in range(1,lag+1):var+=2*(1-k/(lag+1))*float(np.nansum(u.to_numpy()*u.reindex(u.index-k).to_numpy()))
      se=np.sqrt(max(0,var))/n
     z=norm.ppf(1-.05/840);lo=delta.mean()-z*se;hi=delta.mean()+z*se
     summ.append(dict(ident,status='evaluated',months=n,years=len(years),positive_years=int(years.gt(0).sum()),ic_delta=delta.mean(),low_family=lo,high_family=hi,mse_improvement=(ms[bb]-ms[aa]).mean(),historical_support=bool(n>=24 and len(years)>=3 and years.gt(0).all() and lo>0)))
     for date,value in delta.items():daily.append(dict(ident,date=date,ic_delta=value))
 pd.DataFrame(summ).to_csv(out/'summary.csv',index=False);pd.DataFrame(daily).to_parquet(out/'paired_dates.parquet',index=False);js(out/'receipt.json',dict(status='PASS',models=len(models),folds=len(ledger),fitted=sum(x['status']=='fit' for x in ledger),predictions=len(pred),planned_comparisons=120,inputs={x:sha(ROOT/x) for x in paths},protocol_sha256=sha(ROOT/'protocols/r269.json'),code_sha256=sha(__file__),adoption=False));print('DONE',len(models),len(pred),sum(x.get('historical_support',False) for x in summ))
if __name__=='__main__':run()
