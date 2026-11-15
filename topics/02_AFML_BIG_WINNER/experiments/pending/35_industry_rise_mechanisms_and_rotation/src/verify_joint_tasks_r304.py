from pathlib import Path
import json,hashlib,math
from collections import Counter
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'outputs/r304';K=['era','level','industry_code','date']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
r=read(O/'receipt.json')
for p,h in r['inputs'].items():assert sha(R/p)==h
for p,h in r['outputs'].items():assert sha(O/p)==h
sources=[]
for task,round_ in [('onset',253),('reversal',286)]:
 d=pd.read_parquet(R/f'outputs/r{round_}/scores.parquet');d=d[d.variant=='base'];lookup={}
 for x in d.itertuples(index=False):
  key=tuple(getattr(x,k) for k in K)
  eligible=x.past_excess20<=0 if task=='onset' else x.past_excess60>0 and x.mom60>0
  y=None if pd.isna(x.excess20) or (task=='reversal' and pd.isna(x.rel_trough20)) else int(x.return20>=.05 and x.excess20>=.03) if task=='onset' else int(x.rel_trough20<=-.08)
  assert eligible==x.eligible;assert (pd.isna(x.y) if y is None else x.y==y);lookup[key]=(eligible,y)
 sources.append(lookup)
common=sources[0].keys()&sources[1].keys();dual={k for k in common if sources[0][k][0] and sources[1][k][0]};labels=Counter((sources[0][k][1],sources[1][k][1]) for k in dual)
a=[]
for i,round_ in enumerate([253,287]):
 d=pd.read_parquet(R/f'outputs/r{round_}/alerts.parquet',columns=K+['variant','strategy']);s=set()
 for t in d.itertuples(index=False,name=None):
  assert t[:4] in sources[i] and sources[i][t[:4]][0];s.add(t)
 assert len(s)==len(d);a.append(s)
both=a[0]&a[1];paired=pd.read_parquet(O/'paired_alerts.parquet');actual=set(paired.loc[paired.alert_presence=='both',K+['variant','strategy']].itertuples(index=False,name=None));assert actual==both
assert set(paired[K+['variant','strategy']].itertuples(index=False,name=None))==a[0]|a[1]
# Full identity check, not only aggregate agreement.
pairs=pd.read_parquet(O/'paired_dates.parquet');assert set(pairs[K].itertuples(index=False,name=None))==sources[0].keys()|sources[1].keys()
for x in pairs.itertuples(index=False):
 k=tuple(getattr(x,c) for c in K)
 if k in common:
  assert x.coverage=='both';e=('onset' if sources[0][k][0] else 'no_onset')+'__'+('reversal' if sources[1][k][0] else 'no_reversal');assert x.eligibility==e
  for i,field in enumerate(['onset_label','reversal_label']):assert getattr(x,field)==('unknown' if sources[i][k][1] is None else str(sources[i][k][1]))
s=read(O/'summary.json');assert s['common_dates']==len(common);assert s['dual_eligible_dates']==len(dual);assert s['dual_both_positive']==labels[1,1];assert s['simultaneous_alert_rows']==len(both);assert s['simultaneous_unique_dates']==len({x[:4] for x in both})
result=dict(status='PASS',source_labels_reconstructed=sum(map(len,sources)),common_dates=len(common),dual_dates=len(dual),simultaneous_alerts=len(both),nine_cells=[dict(onset_label='unknown' if a is None else a,reversal_label='unknown' if b is None else b,rows=labels[a,b]) for a in [0,1,None] for b in [0,1,None]],verifier_sha256=sha(Path(__file__)))
(O/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
