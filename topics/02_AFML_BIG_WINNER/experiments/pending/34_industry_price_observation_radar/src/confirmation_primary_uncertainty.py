"""Descriptive common-calendar uncertainty; no business pass/fail inference."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,sha

def main():
 out=EP/'outputs/confirmation_primary_uncertainty'
 if out.exists():raise FileExistsError('Preserve uncertainty snapshot')
 root=EP/'outputs/evaluation_versions/s05_20261021/runs/A'
 paths=[root/'event_quality.parquet',root/'parent_coverage.parquet',EP/'outputs/refresh/s02_chain_safe_v2_20261112/calendar_coverage.csv',EP/'protocols/confirmation_v1/uncertainty_plan.md',Path(__file__)]
 e=pd.read_parquet(paths[0]);e=e[e.kind.eq('NEW')];p=pd.read_parquet(paths[1]);dates=pd.read_csv(paths[2]).date
 weeks=pd.to_datetime(dates).dt.to_period('W-SUN').astype(str);wm={w:i for i,w in enumerate(weeks)};n=len(weeks);assert n==501
 def series(d,v):
  idx=pd.to_datetime(d).dt.to_period('W-SUN').astype(str).map(wm);assert idx.notna().all()
  return np.bincount(idx.astype(int),weights=np.asarray(v,float),minlength=n)
 x=np.array([series(e.date,e.status.eq('COVERED')),series(e.date,~e.status.str.contains('UNKNOWN')),series(e.date,np.ones(len(e))),series(e.date,e.status.str.contains('UNKNOWN')),
             series(p.start,p.covered),series(p.start,np.ones(len(p))),series(p.start,p.timing.eq('TIMELY')),series(p.start,p.timing.eq('LATE'))])
 assert x.sum(axis=1).tolist()==[1260,1435,1459,24,1360,5759,583,777]
 rng=np.random.default_rng(34090);weights=[]
 for _ in range(2000):
  starts=rng.integers(0,n,size=int(np.ceil(n/13)));idx=((starts[:,None]+np.arange(13))%n).ravel()[:n];weights.append(np.bincount(idx,minlength=n))
 z=np.array(weights)@x.T
 names=['new_matching_rate','parent_coverage','timely_parent_coverage','late_parent_coverage'];num=[0,4,6,7];den=[1,5,5,5];total=x.sum(axis=1)
 results={name:{'numerator':int(total[i]),'denominator':int(total[j]),'point':float(total[i]/total[j]),'interval95':np.quantile(z[:,i]/z[:,j],[.025,.975]).tolist()} for name,i,j in zip(names,num,den)}
 results['unknown_identification_bounds']={'total_new':1459,'unknown':24,'lower':1260/1459,'upper':1284/1459,'not_confidence_interval':True}
 out.mkdir();pd.DataFrame(x.T,columns=['effective_new','evaluable_new','all_new','unknown_new','covered_parent','all_parent','timely_parent','late_parent']).assign(week=weeks.values).to_csv(out/'weekly_contributions.csv',index=False)
 result={'block_weeks':13,'repetitions':2000,'seed':34090,'results':results,'limits':'Conditional descriptive historical uncertainty; does not address label choice or reused history. No acceptance decision.'}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');(out/'receipt.json').write_text(json.dumps({'inputs':{str(f):sha(f) for f in paths},'artifacts':{f.name:sha(f) for f in out.iterdir() if f.is_file()}},indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
