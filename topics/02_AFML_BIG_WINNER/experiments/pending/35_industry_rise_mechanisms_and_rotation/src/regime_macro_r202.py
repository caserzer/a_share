"""State-dependent rolling macro sensitivity on frozen publication-lag proxies."""
from common import *
import pandas as pd
from sklearn.linear_model import Ridge
from regime_core_r196 import arrays

def run():
 out=ROOT/'outputs/r202';out.mkdir(exist_ok=True);source=ROOT/'outputs/r158/evaluation'
 p=pd.concat([pd.read_parquet(source/'data/monthly_panel.parquet'),pd.read_parquet(source/'data/l1_monthly_panel.parquet')],ignore_index=True);p['row_id']=p.index
 states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;macro=pd.read_parquet(source/'data/r13_macro_states.parquet');old=pd.read_parquet(source/'data/r13_sensitivities.parquet');records=[];ledger=[];maxerr=0.;old_errors=[]
 for lag in [45,75]:
  state=macro[macro.lag.eq(lag)].sort_values('date').copy();state['regime']=state.date.map(states);state['lag_regime']=state.regime.shift(1)
  merged=p.merge(state,on='date',validate='many_to_one');original=old[old.lag.eq(lag)].set_index('row_id')
  for key,g in merged.groupby(KEY):
   g=g.sort_values('date')
   for row in g.itertuples():
    h=g[g.date.lt(row.date)&g.date.ge(row.date-pd.DateOffset(months=36))].dropna(subset=['lag_pmi','lag_money','past_excess20']);before=len(h);h=h[h.lag_regime.notna()];rec=dict(zip(KEY,key),row_id=row.row_id,date=row.date,lag=lag,n_fit=len(h),removed_unknown=before-len(h));current=np.array([row.pmi,row.money]);reason=None
    if len(h)<24:reason='insufficient_history'
    elif pd.isna(row.regime) or not np.isfinite(current).all():reason='unknown_current_state'
    else:
     x=h[['lag_pmi','lag_money']].to_numpy();mu=x.mean(0);sd=x.std(0)
     if (sd<=1e-10).any():reason='constant_macro'
    ledger.append(dict(rec,status='skip' if reason else 'fit',reason=reason))
    if reason:continue
    x=(x-mu)/sd;xt=((current-mu)/sd).reshape(1,-1);xx=arrays(x,h.lag_regime);tt=arrays(xt,pd.Series([row.regime]));y=h.past_excess20.to_numpy()
    for variant,a in xx.items():
     model=Ridge(alpha=1).fit(a,y);centroid=a.mean(0);score=float((tt[variant][0]-centroid)@model.coef_)
     design=np.column_stack([np.ones(len(a)),a]);coef=np.linalg.solve(design.T@design+np.diag([0.]+[1.]*a.shape[1]),design.T@y);check=float((tt[variant][0]-centroid)@coef[1:]);err=abs(score-check);assert err<1e-10;maxerr=max(maxerr,err)
     if variant=='base' and before==len(h) and row.row_id in original.index:
      e=abs(score-original.loc[row.row_id,'conditioned']);assert e<1e-10;old_errors.append(e)
     records.append(dict(rec,variant=variant,regime=row.regime,exposure=float(model.coef_[:2].mean()),conditioned=score,mean=mu.tolist(),scale=sd.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_),design_mean=centroid.tolist(),current_macro=current.tolist(),fit_last_date=h.date.max()))
  print('lag',lag,'models',len(records),flush=True)
 f=pd.DataFrame(records);f.to_parquet(out/'sensitivities.parquet',index=False);pd.DataFrame(ledger).to_parquet(out/'fold_ledger.parquet',index=False)
 common=set(f.groupby('row_id').size().loc[lambda x:x.eq(6)].index);metrics=[];scores=[]
 for key,full in p.groupby(['era','level','date']):
  g=full[full.price_ready&full.row_id.isin(common)]
  if len(g)<20:continue
  rank=g[['mom20','mom60','vol20','dd60']].apply(centered_rank);baseline=((rank.mom20+rank.mom60)/2-rank.vol20+rank.dd60)/3
  for lag in [45,75]:
   for variant in ['base','state','interaction']:
    z=g.join(f[f.lag.eq(lag)&f.variant.eq(variant)].set_index('row_id')[['exposure','conditioned']],on='row_id',validate='one_to_one')
    for method,score in {'F':baseline,'F_exposure':(baseline+centered_rank(z.exposure))/2,'F_macro':(baseline+centered_rank(z.conditioned))/2}.items():
     ordered=z.assign(score=score).sort_values(['score','industry_code'],ascending=[False,True]);top=ordered.head(int(np.ceil(.2*len(z))))
     a=z[KEY+['date','row_id','excess20','excess60']].copy();a=a.assign(lag=lag,variant=variant,method=method,score=score,selected=z.index.isin(top.index));scores.append(a)
     for h in [20,60]:
      known=z[f'excess{h}'].notna();ic=score[known].corr(z.loc[known,f'excess{h}'],method='spearman') if known.sum()>=20 and score[known].nunique()>1 and z.loc[known,f'excess{h}'].nunique()>1 else np.nan;complete=top[f'excess{h}'].notna().all()
      metrics.append(dict(zip(['era','level','date'],key),lag=lag,variant=variant,method=method,horizon=h,ic=ic,n=len(z),known=int(known.sum()),top_complete=bool(complete),top_excess=top[f'excess{h}'].mean() if complete else np.nan))
 pd.concat(scores,ignore_index=True).to_parquet(out/'scores.parquet',index=False);d=pd.DataFrame(metrics);d.to_csv(out/'date_metrics.csv',index=False);comparisons=[]
 for key,g in d.groupby(['era','level','lag','horizon']):
  for metric in ['ic','top_excess']:
   w=g.pivot(index='date',columns=['method','variant'],values=metric)
   pairs=[(('F_macro',v),('F_macro','base')) for v in ['state','interaction']]+[(('F_macro',v),(b,v)) for v in ['base','state','interaction'] for b in ['F','F_exposure']]
   for a,b in pairs:
    z=w[[a,b]].dropna();comparisons.append(dict(zip(['era','level','lag','horizon'],key),metric=metric,first='/'.join(a),second='/'.join(b),dates=len(z),delta=(z[a]-z[b]).mean()))
 pd.DataFrame(comparisons).to_csv(out/'comparisons.csv',index=False)
 reads=[source/'data/monthly_panel.parquet',source/'data/l1_monthly_panel.parquet',source/'data/r13_macro_states.parquet',source/'data/r13_sensitivities.parquet',ROOT/'outputs/r195/market_regimes.parquet',ROOT/'protocols/r202.json',Path(__file__),ROOT/'src/regime_core_r196.py',ROOT/'src/common.py']
 js(out/'verification.json',dict(status='PASS',models=len(f),original_unfiltered_models=len(old_errors),original_max_error=max(old_errors),normal_equation_error=maxerr,common_origins=len(common),metric_rows=len(d),adoption=False,reads={str(x):sha(x) for x in reads},outputs={x:sha(out/x) for x in ['sensitivities.parquet','fold_ledger.parquet','scores.parquet','date_metrics.csv','comparisons.csv']}))
if __name__=='__main__':run()
