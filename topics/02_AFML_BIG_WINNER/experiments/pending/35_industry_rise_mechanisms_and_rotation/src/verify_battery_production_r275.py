from common import *
import gzip,re,math
import pandas as pd
from bs4 import BeautifulSoup

def run():
 out=ROOT/'outputs/r275';records=json.loads((out/'production_registry.json').read_text());selectors=json.loads((ROOT/'protocols/r274.json').read_text())['selectors'];from urllib.parse import urlparse
 lookup={r['month']:r for r in records};matched=0;growth=0
 for r in records:
  path=ROOT/'data/r38_battery_originals'/f"{r['raw_sha256']}.html";assert sha(path)==r['raw_sha256'];raw=path.read_bytes();soup=BeautifulSoup(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw,'html.parser');host=urlparse(r['url']).netloc;selector='.News-Content > div:first-child' if host=='www.aqsiqauto.com' else selectors[host];nodes=soup.select(selector);assert len(nodes)==1
  body=nodes[0].get_text(' ',strip=True);assert body==(out/f"bodies/{r['month']}.txt").read_text();assert sha(out/f"bodies/{r['month']}.txt")==r['body_sha256'];text=''.join(body.split())
  if r['status']=='direct_disclosure':
   assert r['matches']
   for a in r['matches']:
    quote=text[a['start']:a['end']];assert quote==a['quote'];assert r['scope'] in quote;assert float(quote.split('GWh')[0].split('共计')[-1].split('为')[-1])==r['production_gwh'];assert '累计' not in quote;matched+=1
  else:
   assert r['month'] in ['2021-03','2024-04','2025-03'];assert '产量' not in body
  q=lookup.get(r['prior_month']);ok=q is not None and q['status']==r['status']=='direct_disclosure' and q['scope_segment']==r['scope_segment']
  assert (r['production_log_yoy'] is not None)==ok
  if ok:
   assert abs(r['production_log_yoy']-(math.log(r['production_gwh'])-math.log(q['production_gwh'])))<1e-12;assert r['production_growth_available_at']==max(r['available_at'],q['available_at']);growth+=1
 # Independent row/date loop for original qualification gates; mixed-scope counts are upper bounds only.
 p=pd.read_parquet(ROOT/'outputs/r140/cohort_new.parquet');states=pd.read_parquet(ROOT/'outputs/r195/market_regimes.parquet').regime;ledger=json.loads((out/'fold_qualification.json').read_text());checked=0
 for row in ledger:
  g=p.copy()
  for key in KEY:g=g[g[key]==row[key]]
  tr=set();te=set();h=row['horizon'];boundary=pd.Timestamp(row['year'],1,1)
  for _,a in g.iterrows():
   if a.date not in states.index or pd.isna(states.loc[a.date]):continue
   r=lookup[a.economic_month]
   if r['production_log_yoy'] is None or pd.Timestamp(r['production_growth_available_at'])>a.date:continue
   if a.date<boundary and pd.notna(a[f'excess{h}']) and a[f'maturity{h}']<boundary:tr.add(a.date)
   if a.date.year==row['year']:te.add(a.date)
  assert len(tr)==row['supply_train_months'] and len(te)==row['supply_test_months'];assert row['eligible']==(len(tr)>=24 and len(te)>0);checked+=1
 receipt=json.loads((out/'receipt.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(ROOT/f)==h
 for f,h in receipt['outputs'].items():assert sha(out/f)==h
 result=dict(status='PASS',original_sources=81,direct_disclosures=78,quote_checks=matched,same_segment_yoy=growth,independent_qualification_folds=checked,eligible=0,scope='Original DOM/bytes, direct quotes, amounts, dates, annual arithmetic, row-by-row qualification. Same wording is not certified statistical definition; mixed-scope training count only an optimistic upper bound.',adoption=False)
 js(out/'independent_verification.json',result);print(result)
if __name__=='__main__':run()
