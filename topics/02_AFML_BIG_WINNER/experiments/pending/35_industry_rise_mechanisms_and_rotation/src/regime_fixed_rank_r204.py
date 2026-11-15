from common import *
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from evaluate_r01 import scores,VARIANTS
from train_r02 import sample_weights
from regime_core_r196 import arrays
GROUP=['era','level','cohort','method','horizon']
def run():
 out=ROOT/'outputs/r204';out.mkdir(exist_ok=True);panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;parts=[]
 for key,g in panel[panel.price_ready].groupby(['era','level','date']):
  for cohort,needed in VARIANTS.items():
   z=g.dropna(subset=needed).copy()
   if len(z)<20:continue
   sc=scores(z)
   for method in ['momentum','F'] if cohort=='F' else ['F',cohort]:
    p=z[KEY+['date','excess20','excess60','maturity20','maturity60']].copy();p=p.assign(cohort=cohort,method=method,score=sc[method],regime=z.date.map(state));parts.append(p)
 source=pd.concat(parts,ignore_index=True);source.to_parquet(out/'scored_panel.parquet',index=False);preds=[];models=[];ledger=[];maxerr=0.
 for key,g in source.groupby(GROUP[:-1]):
  for h in [20,60]:
   for year in range(2020,2027):
    cut=pd.Timestamp(year,1,1);fit=g.date.lt(cut)&g[f'maturity{h}'].lt(cut)&g[f'excess{h}'].notna();test=g.date.dt.year.eq(year)
    if not test.any():continue
    tr=g[fit&g.regime.notna()];te=g[test&g.regime.notna()];reason='insufficient_train' if len(tr)<300 or tr.date.nunique()<18 else 'no_test' if te.empty else None;ident=dict(zip(GROUP[:-1],key),horizon=h,year=year);ledger.append(dict(ident,train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),removed_fit_unknown=int((fit&g.regime.isna()).sum()),status='skip' if reason else 'fit',reason=reason))
    if reason:continue
    sc=StandardScaler().fit(tr[['score']]);xx=arrays(sc.transform(tr[['score']]),tr.regime);xt=arrays(sc.transform(te[['score']]),te.regime);w=sample_weights(tr).to_numpy();y=tr[f'excess{h}'].to_numpy()
    for variant,x in xx.items():
     model=Ridge(alpha=10).fit(x,y,sample_weight=w);pred=model.predict(xt[variant]);a=np.column_stack([np.ones(len(x)),x]);coef=np.linalg.solve(a.T@(w[:,None]*a)+np.diag([0.]+[10.]*x.shape[1]),a.T@(w*y));err=float(np.max(np.abs(np.column_stack([np.ones(len(te)),xt[variant]])@coef-pred)));assert err<1e-10;maxerr=max(maxerr,err)
     slopes={s:float(model.coef_[0]+(model.coef_[4+j] if variant=='interaction' and j>=0 else 0)) for s,j in [('down_low',-1),('down_high',0),('up_low',1),('up_high',2)]}
     models.append(dict(ident,variant=variant,mean=sc.mean_.tolist(),scale=sc.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_),state_slopes=slopes))
     p=te[KEY+['date','regime','score',f'excess{h}',f'maturity{h}']].rename(columns={f'excess{h}':'y',f'maturity{h}':'maturity'}).copy();p=p.assign(**{k:v for k,v in ident.items() if k not in KEY},variant=variant,prediction=pred,slope=te.regime.map(slopes));preds.append(p)
    p=p.copy();p['variant']='fixed';p['prediction']=p.score;p['slope']=1.;preds.append(p)
 pred=pd.concat(preds,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',models);js(out/'fold_ledger.json',ledger);metrics=[]
 for key,g in pred.groupby(GROUP+['year','date','regime','variant']):
  ident=dict(zip(GROUP+['year','date','regime','variant'],key));g=g.assign(rank_score=np.sign(g.slope)*g.score);q=g[g.y.notna()];ordered=g.sort_values(['rank_score','industry_code'],ascending=[False,True]);top=ordered.head(int(np.ceil(.2*len(g))));ic=q.rank_score.corr(q.y,method='spearman') if len(q)>=20 and q.rank_score.nunique()>1 and q.y.nunique()>1 else np.nan
  metrics.append(dict(ident,known=len(q),origins=len(g),ic=ic,top_excess=top.y.mean() if top.y.notna().all() else np.nan,mse=((q.prediction-q.y)**2).mean() if ident['variant']!='fixed' else np.nan,slope=float(g.slope.iloc[0])))
 d=pd.DataFrame(metrics);d.to_csv(out/'date_metrics.csv',index=False);summary=[]
 for key,g in d.groupby(GROUP):
  for metric in ['ic','top_excess','mse']:
   wide=g.pivot(index='date',columns='variant',values=metric)
   for a,b in [('base','fixed'),('state','base'),('interaction','base'),('interaction','fixed')]:
    if metric=='mse' and b=='fixed':continue
    q=wide[[a,b]].dropna();delta=(q[a]-q[b])*(-1 if metric=='mse' else 1);summary.append(dict(zip(GROUP,key),metric=metric,comparison=a+'-'+b,dates=len(q),improvement=delta.mean()))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
 js(out/'verification.json',dict(status='PASS',models=len(models),prediction_rows=len(pred),normal_equation_error=maxerr,adoption=False,inputs={x:sha(ROOT/x) for x in ['outputs/r130/monthly_panel.parquet','outputs/r195/market_regimes.parquet','protocols/r204.json','src/regime_fixed_rank_r204.py','src/evaluate_r01.py','src/train_r02.py','src/regime_core_r196.py','src/common.py']},outputs={x:sha(out/x) for x in ['scored_panel.parquet','predictions.parquet','models.json','fold_ledger.json','date_metrics.csv','summary.csv']}))
 print(len(models),len(pred),maxerr)
if __name__=='__main__':run()
