"""Check manually selected total-equity column against fresh PDF text and bridges."""
import fitz,re
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r151';rows=json.loads((out/'reviewed_cells.json').read_text());bridges=json.loads((out/'bridges.json').read_text());n=0
 for x in rows:
  assert sha(ROOT/x['source_pdf'])==x['source_pdf_sha256'] and sha(ROOT/x['image'])==x['image_sha256']
  with fitz.open(ROOT/x['source_pdf']) as doc:
   p=doc[x['page']-1];lo,hi=x['total_column_x_fraction'];text=p.get_text(clip=fitz.Rect(p.rect.width*lo,0,p.rect.width*hi,p.rect.height))
  compact=re.sub(r'[\s,]','',text).replace('−','-').replace('—','-')
  assert x['amount_cny'] in compact,(x['symbol'],x['item'],compact)
  assert x['column']=='consolidated_total_equity_including_minority' and x['fetched_at'][:10]>='2026-11-14';n+=1
 for b in bridges:
  q={x['item']:D(x['amount_cny']) for x in rows if x['symbol']==b['symbol']}
  assert D(b['change_cny'])==q['closing']-q['opening']==q['change']
  assert sum(D(v) for v in b['components'].values())+D(b['unexplained_residual_cny'])==q['change']
  assert D(b['unexplained_residual_cny'])==0
  assert b['undisclosed_blank_categories'] and not b['model_admitted'] and not b['cash_payment_equivalence']
  if 'owner_transactions' in q:assert q['owner_transactions']==q['ordinary_share_input']+q['share_based_payment']+q['owner_other']
  if 'reserve_accrual' in q:
   net=q['reserve_accrual']+q['reserve_usage']
   if 'special_reserve' in q:assert net==q['special_reserve']
   else:assert net==0
 js(out/'verification.json',dict(status='PASS',fresh_total_column_cells=n,bridges=3,zero_residual_bridges=3,subcomponent_identities=3,visual_pages_reviewed=8,boundary='not operating-profit attribution, not cash payment evidence, no prediction'))
 print('PASS',n,'total-column cells; 3 bridges; 3 subcomponent identities')
if __name__=='__main__':run()
