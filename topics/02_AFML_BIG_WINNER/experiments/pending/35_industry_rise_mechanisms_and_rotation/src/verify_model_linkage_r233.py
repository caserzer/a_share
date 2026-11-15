from common import *
import pandas as pd
from collections import Counter
from model_linkage_r233 import BASE,MODEL

def run():
 out=ROOT/'outputs/r233';link=pd.read_csv(out/'model_linkage.csv');coverage=pd.read_csv(out/'gate_output_coverage.csv');snap=json.loads((out/'historical_snapshot_2026-09-30.json').read_text());snapshot={(x['source_round'],)+tuple(x[k] for k in MODEL):x for x in snap['models']};total=0;checked=0
 for rnd in [196,199,200,201]:
  p=pd.read_parquet(ROOT/f'outputs/r{rnd}/predictions.parquet',columns=MODEL+['date']);counts=Counter(p[MODEL].itertuples(index=False,name=None));at=Counter(p[p.date.eq(pd.Timestamp('2026-09-30'))][MODEL].itertuples(index=False,name=None));models=json.loads((ROOT/f'outputs/r{rnd}/models.json').read_text());assert set(counts)=={tuple(x[k] for k in MODEL) for x in models};z=link[link.source_round.eq(rnd)];assert len(z)==len(models)
  for row in z.to_dict('records'):
   key=tuple(row[k] for k in MODEL);assert row['prediction_rows']==counts[key]
   if at[key]:assert snapshot[(rnd,)+key]['exact_date_rows']==at[key]
   else:assert (rnd,)+key not in snapshot
   checked+=1
  g=json.loads((ROOT/f'outputs/r{rnd}/fold_ledger.json').read_text());z=coverage[coverage.source_round.eq(rnd)];assert len(z)==len(g);found={tuple(x[k] for k in BASE) for x in models};gate_rows={tuple(row[k] for k in BASE):row for row in z.to_dict('records')}
  for native in g:
   key=tuple(native[k] for k in BASE);row=gate_rows[key];assert row['source_status']==native['status'] and row['has_model']==(key in found)
  total+=len(p)
 js(out/'independent_verification.json',dict(status='PASS',model_records=checked,prediction_rows=total,snapshot_models=len(snapshot),scope='Independent tuple counting for every prediction/model, exact-date snapshot counts and native fold output coverage',code_sha256=sha(__file__)))
 print(checked,total,len(snapshot))
if __name__=='__main__':run()
