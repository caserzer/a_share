import pandas as pd
from common import *
from battery_evidence_r35 import BASE

def run():
 out=ROOT/'outputs/r35';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 s=json.loads((BASE/'state.json').read_text());ev=[json.loads(x) for x in (BASE/'evidence.jsonl').read_text().splitlines() if x.strip()];lookup={d['document_id']:d for d in s['documents']};a=pd.read_csv(out/'evidence_audit.csv');assert len(a)==len(ev)==218
 for e in ev:
  row=a[a.evidence_id.eq(e['evidence_id'])];assert len(row)==1;row=row.iloc[0];d=lookup[e['document_id']];assert row.document_id==d['document_id']
  eff=pd.to_datetime(e.get('effective_at'),utc=True);pub=pd.to_datetime(d.get('published_at'),utc=True);assert row.effective_before_publication==bool(pd.notna(eff) and pd.notna(pub) and eff<pub)
 c=pd.read_csv(out/'monthly_installation_leads.csv');assert not c.numeric_factor_eligible.any();assert set(c.month)=={'2026-08','2026-09'}
 expected={'2026-08':(79.0,2),'2026-09':(87.2,3)}
 for month,(value,count) in expected.items():
  z=c[c.month.eq(month)];assert len(z)==count and z.value.eq(value).all() and z.url.nunique()==1 and z.content_hash.isna().all()
 assert receipt['summary']['effective_before_publication']==9 and receipt['summary']['eligible_predictive_series']==0
 js(out/'verification.json',dict(status='PASS',all_evidence_refs_checked=len(ev),monthly_quote_rows=5,distinct_months=2,limitation='verifies local assertions and join/clock rules only, not external factual accuracy'))
 print('R35 VERIFIED 218 references; five quotes collapse to two months')
if __name__=='__main__':run()
