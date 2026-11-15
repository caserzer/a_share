"""Saved-parameter prediction reconstruction independent of regime array helper."""
from common import *
import pandas as pd
from train_r02 import F

def run():
 out=ROOT/'outputs/r197';models=json.loads((out/'models.json').read_text());pred=pd.read_parquet(out/'predictions.parquet');state=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime
 panel=pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet');l1=pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet');maximum=0.;count=0
 for family in pred.family.unique():
  p=pd.concat([panel,l1],ignore_index=True) if family.startswith('eps_') else panel.copy();p['log_members']=np.log(p.members)
  path=f'data/r29_{family[4:]}_coverage.parquet' if family.startswith('eps_') else 'data/r25_revision_coverage.parquet'
  g=pd.read_parquet(ROOT/path).merge(p,on=KEY+['date'],suffixes=('_coverage',''),validate='many_to_one');g=g[g.price_ready].dropna(subset=F+['covered_member_median'])
  for m in [m for m in models if m['family']==family]:
   v=g[(g.era==m['era'])&(g.level==m['level'])&(g.fy_offset==m['fy_offset'])];v=v[v.eligible if m['population']=='strict' else v.known.ge(5)&~v.eligible].copy();v=v[v.groupby('date').date.transform('size').ge(2)];v['expectation']=v.covered_member_median
   rank=(v.groupby('date')[m['columns']].rank(method='average')-.5)/v.groupby('date')[m['columns']].transform('count')-.5
   test=v.date.dt.year.eq(m['year'])&v.date.map(state).notna();v=v[test];x=(rank.loc[v.index].to_numpy()-m['scaler_mean'])/m['scaler_scale'];s=v.date.map(state)
   dummy=np.array([[float(t==k) for k in ['down_high','up_low','up_high']] for t in s]);design=x
   if m['variant']!='base':design=np.concatenate([x,dummy],axis=1)
   if m['variant']=='interaction':design=np.concatenate([design]+[x*dummy[:,i,None] for i in range(3)],axis=1)
   z=v[KEY+['date']].copy();z['manual']=design@np.array(m['coef'])+m['intercept']
   q=pred.copy()
   for k in ['family','era','level','fy_offset','population','horizon','year','method','variant']:q=q[q[k]==m[k]]
   q=q.merge(z,on=KEY+['date'],validate='one_to_one');assert len(q)==len(v)
   err=float((q.prediction-q.manual).abs().max());assert err<1e-12;maximum=max(maximum,err);count+=len(q)
 assert count==len(pred)
 js(out/'independent_verification.json',dict(status='PASS',rows=count,max_prediction_error=maximum,scope='all saved-parameter predictions and independently constructed dummy interactions',code_sha256=sha(__file__),prediction_sha256=sha(out/'predictions.parquet')))
 print(count,maximum)
if __name__=='__main__':run()
