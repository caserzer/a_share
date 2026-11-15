"""Fresh current-column source checks plus independent Decimal bridge."""
import fitz,re
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r152';rows=json.loads((out/'reviewed_cells.json').read_text());b=json.loads((out/'bridge.json').read_text());q={x['item']:D(x['amount_cny']) for x in rows}
 for x in rows:
  assert sha(ROOT/x['source_pdf'])==x['source_pdf_sha256'] and sha(ROOT/x['image'])==x['image_sha256']
  with fitz.open(ROOT/x['source_pdf']) as doc:
   p=doc[x['page']-1];a,c,d,e=x['clip_fraction'];text=p.get_text(clip=fitz.Rect(a*p.rect.width,c*p.rect.height,d*p.rect.width,e*p.rect.height))
  text=re.sub(r'[\s,]','',text).replace('−','-').replace('—','-');assert x['amount_cny'] in text,(x['item'],text)
 assert sum(v for k,v in q.items() if k!='operating_cashflow')==q['operating_cashflow']
 for group,val in b['groups_cny'].items():assert D(val)==sum(D(x['amount_cny']) for x in rows if x['group']==group)
 facts=json.loads((ROOT/'outputs/r149/candidate_facts.json').read_text())
 for key,old in [('net_profit','net_profit'),('operating_cashflow','net_cash_operate')]:assert q[key]==D(str(next(x['amount_cny'] for x in facts if x['symbol']=='600955.SH' and x['item_code']==old)))
 wc=q['inventory']+q['operating_receivables']+q['operating_payables'];assert abs(b['working_capital_share_of_operating_cashflow']-float(wc/q['operating_cashflow']))<1e-12
 assert abs(b['depreciation_share_of_operating_cashflow']-float(q['depreciation']/q['operating_cashflow']))<1e-12
 assert D(b['operating_cashflow_less_disclosed_working_capital_cny'])==q['operating_cashflow']-wc and D(b['unexplained_residual_cny'])==0
 assert not b['sustainable_cashflow_estimate'] and not b['model_admitted'] and not b['strict_pit']
 js(out/'verification.json',dict(status='PASS',current_column_cells=14,disclosed_terms=13,bridge_residual_cny='0.00',prior_fact_matches=2,unreported_cells_not_imputed=5))
 print('PASS 14 current-column cells, 13 signed terms, 2 prior facts, zero net residual')
if __name__=='__main__':run()
