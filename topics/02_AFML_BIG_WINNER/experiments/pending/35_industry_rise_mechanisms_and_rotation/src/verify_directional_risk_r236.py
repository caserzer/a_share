from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r236';q=pd.read_csv(out/'directional_risk.csv');checked=0;maximum=0.
 for rnd,z in q.groupby('source_round'):
  d=pd.read_parquet(ROOT/f'outputs/r{rnd}/daily_returns.parquet');keys=['era','level','cohort','horizon','method'];lookup={k:g for k,g in d.groupby(keys)};original=pd.read_csv(ROOT/f'outputs/r{rnd}/paired_risk.csv');assert z.pair_id.nunique()==len(original)
  for row in z.to_dict('records'):
   if row['status']=='incomplete_original_path':assert not row['both_whole'];continue
   base=tuple(row[k] for k in keys[:-1]);a=lookup[base+(row['method'],)].set_index('date').sort_index();b=lookup[base+(row['control'],)].set_index('date').sort_index();assert a.index.equals(b.index);direction=row['market_direction'];idx=[i for i,x in enumerate(a.benchmark) if direction=='all' or (direction=='down' and x<0) or (direction=='up' and x>0) or (direction=='zero' and x==0)];assert len(idx)==row['days']
   for prefix,frame in [('first_',a),('control_',b)]:
    values=frame.iloc[idx][row['cost']].tolist();market=frame.iloc[idx].benchmark.tolist();n=len(values);mean=sum(values)/n if n else np.nan;mu=sum(market)/n if n else np.nan;den=sum((x-mu)**2 for x in market);metrics=dict(mean=mean,loss_fraction=sum(x<0 for x in values)/n if n else np.nan,downside_rms=(sum(min(x,0)**2 for x in values)/n)**.5 if n else np.nan,beta=sum((x-mean)*(y-mu) for x,y in zip(values,market))/den if n>=2 and den>0 else np.nan)
    for k,v in metrics.items():
     assert np.isclose(v,row[prefix+k],atol=1e-11,equal_nan=True)
     if np.isfinite(v):maximum=max(maximum,abs(v-row[prefix+k]))
     checked+=1
   for k in ['mean','loss_fraction','downside_rms','beta']:assert np.isclose(row['first_'+k]-row['control_'+k],row['delta_'+k],atol=1e-11,equal_nan=True)
 for _,g in q[q.status.eq('complete_path_diagnostic')].groupby('pair_id'):
  assert g[g.market_direction.ne('all')].days.sum()==g[g.market_direction.eq('all')].days.iloc[0]
 js(out/'independent_verification.json',dict(status='PASS',scalar_metric_checks=checked,max_error=maximum,scope='Every direction group, both legs, scalar mean/loss/RMS/beta, deltas and partition counts',code_sha256=sha(__file__)));print(checked,maximum)
if __name__=='__main__':run()
