"""Independent model, covariance and full exit accounting checks."""
import shutil
import pandas as pd
from common import *
import size_models_r31,verify_size_models_r31,verify_classifiers_r32

def run():
 out=ROOT/'outputs/r142';root=out/'evaluation'
 for p,h in json.loads((out/'summary.json').read_text())['reads'].items():assert sha(p)==h
 for name in ['size_models_r31','classifiers_size_r32','evaluate_classifiers_r32']:shutil.copyfile(ROOT/f'src/{name}.py',root/f'src/{name}.py')
 size_models_r31.ROOT=root;verify_size_models_r31.ROOT=root;verify_classifiers_r32.ROOT=root;verify_size_models_r31.run();verify_classifiers_r32.run()
 dest=root/'outputs/r31';p=pd.read_parquet(dest/'predictions.parquet');metrics=pd.read_csv(dest/'metrics_by_date.csv',parse_dates=['date']);keys=['era','level','horizon','method','date'];look=metrics.set_index(keys)
 for key,g in p.groupby(keys):
  q=g.dropna(subset=['target']);r=look.loc[key];assert r.origins==len(g) and r.complete==len(q);assert np.isclose(r.mse,((q.prediction-q.target)**2).mean(),equal_nan=True);ic=q.prediction.rank().corr(q.target.rank()) if len(q)>=5 and q.prediction.nunique()>1 and q.target.nunique()>1 else np.nan;assert np.isclose(r.ic,ic,equal_nan=True)
 inc=pd.read_csv(dest/'increments.csv');paired=pd.read_csv(dest/'paired_by_date.csv',parse_dates=['date'])
 for r in inc.to_dict('records'):
  z=paired.copy()
  for k in ['era','level','horizon','comparison','metric']:z=z[z[k].eq(r[k])]
  z=z.dropna(subset=['delta']);v=z.delta.to_numpy();t=z.date.dt.to_period('M').astype('int64').to_numpy();lag=3 if r['horizon']==20 else 6;k=np.maximum(1-np.abs(t[:,None]-t[None,:])/(lag+1),0);u=v-v.mean();se=np.sqrt(max(u@k@u,0))/len(v);assert r['months']==len(v) and np.isclose(r['mean'],v.mean()) and np.isclose(r['low99'],v.mean()-2.5758293035489004*se) and np.isclose(r['high99'],v.mean()+2.5758293035489004*se)
 # Full exit outcomes against repaired inputs, selection and cost algebra.
 p=pd.read_parquet(root/'data/r33_exit_origins.parquet');cols=KEY+['date','return20','market_return20','return60','market_return60'];panel=pd.concat([pd.read_parquet(root/f'data/{f}',columns=cols) for f in ['monthly_panel.parquet','l1_monthly_panel.parquet']]).set_index(KEY+['date']);q=panel.loc[pd.MultiIndex.from_frame(p[KEY+['date']])]
 for c in cols[len(KEY)+1:]:assert np.allclose(p[c],q[c],equal_nan=True)
 d=pd.read_csv(root/'outputs/r33/date_metrics.csv',parse_dates=['date']);look=d.set_index(keys+['cost']);checks=0
 for key,g in p.groupby(keys):
  chosen=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)*.2)));assert set(g[g.alert].industry_code)==set(chosen.industry_code);h=key[2];r=g[f'return{h}'];b=g[f'market_return{h}'];known=r.notna()&b.notna();valid=known&g.alert
  for c in [0,.002,.005]:
   x=look.loc[key+(c,)];assert x.origins==len(g) and x.alerts==len(chosen) and x.complete==known.sum() and x.alert_complete==valid.sum() and x.policy_complete==known.all();cash=(1-c)-(1+r)*(1-c);switch=(1-c)**3*(1+b)-(1+r)*(1-c)
   values=dict(alert_cash=cash[valid].mean(),alert_market=switch[valid].mean(),policy_cash=cash[g.alert].sum()/len(g) if known.all() else np.nan,policy_market=switch[g.alert].sum()/len(g) if known.all() else np.nan,wrong_absolute=r[valid].gt(0).mean(),wrong_relative=(r[valid]-b[valid]).gt(0).mean(),missed_upside=r[valid].clip(lower=0).mean(),avoided_loss=-r[valid].clip(upper=0).mean(),precision=g.loc[valid,'y'].mean())
   for col,value in values.items():assert np.isclose(x[col],value,equal_nan=True)
   checks+=1
 policies=pd.read_csv(root/'outputs/r33/paired_policy.csv')
 for x in policies.to_dict('records'):
  z=d.copy()
  for k in ['era','level','horizon','cost']:z=z[z[k].eq(x[k])]
  w=z.pivot(index='date',columns='method',values=x['metric']);delta=w.FDS-w.FS if x['comparison']=='diffusion_with_size' else w.FD-w.F;assert delta.count()==x['months'] and np.isclose(delta.mean(),x['mean_delta'],equal_nan=True)
 js(out/'verification.json',dict(status='PASS',return_date_metrics=len(metrics),return_intervals=len(inc),exit_origins=len(p),exit_date_cost_checks=checks,exit_policy_comparisons=len(policies),subchecks={str(x.relative_to(out)):sha(x) for x in [root/'outputs/r31/verification.json',root/'outputs/r32/verification.json']},verifier_sha256=sha(__file__)))
 print('SIZE REPAIR VERIFIED',len(metrics),len(p),checks,flush=True)
if __name__=='__main__':run()
