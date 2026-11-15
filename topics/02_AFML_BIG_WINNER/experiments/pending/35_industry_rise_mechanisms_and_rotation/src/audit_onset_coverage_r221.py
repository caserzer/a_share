from common import *
import pandas as pd
out=ROOT/'outputs/r221';rows=[];reads=[]
for rnd in [196,199,200,201]:
 path=ROOT/f'outputs/r{rnd}/fold_ledger.json';reads.append(path);d=pd.DataFrame(json.loads(path.read_text()));d=d[d.task.eq('onset')];d['source_round']=rnd;rows.append(d)
d=pd.concat(rows,ignore_index=True);s=d.groupby(['source_round','horizon','status','reason'],dropna=False).size().reset_index(name='ledger_records');s.to_csv(out/'qualification_coverage.csv',index=False);p=pd.read_parquet(out/'actions.parquet');fit_h=sorted(d[d.status.eq('fit')].horizon.unique().tolist());assert sorted(p.horizon.unique().tolist())==fit_h;js(out/'coverage_verification.json',dict(status='PASS',available_prediction_horizons=fit_h,scope='Recorded original folds only; failed models not fabricated, method folds not independent',inputs={str(x):sha(x) for x in reads},output_sha256=sha(out/'qualification_coverage.csv'),script_sha256=sha(__file__)));print(s.to_string(index=False))
