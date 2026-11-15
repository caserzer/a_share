from common import *
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from build_panel import price_features,delayed_labels
from train_r02 import F,train_masks
from refit_r131 import prepare
from regime_core_r196 import arrays

def run():
 out=ROOT/'outputs/r256';paths=['outputs/r129/daily_2026-10-21.parquet','outputs/r130/monthly_panel.parquet','outputs/r196/models.json','outputs/r196/fold_ledger.json','outputs/r195/market_regimes.parquet','outputs/r253/scores.parquet']
 source=pd.read_parquet(ROOT/paths[0]);market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;parts=[]
 for _,g in source.groupby(KEY+['block'],sort=False):
  q=delayed_labels(price_features(g),market,horizons=(20,));q['log_members']=np.log(q.members);parts.append(q[q[F].notna().all(axis=1)&q.coverage.ge(.8)&q.members.ge(5)])
 ready=pd.concat(parts,ignore_index=True);ranks=ready.groupby(['era','level','date'])[F].transform(centered_rank);states=pd.read_parquet(ROOT/paths[4]).regime;ready['regime']=ready.date.map(states)
 models=[m for m in json.loads((ROOT/paths[2]).read_text()) if m['family']=='core' and m['cohort']=='F' and m['method']=='F' and m['task']=='onset' and m['horizon']==20]
 ledger=json.loads((ROOT/paths[3]).read_text());monthly=pd.read_parquet(ROOT/paths[1]);monthly['log_members']=np.log(monthly.members)
 prior=pd.read_parquet(ROOT/paths[5]);folds=[];preds=[];calrows=[];metrics=[];bins=[];maxerror=0.
 for m in models:
  year=m['year'];boundary=pd.Timestamp(year,1,1);start=pd.Timestamp(year-1,7,1);ident={k:m[k] for k in ['era','level','year','variant']}
  q,_=prepare(monthly,m['era'],m['level'],'F','onset',20);q=q[q.date.map(states).notna()];fit,cal,_=train_masks(q,year,20,'onset');tr=q[fit];mc=q[cal]
  rec=next(x for x in ledger if all(x.get(k)==m[k] for k in ['family','era','level','cohort','method','task','horizon','year']))
  assert len(mc)==rec['cal_rows'] and len(tr)==rec['fit_rows'] and tr.maturity20.max()<start
  g=ready[ready.era.eq(m['era'])&ready.level.eq(m['level'])&ready.date.ge(start)&ready.date.lt(pd.Timestamp(year+1,1,1))&ready.regime.notna()].copy()
  x=(ranks.loc[g.index,m['columns']].to_numpy()-m['scaler_mean'])/m['scaler_scale'];x=arrays(x,g.regime)[m['variant']];g['linear']=x@np.array(m['coefficient']).ravel()+np.asarray(m['intercept']).item();g=g[g.past_excess20.le(0)];g['y']=((g.return20>=.05)&(g.excess20>=.03)).astype(float).where(g.excess20.notna())
  ca=g[g.date.lt(boundary)&g.maturity20.lt(boundary)&g.y.notna()].copy();te=g[g.date.ge(boundary)].copy();counts=ca.y.value_counts().reindex([0.,1.],fill_value=0);ok=len(ca)>=100 and ca.date.dt.to_period('M').nunique()>=4 and counts.min()>=10
  fold=dict(ident,status='fit' if ok else 'skip',cal_rows=len(ca),cal_months=ca.date.dt.to_period('M').nunique(),class0=int(counts[0]),class1=int(counts[1]),fit_max_maturity=tr.maturity20.max(),cal_max_maturity=ca.maturity20.max(),monthly_n_cal=len(mc),base_model=m)
  if not ok:folds.append(fold);continue
  ca['weight']=len(mc)/(ca.date.nunique()*ca.groupby('date').date.transform('size'));f=LogisticRegression(C=1,max_iter=2000,random_state=3502).fit(ca[['linear']],ca.y,sample_weight=ca.weight)
  fold.update(coefficient=float(f.coef_[0,0]),intercept=float(f.intercept_[0]),iterations=int(f.n_iter_[0]),converged=bool(f.n_iter_[0]<2000));folds.append(fold)
  ca['year']=year;ca['variant']=m['variant'];calrows.append(ca[KEY+['date','maturity20','y','linear','weight','year','variant']])
  te['monthly_probability']=expit(te.linear*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item());te['daily_probability']=f.predict_proba(te[['linear']])[:,1];te['year']=year;te['variant']=m['variant']
  old=prior[prior.era.eq(m['era'])&prior.level.eq(m['level'])&prior.year.eq(year)&prior.variant.eq(m['variant'])&prior.eligible];check=te.merge(old[KEY+['date','score']],on=KEY+['date'],how='outer',indicator=True,validate='one_to_one');assert check._merge.eq('both').all();err=float((check.monthly_probability-check.score).abs().max());assert err<1e-10;maxerror=max(maxerror,err)
  preds.append(te[KEY+['date','maturity20','y','year','variant','linear','monthly_probability','daily_probability']]);v=te[te.y.notna()]
  for method in ['monthly','daily']:
   p=v[method+'_probability'];z=pd.DataFrame(dict(date=v.date,brier=(p-v.y)**2,logloss=-(v.y*np.log(p.clip(1e-15,1-1e-15))+(1-v.y)*np.log(1-p.clip(1e-15,1-1e-15))),gap=p-v.y));av=z.groupby('date')[['brier','logloss','gap']].mean().mean();metrics.append(dict(ident,method=method,rows=len(te),mature=len(v),unknown=int(te.y.isna().sum()),dates=v.date.nunique(),**av.to_dict()))
   for k,b in v.assign(bin=np.minimum((p*10).astype(int),9),prob=p).groupby('bin'):bins.append(dict(ident,method=method,bin=int(k),rows=len(b),probability=b.prob.mean(),observed=b.y.mean()))
  print('CALIBRATED',ident,len(ca),len(te),flush=True)
 pd.concat(preds,ignore_index=True).to_parquet(out/'predictions.parquet',index=False);pd.concat(calrows,ignore_index=True).to_parquet(out/'calibration_rows.parquet',index=False);js(out/'folds.json',folds);pd.DataFrame(metrics).to_csv(out/'summary.csv',index=False);js(out/'bins.json',bins)
 js(out/'receipt.json',dict(status='PASS',models=len(models),fitted=sum(x['status']=='fit' for x in folds),monthly_max_error=maxerror,inputs={p:sha(ROOT/p) for p in paths},market_sha256=sha(CACHE/'forecast_v5/CSI_ALL.parquet'),protocol_sha256=sha(ROOT/'protocols/r256.json'),code_sha256=sha(__file__),base_refitted=False,adoption=False))
if __name__=='__main__':run()
