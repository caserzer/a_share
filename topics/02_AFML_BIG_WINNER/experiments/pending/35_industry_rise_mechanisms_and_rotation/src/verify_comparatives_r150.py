"""Independent fresh PyMuPDF extraction and Decimal balance/ratio verification."""
import re,fitz
from decimal import Decimal as D
from common import *

def run():
 out=ROOT/'outputs/r150';rows=json.loads((out/'reviewed_comparatives.json').read_text());facts=json.loads((ROOT/'outputs/r149/candidate_facts.json').read_text());summaries=json.loads((out/'issuer_changes.json').read_text());checks=0
 assert len(rows)==30 and len({(x['symbol'],x['item_code']) for x in rows})==30
 for x in rows:
  pdf=ROOT/x['source_pdf'];assert sha(pdf)==x['source_pdf_sha256']
  with fitz.open(pdf) as doc:text=doc[x['page']-1].get_text(sort=True)
  # Use original formatted current number from independently reviewed R149 cells.
  f=next(f for f in facts if (f['symbol'],f['item_code'])==(x['symbol'],x['item_code']))
  pairs=re.findall(re.escape(f['source_reported_number'])+r'\s+([\d,]+(?:\.\d+)?)',text)
  assert x['prior_reported'] in pairs,(x['symbol'],x['item_code'],pairs)
  assert D(x['current_cny'])==D(str(f['amount_cny']))
  assert D(x['prior_cny'])==D(x['prior_reported'].replace(',',''))*D(str(x['unit']))
  assert x['announce_date']>'2025-12-31' and x['fetched_at'][:10]>='2026-11-14'
  assert not x['strict_pit_certified'] and not x['historical_model_admitted'] and not x['prior_first_publication_verified']
  for p,h in x['review_images'].items():assert sha(ROOT/p)==h
  checks+=1
 for s in summaries:
  q={x['item_code']:x for x in rows if x['symbol']==s['symbol']}
  for field in ['current_cny','prior_cny']:
   assert abs(D(q['total_assets'][field])-D(q['total_liabilities'][field])-D(q['total_equity'][field]))<=D('.02')
  for key,item in [('asset','total_assets'),('liability','total_liabilities'),('equity','total_equity')]:
   expected=(D(q[item]['current_cny'])/D(q[item]['prior_cny'])-1)*100
   assert abs(float(expected)-s[key+'_change_pct'])<1e-10
  old=D(q['total_liabilities']['prior_cny'])/D(q['total_assets']['prior_cny'])*100;now=D(q['total_liabilities']['current_cny'])/D(q['total_assets']['current_cny'])*100
  for k,v in [('prior_liabilities_assets_pct',old),('current_liabilities_assets_pct',now),('leverage_change_pp',now-old)]:assert abs(s[k]-float(v))<1e-10
 js(out/'verification.json',dict(status='PASS',fresh_pdf_amount_pairs=checks,balance_identities=20,issuer_ratio_checks=60,strict_pit=False,model_admitted=False,scope='ten local issuer reports only; total liability ratio is not debt ratio or bank capital adequacy'))
 print('PASS',checks,'fresh PDF pairs, 20 identities, 60 ratios')
if __name__=='__main__':run()
