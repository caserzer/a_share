from pathlib import Path
import json,hashlib,zipfile
from collections import Counter
from decimal import Decimal as D
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'outputs/r303'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read(O/'receipt.json')
for p,h in r['inputs'].items():assert sha(Path(p))==h
for p,h in r['outputs'].items():assert sha(O/p)==h
archive=next(Path(p) for p in r['inputs'] if p.endswith('provider_responses.zip'));pages=read(O/'source_field_audit.json');source_rows=0
with zipfile.ZipFile(archive) as z:
 for p in pages:
  data=json.loads(z.read(p['archive_path']))['data'];assert data['fields']==p['fields'];assert len(data['items'])==p['rows'];assert not set(data['fields'])&{'n_income','minority_gain','total_profit','income_tax'};source_rows+=len(data['items'])
base=pd.read_parquet(R/'outputs/r70/member_evidence.parquet');keys=set()
for x in base.to_dict('records'):
 if x['joint_profit_known']:keys.add((x['instrument'],x['audit_period']))
u=pd.read_parquet(O/'unavailable_original_pairs.parquet');assert set(map(tuple,u[['instrument','audit_period']].to_numpy()))==keys
original=read(R/'outputs/r302/profit_scope_comparison.json');lookup={(x['symbol'],x['period']):x for x in original};s=read(O/'summary.json');rows=read(O/'fixed10_comparison.json')
for x in rows:
 a=lookup[x['symbol'],'2026H1'];b=lookup[x['symbol'],'2025H1']
 for field,label in [('consolidated','consolidated'),('attributable','attributable')]:
  delta=D(a[field])-D(b[field]);assert delta==D(x[label+'_change']);assert ('up' if delta>0 else 'down' if delta<0 else 'flat')==x[label+'_direction'];assert (D(a[field])<0)==x[label+'_current_loss']
 assert x['direction_changed']==(x['consolidated_direction']!=x['attributable_direction'])
assert s['original_income_rows']==source_rows and s['original_unique_known_pairs']==len(keys)
assert s['fixed10_direction_changes']==sum(x['direction_changed'] for x in rows)
result=dict(status='PASS',raw_response_pages=len(pages),raw_rows=source_rows,unique_pairs=len(keys),fixed10_checks=len(rows),full_cohort_conclusion='unavailable_not_unchanged',verifier_sha256=sha(Path(__file__)))
(O/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result)
