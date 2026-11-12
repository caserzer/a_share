import sys,json,math
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p53';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
r=EP/'restart';af=r/'p48/distinct_selections.csv';mf=EP/'configs/pool_metric_v1.json';target=json.loads(mf.read_text())['target_realized_success_rate_min'];old=pd.read_csv(af);names=old.candidate.tolist()+['p50:'+x for x in ['B','S','Z','P','momentum']];rows=[];inputs=[af,mf,Path(__file__),r/'P53_fixed_event_bounds_plan.md'];cache={}
for name in names:
 version,method=name.split(':');f=r/version/'evaluated.parquet'
 if version not in cache:cache[version]=pd.read_parquet(f);inputs.append(f)
 q=cache[version];y=q.loc[q[method+'_edge'],'new_win126'];assert set(y.dropna().unique())<=set([0.,1.]);n=len(y);k=int(y.notna().sum());w=int(y.sum());u=n-k;lo=w/n;hi=(w+u)/n
 assert np.isclose(y.fillna(0).mean(),lo) and np.isclose(y.fillna(1).mean(),hi)
 if name in old.candidate.values:
  a=old[old.candidate.eq(name)].iloc[0];assert n==a.edges and k==a.known and np.isclose(w/k,a.win)
 else:
  ef=r/version/'events.csv';a=pd.read_csv(ef).query('horizon==126');a=a[a.method.eq(method)].iloc[0];assert n==a.edges and k==a.known and np.isclose(w/k,a.win)
 rows.append(dict(candidate=name,events=n,known=k,successes=w,unknown=u,mature_win=w/k,all_unknown_fail_bound=lo,all_unknown_succeed_bound=hi,can_fixed_set_reach_60=hi>=target,successes_needed=math.ceil(target*n),max_possible_successes=w+u,scope='EXISTING_FIXED_EVENT_SET_ONLY'))
a=pd.DataFrame(rows);a.to_csv(OUT/'bounds.csv',index=False);(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',candidates=len(a),unreachable_count=int((~a.can_fixed_set_reach_60).sum()),target=target,unknowns_not_imputed_in_source=True,inputs={str(f):sha(f) for f in inputs},artifacts={f.name:sha(f) for f in OUT.iterdir() if f.is_file()}),indent=2)+'\n');print(a[['candidate','events','successes','unknown','all_unknown_succeed_bound','can_fixed_set_reach_60']].to_string(index=False))
