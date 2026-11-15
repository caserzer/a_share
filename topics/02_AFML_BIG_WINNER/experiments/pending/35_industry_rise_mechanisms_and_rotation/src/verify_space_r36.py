import pandas as pd
from common import *
from space_evidence_r36 import BASE

def run():
 out=ROOT/'outputs/r36';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 files=json.loads((out/'local_file_manifest.json').read_text())
 for p,h in files.items():assert sha(p)==h
 state=json.loads((BASE/'state.json').read_text());docs={x['document_id']:x for x in state['documents']};ev=[json.loads(x) for x in (BASE/'evidence.jsonl').read_text().splitlines() if x.strip()];audit=pd.read_csv(out/'evidence_audit.csv').set_index('evidence_id')
 assert len(audit)==len(ev)==221
 for e in ev:
  row=audit.loc[e['evidence_id']];d=docs[e['document_id']];assert row.document_id==d['document_id']
  pub=pd.to_datetime(d.get('published_at'),utc=True);eff=pd.to_datetime(e.get('effective_at'),utc=True);end=pd.to_datetime(e.get('period_end'),utc=True)
  assert row.effective_before_publication==bool(pd.notna(pub) and pd.notna(eff) and eff<pub)
  assert row.period_after_publication==bool(pd.notna(pub) and pd.notna(end) and end>pub)
  assert row.local_raw_hash_match==(d.get('content_hash') in files.values())
 obs=json.loads((out/'numeric_observations.json').read_text());assert len(obs)==8 and all(not x['ep35_numeric_factor_eligible'] for x in obs)
 groups={}
 for o in obs:groups.setdefault((o['metric_id'],o['entity_id'],o['normalized_unit'],o['statement_class']),set()).add(o['period_end'])
 assert len(groups)==8 and max(map(len,groups.values()))==1
 js(out/'verification.json',dict(status='PASS',all_references=221,local_files_hashed=len(files),numeric_groups=8,max_periods=1,limitation='no external fact or full-workspace source absence certification'))
 print('R36 VERIFIED',len(files),'local files; 8 single-period groups')
if __name__=='__main__':run()
