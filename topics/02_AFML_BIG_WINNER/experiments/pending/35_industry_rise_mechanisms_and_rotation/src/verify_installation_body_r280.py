from common import *
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from decimal import Decimal,localcontext
import gzip,re,math

def interval(s):
 v=Decimal(s);unit=Decimal(10)**v.as_tuple().exponent;return v-unit/2,v+unit/2

def run():
 o=ROOT/'outputs/r280';rows=json.loads((o/'records.json').read_text());source=json.loads((ROOT/'outputs/r60/frozen_monthly_series.json').read_text());lookup={r['month']:r for r in source};selectors=json.loads((ROOT/'protocols/r274.json').read_text())['selectors'];quotes=0;pairs=0
 for r in rows:
  x=lookup[r['month']];path=ROOT/'data/r38_battery_originals'/f"{x['raw_sha256']}.html";assert sha(path)==x['raw_sha256'];raw=path.read_bytes();soup=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');host=urlparse(x['url']).netloc;nodes=soup.select('.News-Content > div:first-child' if host=='www.aqsiqauto.com' else selectors[host]);assert len(nodes)==1;body=nodes[0].get_text(' ',strip=True);assert body==(ROOT/f"outputs/r275/bodies/{r['month']}.txt").read_text();text=''.join(body.split())
  assert r['matches'] and r['status']=='matches_frozen_value'
  for a in r['matches']:
   q=text[a['start']:a['end']];assert q==a['quote'];assert '动力电池装车量' in q and ('我国' in q or '国内' in q);assert '累计' not in q;assert '三元' not in q and '铁锂' not in q;assert float(a['amount_token'])==x['value_gwh'];assert re.search(r'(?<!\d)'+str(int(r['month'][-2:]))+r'月份?',q);assert q.endswith(a['amount_token']+'GWh');quotes+=1
  if r['growth_reproduced']:
   prior=lookup[x['prior_month']];assert abs((math.log(x['value_gwh'])-math.log(prior['value_gwh']))-x['log_yoy'])<1e-12;assert x['prior_sha256']==prior['raw_sha256'];assert x['growth_available_at']==max(x['available_at'],prior['available_at'])
  if r['annual_status']!='missing_prior_or_rate':
   with localcontext() as ctx:
    ctx.prec=40;c0,c1=interval(r['current_amount_token']);p0,p1=interval(r['prior_amount_token']);y0,y1=interval(r['reported_rate_token']);y0/=100;y1/=100;implied0=c0/(1+y1);implied1=c1/(1+y0);ok=max(p0,implied0)<=min(p1,implied1);assert ok==(r['annual_status']=='rounding_compatible');pairs+=1
 receipt=json.loads((o/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(ROOT/f)==h
 for f,h in receipt['outputs'].items():assert sha(o/f)==h
 js(o/'independent_verification.json',dict(status='PASS',original_documents=len(rows),national_current_month_quotes=quotes,annual_arithmetic_checks=69,independent_rounding_pairs=pairs,scope='Original corrected DOM identity, monthly national amount and69 frozen growth/hash/clock records, alternative Decimal denominator intervals; not first-release or revision-cause certification'))
 print('PASS',len(rows),quotes,pairs)
if __name__=='__main__':run()
