"""Audit frozen source, annual ratios, and conservative monthly availability."""
import math
import pandas as pd
from common import *

def run(round_id='r39'):
 assert round_id in ['r39','r40']
 out=ROOT/f'outputs/{round_id}';series=json.loads((out/'frozen_monthly_series.json').read_text());observations=json.loads((out/'signal_coverage.json').read_text());summary=json.loads((out/'coverage_summary.json').read_text())
 for path,digest in summary['inputs'].items():assert sha(Path(path))==digest
 by={x['month']:x for x in series};assert len(by)==len(series)
 checked=0
 for x in series:
  assert pd.Timestamp(x['available_at'])>pd.Timestamp(x['page_date'])
  lag=by.get(str(pd.Period(x['month'],'M')-12))
  if lag is None:assert x['log_yoy'] is None and x['growth_available_at'] is None;continue
  assert abs(math.exp(x['log_yoy'])*lag['value_gwh']-x['value_gwh'])<1e-10
  assert x['prior_sha256']==lag['raw_sha256']
  assert pd.Timestamp(x['growth_available_at'])==max(pd.Timestamp(x['available_at']),pd.Timestamp(lag['available_at']))
  checked+=1
 for x in observations:
  date=pd.Timestamp(x['date']);valid=[]
  for f in series:
   if f['log_yoy'] is None or pd.Timestamp(f['growth_available_at'])>date:continue
   m=pd.Timestamp(f['month']+'-01');age=(date.year-m.year)*12+date.month-m.month
   if 0<=age<=2:valid.append(f['month'])
  assert x['economic_month']==(sorted(valid)[-1] if valid else None)
  if valid:assert x['log_yoy']==by[x['economic_month']]['log_yoy']
 # A January economic period reposted in July must not become a February signal.
 assert pd.Timestamp(by['2022-01']['available_at'])>=pd.Timestamp('2022-07-02')
 assert all(not(x['economic_month']=='2022-01' and x['date']<'2022-07-02') for x in observations)
 js(out/'verification.json',dict(status='PASS',source_hashes=len(summary['inputs']),ratios_checked=checked,asof_selections_checked=len(observations),late_republication_no_backdating=True,limits='source and timing consistency; not first-release authenticity, causal or predictive validation'))
 print(round_id.upper(),'VERIFIED',checked,'ratios',len(observations),'as-of selections')

if __name__=='__main__':run()
