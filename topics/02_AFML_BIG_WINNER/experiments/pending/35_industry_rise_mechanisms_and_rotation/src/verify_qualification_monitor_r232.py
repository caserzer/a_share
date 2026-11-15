from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r232';d=pd.read_parquet(out/'qualification_records.parquet');checked=0
 for path,g in d.groupby('source_path'):
  p=ROOT/path;original=pd.read_parquet(p).to_dict('records') if p.suffix=='.parquet' else json.loads(p.read_text());assert len(g)==len(original);assert sorted(g.source_row.tolist())==list(range(len(original)))
  for row in g.to_dict('records'):
   raw=json.loads(json.dumps(original[row['source_row']],default=str));assert json.loads(row['raw_record'])==raw;assert row['fit_gate_passed']==(raw.get('status')=='fit');train=next((raw[k] for k in ['state_fit_dates','state_train_months'] if k in raw),None);cal=raw.get('state_cal_dates')
   for state in ['down_low','down_high','up_low','up_high']:
    for prefix,mapping in [('train_',train),('cal_',cal)]:
     value=row[prefix+state]
     if mapping is None:assert pd.isna(value)
     else:assert value==mapping.get(state,0)
   assert not row['adoption'];checked+=1
 families=json.loads((out/'family_qualification.json').read_text())['families'];expected={x['family'] for x in json.loads((ROOT/'outputs/r195/experiment_registry.json').read_text())['families']};assert {x['family'] for x in families}==expected
 for f in families:
  z=d[d.families.map(lambda x:f['family'] in json.loads(x))];assert len(z)==f['records'] and int(z.fit_gate_passed.sum())==f['fit_gate_records'] and z.source_status.value_counts().to_dict()==f['status_counts']
 # R208 is an independent preexisting normalization of the classifier state ledger.
 source=pd.read_csv(ROOT/'outputs/r208/state_support.csv');fit=source[source.status.eq('fit')];c=json.loads((out/'classifier_support.json').read_text());assert len(fit)==c['state_slots'];assert int(fit.state_cal_dates.eq(0).sum())==c['zero_calibration_state_slots']
 js(out/'independent_verification.json',dict(status='PASS',raw_records=checked,families=len(families),classifier_state_slots=len(fit),zero_calibration_slots=int(fit.state_cal_dates.eq(0).sum()),scope='Every raw record and count against source; null-vs-zero checks; all-family summary totals; independent R208 classifier support crosscheck',inputs={str(ROOT/'outputs/r208/state_support.csv'):sha(ROOT/'outputs/r208/state_support.csv')},code_sha256=sha(__file__)))
 print(checked,len(families),len(fit),int(fit.state_cal_dates.eq(0).sum()))
if __name__=='__main__':run()
