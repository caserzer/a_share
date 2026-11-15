from common import *
from battery_validation_status_r282 import audit
from datetime import datetime,timezone
import tempfile
import pandas as pd

def run():
 path=ROOT/'protocols/r282.json';now=datetime.now(timezone.utc).isoformat();actual=audit(path,now);o=ROOT/'outputs/r282';js(o/'current_status.json',actual)
 distant=audit(path,'2030-01-01T00:00:00Z');assert actual['rows']==distant['rows'];assert all(x['independent_prospective_rows']==0 for x in actual['rows'])
 rejected=[]
 for cutoff in ['2026-11-14','2020-01-01T00:00:00Z']:
  try:audit(path,cutoff)
  except ValueError as e:rejected.append(str(e))
  else:raise AssertionError('expected refusal')
 c=json.loads(path.read_text());c['frozen_inputs']['outputs/r281/models.json']='0'*64
 with tempfile.TemporaryDirectory() as tmp:
  test=Path(tmp)/'contract.json';js(test,c)
  try:audit(test,now)
  except ValueError as e:rejected.append(str(e))
  else:raise AssertionError('expected hash refusal')
 p=pd.read_parquet(ROOT/'outputs/r281/predictions.parquet');checks=0
 for row in actual['rows']:
  d=p[p.horizon==row['horizon']];valid=[r for r in d.to_dict('records') if pd.notna(r['target']) and pd.notna(r['maturity']) and pd.Timestamp(r['maturity'],tz='Asia/Shanghai')<=pd.Timestamp(now)]
  assert len(valid)==row['archived_evaluable_rows'];assert len({r['date'] for r in valid})==row['archived_evaluable_months'];checks+=len(d)
 models=json.loads((ROOT/'outputs/r281/models.json').read_text());assert len(models)==120 and {m['year'] for m in models}=={2026}
 js(o/'verification.json',dict(status='PASS',real_as_of=now,independent_rows_counted=checks,models_frozen=len(models),refusal_cases=rejected,future_cutoff_does_not_fabricate_evidence=True,scope='Current archive eligibility and freeze/hash handling only; not future ingestion, execution or prospective performance certification'))
 print('PASS',checks,len(rejected))
if __name__=='__main__':run()
