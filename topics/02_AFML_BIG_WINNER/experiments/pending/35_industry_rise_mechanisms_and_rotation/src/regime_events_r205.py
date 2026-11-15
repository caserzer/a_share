from common import *
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from regime_core_r196 import arrays
from train_r02 import sample_weights
SOURCES={'fixed_fy':'data/r26_industry_events.parquet','unknown_controls':'data/r26_unknown_control_sensitivity.parquet','paired_fy':'outputs/r91/industry_events.parquet'}
GROUP=['family','era','level','target_type','horizon']
def run():
 out=ROOT/'outputs/r205';out.mkdir(exist_ok=True);root=ROOT/'outputs/r144/evaluation';state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;calendar=state.index;parts=[];models=[];ledger=[];coverage=[];maximum=0.
 for family,path in SOURCES.items():
  raw=pd.read_parquet(root/path);raw['event_id']=np.arange(len(raw));raw['date']=raw.signal_date
  pos=calendar.searchsorted(raw.date,side='left')-1;raw['state_date']=[calendar[x] if x>=0 else pd.NaT for x in pos];raw['regime']=raw.state_date.map(state)
  assert (raw.state_date.dropna()<raw.loc[raw.state_date.notna(),'date']).all()
  extra=['current','next'] if family=='paired_fy' else ['revision'];cols=['pre20','pre60']+extra;g=raw.dropna(subset=cols+['regime']).copy();g.to_parquet(out/f'{family}_panel.parquet',index=False)
  coverage.append(dict(family=family,source_rows=len(raw),complete_rows=len(g),unknown_state=int(raw.regime.isna().sum()),signal_dates=g.date.nunique(),months=g.date.dt.to_period('M').nunique()))
  for (era,level),z in g.groupby(['era','level']):
   for typ in ['post'] if family=='paired_fy' else ['post','matched_post']:
    for h in [20,60]:
     target=typ+str(h)
     for year in range(2020,2027):
      cut=pd.Timestamp(year,1,1);tr=z[z.date.lt(cut)&z[f'maturity{h}'].lt(cut)&z[target].notna()];te=z[z.date.dt.year.eq(year)]
      if te.empty:continue
      ident=dict(family=family,era=era,level=level,target_type=typ,horizon=h,year=year);months=tr.date.dt.to_period('M').nunique();reason='insufficient_train' if len(tr)<300 or months<18 else None;ledger.append(dict(ident,train_rows=len(tr),train_months=months,test_rows=len(te),status='skip' if reason else 'fit',reason=reason,state_train_months=tr.groupby('regime').date.apply(lambda x:x.dt.to_period('M').nunique()).to_dict()))
      if reason:continue
      for method,features in [('controls',['pre20','pre60']),('with_revision',cols)]:
       scaler=StandardScaler().fit(tr[features]);xx=arrays(scaler.transform(tr[features]),tr.regime);xt=arrays(scaler.transform(te[features]),te.regime);w=sample_weights(tr).to_numpy();y=tr[target].to_numpy()
       for variant,x in xx.items():
        model=Ridge(alpha=10).fit(x,y,sample_weight=w);pred=model.predict(xt[variant]);a=np.column_stack([np.ones(len(x)),x]);coef=np.linalg.solve(a.T@(w[:,None]*a)+np.diag([0.]+[10.]*x.shape[1]),a.T@(w*y));err=float(np.max(np.abs(np.column_stack([np.ones(len(te)),xt[variant]])@coef-pred)));assert err<1e-10;maximum=max(maximum,err)
        models.append(dict(ident,method=method,variant=variant,columns=features,mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),coef=model.coef_.tolist(),intercept=float(model.intercept_)))
        p=te[KEY+['date','state_date','regime','event_id',target,f'maturity{h}']].rename(columns={target:'y',f'maturity{h}':'maturity'}).copy();p=p.assign(**{k:v for k,v in ident.items() if k not in KEY},method=method,variant=variant,prediction=pred);parts.append(p)
  print(family,len(models),flush=True)
 pred=pd.concat(parts,ignore_index=True);pred.to_parquet(out/'predictions.parquet',index=False);js(out/'models.json',models);js(out/'fold_ledger.json',ledger);js(out/'coverage.json',coverage);rows=[]
 for key,g in pred.groupby(GROUP+['method','variant','date','regime']):
  q=g[g.y.notna()];rows.append(dict(zip(GROUP+['method','variant','date','regime'],key),origins=len(g),known=len(q),mse=((q.prediction-q.y)**2).mean()))
 d=pd.DataFrame(rows);d.to_csv(out/'date_metrics.csv',index=False);summary=[]
 for key,g in d.groupby(GROUP):
  w=g.pivot(index='date',columns=['method','variant'],values='mse')
  for a,b in [(('with_revision',v),('with_revision','base')) for v in ['state','interaction']]+[(('with_revision',v),('controls',v)) for v in ['base','state','interaction']]:
   q=w[[a,b]].dropna();summary.append(dict(zip(GROUP,key),first='/'.join(a),second='/'.join(b),dates=len(q),mse_improvement=(q[b]-q[a]).mean()))
 pd.DataFrame(summary).to_csv(out/'summary.csv',index=False)
 reads=[root/x for x in SOURCES.values()]+[ROOT/'outputs/r195/market_regimes.parquet',ROOT/'protocols/r205.json',Path(__file__),ROOT/'src/regime_core_r196.py',ROOT/'src/train_r02.py',ROOT/'src/common.py']
 js(out/'verification.json',dict(status='PASS',models=len(models),predictions=len(pred),normal_equation_error=maximum,adoption=False,inputs={str(x):sha(x) for x in reads},outputs={x:sha(out/x) for x in ['predictions.parquet','models.json','fold_ledger.json','coverage.json','date_metrics.csv','summary.csv']}))
if __name__=='__main__':run()
