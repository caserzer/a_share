from common import *
import pandas as pd
from classifier_action_uncertainty_r222 import IDENT
out=ROOT/'outputs/r222';raw=pd.read_parquet(out/'paired_dates.parquet');lookup={}
def canon(x):
 try:return str(float(x))
 except (ValueError,TypeError):return str(x)
def key(row,variant,metric):return tuple(canon(row[c]) for c in IDENT)+(pd.Timestamp(row['date']),variant,metric)
for rnd,task in [(220,'reversal'),(221,'onset')]:
 d=pd.read_csv(ROOT/f'outputs/r{rnd}/date_metrics.csv',parse_dates=['date']);d['task']=task
 for row in d.to_dict('records'):
  for metric in ['cash_policy_gain','market_policy_gain']:lookup[key(row,row['variant'],metric)]=row[metric]
d=pd.read_csv(ROOT/'outputs/r221/capacity_baseline_dates.csv',parse_dates=['date']);d['task']='onset'
for row in d.to_dict('records'):
 for metric in ['cash_selection_increment','market_selection_increment']:lookup[key(row,row['variant'],metric)]=row[metric]
maximum=0.
for row in raw.to_dict('records'):
 variant,control=row['comparison'].split('-',1);value=lookup[key(row,variant,row['metric'])]
 if control=='base':value-=lookup[key(row,'base',row['metric'])]
 assert np.isclose(value,row['delta'],atol=1e-12,equal_nan=True);err=abs(value-row['delta']);maximum=max(maximum,err if np.isfinite(err) else 0)
js(out/'independent_pair_verification.json',dict(status='PASS',dated_contrasts=len(raw),max_error=maximum,scope='Every direct contrast independently retrieved from original dated economics or capacity baseline; no placeholder fill',script_sha256=sha(__file__)));print('PASS',len(raw),maximum)
