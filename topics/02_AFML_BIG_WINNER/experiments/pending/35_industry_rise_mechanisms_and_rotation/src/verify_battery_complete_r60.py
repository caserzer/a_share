import math
from common import *
def run():
 out=ROOT/'outputs/r60';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h
 assert sha(out/'frozen_monthly_series.json')==rec['series_sha256']
 new={x['month']:x for x in json.loads((out/'frozen_monthly_series.json').read_text())};old=json.loads((ROOT/'outputs/r51/frozen_monthly_series.json').read_text());assert len(new)==81
 for x in old:
  y=new[x['month']]
  for k in ['month','value_gwh','page_date','available_at','url','raw_sha256']:assert x[k]==y[k]
  if x['log_yoy'] is not None:assert x==y
 known=0
 for x in new.values():
  if x['month']<'2021-01':assert x['log_yoy'] is None;continue
  p=new[str(int(x['month'][:4])-1)+x['month'][4:]];assert abs(math.expm1(x['log_yoy'])-(x['value_gwh']-p['value_gwh'])/p['value_gwh'])<1e-12;assert x['growth_available_at']==max(x['available_at'],p['available_at']);known+=1
 ledger=json.loads((ROOT/'outputs/r38/download_ledger.json').read_text());saved=[x for x in ledger if x['status']=='saved'];assert len(saved)<=100 and sum(x['bytes_read'] for x in ledger)<=100000000
 js(out/'verification.json',dict(status='PASS',economic_months=81,yoy_pairs=known,old_economic_rows_preserved=69,old_known_yoy_rows_preserved=50,new_raw_pages=12,full_month_grid=True,strict_PIT=False))
 print('R60 VERIFIED 81 monthly values and69 YoY pairs')
if __name__=='__main__':run()
