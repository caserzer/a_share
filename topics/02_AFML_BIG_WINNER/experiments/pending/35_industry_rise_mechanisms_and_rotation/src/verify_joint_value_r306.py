from pathlib import Path
from collections import defaultdict
from statistics import fmean
import json,hashlib,math
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'outputs/r306';K=['era','level','industry_code','date'];G=['era','level','variant','strategy'];M=['terminal_return','terminal_excess','worst_absolute_shortfall','mean_absolute_shortfall','worst_relative_shortfall','onset_hit','reversal_hit']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def equal(a,b):return (pd.isna(a) and pd.isna(b)) or abs(a-b)<1e-12
r=json.loads((O/'receipt.json').read_text())
for p,h in r['inputs'].items():assert sha(R/p)==h
for p,h in r['outputs'].items():assert sha(O/p)==h
source=pd.read_parquet(R/'outputs/r304/paired_alerts.parquet');expected={tuple(getattr(x,k) for k in K+['variant','strategy']):x.alert_presence=='both' for x in source.itertuples() if x.coverage=='both' and x.eligibility=='onset__reversal' and x.alert_presence in ('both','left_only')}
a=pd.read_parquet(O/'alert_observations.parquet');assert len(a)==len(expected)
paths=np.load(R/'outputs/r291/normalized_paths.npz');stock=paths['stock'];market=paths['market'];keys=pd.read_parquet(R/'outputs/r291/path_keys.parquet');by={tuple(getattr(x,k) for k in K):x.path_id for x in keys.itertuples()};risk={}
for k in {key[:4] for key in expected}:
 if k not in by:continue
 i=by[k];s=list(map(float,stock[i]));b=list(map(float,market[i]));loss=[max(1-v,0) for v in s[1:]];trough=min(x/y-1 for x,y in zip(s[1:],b[1:]));ret=s[-1]-1;ex=s[-1]-b[-1];risk[k]=[ret,ex,max(loss),fmean(loss),max(-trough,0),float(ret>=.05 and ex>=.03),float(trough<=-.08)]
groups=defaultdict(list)
for x in a.itertuples():
 k=tuple(getattr(x,c) for c in K);assert x.joint_alert==expected[k+(x.variant,x.strategy)];assert x.complete_path==(k in risk)
 for i,m in enumerate(M):assert equal(getattr(x,m),risk[k][i] if k in risk else float('nan'))
 groups[tuple(getattr(x,c) for c in G+['date'])].append((x.joint_alert,risk.get(k)))
d=pd.read_parquet(O/'date_contrasts.parquet');assert len(d)==len(groups)
for x in d.itertuples():
 g=groups[tuple(getattr(x,c) for c in G+['date'])];t=[v for yes,v in g if yes];c=[v for yes,v in g if not yes];primary=bool(t and c and all(v is not None for _,v in g));assert x.primary==primary;assert x.joint==len(t) and x.onset_only==len(c);assert x.joint_unknown==sum(v is None for v in t) and x.onset_only_unknown==sum(v is None for v in c)
 for i,m in enumerate(M):
  tv=fmean(v[i] for v in t) if primary else float('nan');cv=fmean(v[i] for v in c) if primary else float('nan')
  assert equal(getattr(x,m+'_joint'),tv) and equal(getattr(x,m+'_onset_only'),cv) and equal(getattr(x,m+'_difference'),tv-cv)
s=pd.read_csv(O/'summary.csv',dtype={'period':str})
for x in s.itertuples():
 q=d.copy()
 for k in G:q=q[q[k]==getattr(x,k)]
 if x.period!='all':q=q[q.date.dt.year==int(x.period)]
 assert len(q)==x.dates;q=q[q.primary];assert len(q)==x.complete_paired_dates
 for m in M:assert equal(getattr(x,m+'_difference'),fmean(q[m+'_difference']) if len(q) else float('nan'))
 assert x.stability_eligible==(q.date.dt.to_period('M').nunique()>=24 and q.date.dt.year.nunique()>=3)
result=dict(status='PASS',observations=len(a),unique_complete_paths=len(risk),date_contrasts=len(d),summary_rows=len(s),verifier_sha256=sha(Path(__file__)),limitation='Risk arrays reused from independently raw-price-verified R291; this round independently recomputes primitives and joins, not all raw price paths')
(O/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
