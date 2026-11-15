import gzip,re,math
import pandas as pd
from bs4 import BeautifulSoup
from common import *
def run():
 out=ROOT/'outputs/r60';source=ROOT/'outputs/r51/frozen_monthly_series.json';review=out/'reviewed_additions.json';rows=json.loads(source.read_text());old=json.loads(source.read_text());adds=json.loads(review.read_text());inputs=[source,review,ROOT/'protocols/r60.json',Path(__file__)]
 for x in adds:
  raw=Path(x['raw_path']);assert sha(raw)==x['raw_sha256'];inputs.append(raw);data=raw.read_bytes();data=gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data;t=re.sub(r'\s+','',BeautifulSoup(data,'html.parser').get_text(' ',strip=True))
  for k in ['month_evidence','value_evidence','date_evidence']:assert re.sub(r'\s+','',x[k]) in t
  assert x['month'] not in {y['month'] for y in rows};available=pd.Timestamp(x['page_date']).normalize()+pd.Timedelta(days=1);assert available>pd.Period(x['month'],'M').end_time
  rows.append(dict(month=x['month'],value_gwh=x['value_gwh'],page_date=x['page_date'],available_at=available.isoformat(),url=x['url'],raw_sha256=x['raw_sha256'],log_yoy=None))
 by={x['month']:x for x in rows}
 for x in rows:
  if x.get('log_yoy') is not None:continue
  prior=str(int(x['month'][:4])-1)+x['month'][4:];p=by.get(prior)
  x.update(prior_month=prior,prior_gwh=p['value_gwh'] if p else None,prior_sha256=p['raw_sha256'] if p else None,log_yoy=math.log(x['value_gwh']/p['value_gwh']) if p else None,growth_available_at=max(x['available_at'],p['available_at']) if p else None)
 rows.sort(key=lambda x:x['month']);assert [x['month'] for x in rows]==list(pd.period_range('2020-01','2026-09',freq='M').astype(str));js(out/'frozen_monthly_series.json',rows)
 changes=[dict(month=x['month'],before=next((y for y in old if y['month']==x['month']),None),after=x) for x in rows if next((y for y in old if y['month']==x['month']),None)!=x];js(out/'changes.json',changes)
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},months=len(rows),yoy_months=sum(x['log_yoy'] is not None for x in rows),added_months=len(adds),series_sha256=sha(out/'frozen_monthly_series.json'),status='complete_month_grid_historical_proxy_not_PIT',old_models_preserved=True))
 current=json.loads((ROOT/'outputs/current_sources.json').read_text());current['selected']['reviewed_complete_battery_series']=dict(path='outputs/r60/frozen_monthly_series.json',sha256=sha(out/'frozen_monthly_series.json'));js(ROOT/'outputs/current_sources.json',current)
 print('R60',len(rows),'months',sum(x['log_yoy'] is not None for x in rows),'YoY',len(changes),'changed/new records')
if __name__=='__main__':run()
