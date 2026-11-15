from common import *
import pandas as pd
out=ROOT/'outputs/r220';rows=[];reads=[]
for rnd in [196,199,200,201]:
 path=ROOT/f'outputs/r{rnd}/fold_ledger.json';reads.append(path);d=pd.DataFrame(json.loads(path.read_text()));d=d[d.task.eq('reversal')];d['source_round']=rnd;rows.append(d)
d=pd.concat(rows,ignore_index=True);s=d.groupby(['source_round','horizon','status','reason'],dropna=False).size().reset_index(name='ledger_records');s.to_csv(out/'qualification_coverage.csv',index=False);assert not ((d.horizon.eq(60))&d.status.eq('fit')).any();p=pd.read_parquet(out/'actions.parquet');assert set(p.horizon)=={20};js(out/'coverage_verification.json',dict(status='PASS',available_prediction_horizons=[20],sixty_day_fitted_ledger_records=0,scope='Original recorded folds only; method folds not independent, R196 follows original available model registry',inputs={str(x):sha(x) for x in reads},output_sha256=sha(out/'qualification_coverage.csv'),script_sha256=sha(__file__)))
