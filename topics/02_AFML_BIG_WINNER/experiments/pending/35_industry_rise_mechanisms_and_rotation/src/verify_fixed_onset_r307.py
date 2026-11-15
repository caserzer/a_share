from pathlib import Path
from collections import defaultdict
from statistics import fmean
import json,hashlib
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'outputs/r307';K=['era','level','industry_code','date'];G=['era','level','strategy'];V=['base','state','interaction'];M=['terminal_return','terminal_excess','worst_absolute_shortfall','mean_absolute_shortfall','worst_relative_shortfall','onset_hit','reversal_hit']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def eq(a,b):return (pd.isna(a) and pd.isna(b)) or abs(a-b)<1e-12
receipt=json.loads((O/'receipt.json').read_text())
for p,h in receipt['inputs'].items():assert sha(R/p)==h
for p,h in receipt['outputs'].items():assert sha(O/p)==h
source=pd.read_parquet(R/'outputs/r306/alert_observations.parquet');source=source[source.variant=='base'];expected={tuple(getattr(x,k) for k in K+['strategy']):x for x in source.itertuples()};rev=pd.read_parquet(R/'outputs/r287/alerts.parquet',columns=K+['strategy','variant']);lookup=set(rev.itertuples(index=False,name=None));a=pd.read_parquet(O/'fixed_observations.parquet');assert len(a)==len(expected);groups=defaultdict(list)
for x in a.itertuples():
 k=tuple(getattr(x,c) for c in K+['strategy']);old=expected[k]
 for m in M:assert eq(getattr(x,m),getattr(old,m))
 assert x.complete_path==old.complete_path
 for v in V:assert getattr(x,'alert_'+v)==(k+(v,) in lookup)
 groups[tuple(getattr(x,c) for c in G+['date'])].append(x)
contrasts={};support={}
for k,g in groups.items():
 allknown=all(x.complete_path for x in g);both={v:any(getattr(x,'alert_'+v) for x in g) and any(not getattr(x,'alert_'+v) for x in g) for v in V};support[k]=allknown and all(both.values())
 for v in V:
  t=[x for x in g if getattr(x,'alert_'+v)];c=[x for x in g if not getattr(x,'alert_'+v)];contrasts[k+(v,)]=[fmean(getattr(x,m) for x in t)-fmean(getattr(x,m) for x in c) if allknown and both[v] else float('nan') for m in M]
d=pd.read_parquet(O/'date_contrasts.parquet');assert len(d)==3*len(groups)
for x in d.itertuples():
 k=tuple(getattr(x,c) for c in G+['date']);assert x.common_supported==support[k]
 for i,m in enumerate(M):assert eq(getattr(x,m+'_contrast'),contrasts[k+(x.variant,)][i])
p=pd.read_parquet(O/'paired_increments.parquet');assert len(p)==2*sum(support.values())
for x in p.itertuples():
 k=tuple(getattr(x,c) for c in G+['date']);assert support[k]
 for i,m in enumerate(M):assert eq(getattr(x,m+'_increment'),contrasts[k+(x.variant,)][i]-contrasts[k+('base',)][i])
s=pd.read_csv(O/'summary.csv',dtype={'period':str})
for x in s.itertuples():
 q=p[p.variant==x.variant]
 for k in G:q=q[q[k]==getattr(x,k)]
 if x.period!='all':q=q[q.date.dt.year==int(x.period)]
 assert x.common_dates==len(q)
 for m in M:assert eq(getattr(x,m+'_increment'),fmean(q[m+'_increment']) if len(q) else float('nan'))
 assert x.stability_eligible==(q.date.dt.to_period('M').nunique()>=24 and q.date.dt.year.nunique()>=3)
result=dict(status='PASS',fixed_observations=len(a),membership_checks=3*len(a),date_variant_contrasts=len(d),paired_increments=len(p),summary_rows=len(s),verifier_sha256=sha(Path(__file__)))
(O/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
