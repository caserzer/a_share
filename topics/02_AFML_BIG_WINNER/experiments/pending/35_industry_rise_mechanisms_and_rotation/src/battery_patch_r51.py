"""One authorized source addition; preserve R40/R50 research versions."""
import math
from bs4 import BeautifulSoup
from common import *

def run():
 out=ROOT/'outputs/r51';out.mkdir(exist_ok=True)
 source=ROOT/'outputs/r40/frozen_monthly_series.json';raw=ROOT/'data/r38_battery_originals/d8c5bfc670cd7adcaafe1eaa8b44daaaa7bb6c2229ae8686314e53feb5742baa.html'
 assert sha(raw)=='d8c5bfc670cd7adcaafe1eaa8b44daaaa7bb6c2229ae8686314e53feb5742baa'
 text=BeautifulSoup(raw.read_bytes(),'html.parser').get_text(' ',strip=True)
 assert '2025-10-15 08:51 来源：汽车动力电池联盟公众号' in text and '9月，我国动力电池装车量76.0GWh' in text
 old=json.loads(source.read_text());rows=json.loads(source.read_text());assert not any(x['month']=='2025-09' for x in rows)
 rows.append(dict(month='2025-09',value_gwh=76.0,page_date='2025-10-15 08:51',available_at='2025-10-16T00:00:00',url='https://m.mysteel.com/a/25101508/E4EB4049BA1368F5_abc.html',raw_sha256=sha(raw)))
 by={x['month']:x for x in rows}
 for x in rows:
  if x['month'] not in ['2025-09','2026-09']:continue
  prior=str(int(x['month'][:4])-1)+x['month'][4:];p=by.get(prior)
  x.update(prior_month=prior,prior_gwh=p['value_gwh'] if p else None,prior_sha256=p['raw_sha256'] if p else None,log_yoy=math.log(x['value_gwh']/p['value_gwh']) if p else None,growth_available_at=max(x['available_at'],p['available_at']) if p else None)
 rows.sort(key=lambda x:x['month']);js(out/'frozen_monthly_series.json',rows)
 changes=[dict(month=x['month'],before=next((y for y in old if y['month']==x['month']),None),after=x) for x in rows if next((y for y in old if y['month']==x['month']),None)!=x]
 js(out/'changes.json',changes);js(out/'receipt.json',dict(reads={str(p):sha(p) for p in [source,raw,Path(__file__)]},months=len(rows),yoy_known=sum(x['log_yoy'] is not None for x in rows),series_sha256=sha(out/'frozen_monthly_series.json'),status='incremental_historical_proxy_not_model_rerun',publication_note='republication page date + one day; no first-release certification',preserved=['R40 frozen series and experiment','R50 historical monitor']))
 print('R51',len(rows),'months',sum(x['log_yoy'] is not None for x in rows),'YoY; changed:',[x['month'] for x in changes])
if __name__=='__main__':run()
