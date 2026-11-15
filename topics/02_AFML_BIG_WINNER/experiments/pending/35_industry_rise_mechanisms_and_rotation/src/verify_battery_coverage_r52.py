import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r52';rec=json.loads((out/'coverage_summary.json').read_text())
 for p,h in rec['inputs'].items():assert sha(p)==h
 rows=json.loads((out/'signal_coverage.json').read_text());features=json.loads((ROOT/'outputs/r51/frozen_monthly_series.json').read_text())
 for x in rows:
  date=pd.Timestamp(x['date']);valid=[]
  for f in features:
   if not f['growth_available_at']:continue
   age=(date.year-int(f['month'][:4]))*12+date.month-int(f['month'][5:])
   if pd.Timestamp(f['growth_available_at'])<=date and age in [0,1,2]:valid.append(f)
  if valid:
   q=sorted(valid,key=lambda f:f['month'])[-1];assert x['economic_month']==q['month'] and x['log_yoy']==q['log_yoy']
  else:assert x['log_yoy'] is None
 changes=json.loads((out/'selection_changes.json').read_text());assert len(changes)==4
 assert {x['after']['date'] for x in changes}=={'2025-10-31T00:00:00','2025-11-28T00:00:00'}
 js(out/'verification.json',dict(status='PASS',time_selection_checks=len(rows),changed_rows=4,additional_complete_dates_per_level=1,no_outcomes_read=True))
 print('R52 VERIFIED',len(rows),'selections')
if __name__=='__main__':run()
