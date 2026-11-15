import math
from common import *
def run():
 out=ROOT/'outputs/r51';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 assert sha(out/'frozen_monthly_series.json')==rec['series_sha256']
 old={x['month']:x for x in json.loads((ROOT/'outputs/r40/frozen_monthly_series.json').read_text())};new={x['month']:x for x in json.loads((out/'frozen_monthly_series.json').read_text())}
 assert len(new)==69 and set(new)-set(old)=={'2025-09'}
 for k,x in old.items():
  if k!='2026-09':assert new[k]==x
 for k in ['2025-09','2026-09']:
  x=new[k];p=new[x['prior_month']];assert abs(math.expm1(x['log_yoy'])-(x['value_gwh']-p['value_gwh'])/p['value_gwh'])<1e-14
  assert x['growth_available_at']==max(x['available_at'],p['available_at'])
 assert len(json.loads((out/'changes.json').read_text()))==2
 js(out/'verification.json',dict(status='PASS',unchanged_prior_rows=67,new_months=1,new_yoy_values=2,old_models_and_monitor_preserved=True))
 print('R51 VERIFIED 67 unchanged rows and two added YoY values')
if __name__=='__main__':run()
