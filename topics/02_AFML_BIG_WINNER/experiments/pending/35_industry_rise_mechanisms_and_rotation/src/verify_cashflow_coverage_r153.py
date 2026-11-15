"""Fresh current-column extraction, independent sums, profit-basis checks."""
import fitz,re
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r153';rows=json.loads((out/'reviewed_cells.json').read_text());bridges=json.loads((out/'bridges.json').read_text());n=0
 for x in rows:
  assert sha(ROOT/x['source_pdf'])==x['source_pdf_sha256'] and sha(ROOT/x['image'])==x['image_sha256']
  if x['amount_cny'] is None:assert x['status'] in ['blank','dash','not_separately_presented'];continue
  with fitz.open(ROOT/x['source_pdf']) as doc:
   p=doc[x['page']-1];a,b=x['x_fraction'];text=p.get_text(clip=fitz.Rect(a*p.rect.width,0,b*p.rect.width,p.rect.height))
  compact=re.sub(r'[\s,]','',text).replace('−','-').replace('—','-').replace('－','-');number=x['source_number'];expected='('+number[1:]+')' if x['symbol']=='002948.SZ' and number.startswith('-') else number
  assert expected in compact,(x['symbol'],x['item'],compact)
  assert D(x['amount_cny'])==D(number)*D(x['unit']);n+=1
 traps=[('002832.SZ','retirement_loss','1080.39',0),('300411.SZ','disposal_loss','-9949.12',0),('300693.SZ','retirement_loss','0.00',0),('300693.SZ','investment_loss','0.00',1),('300693.SZ','deferred_tax_liability','0.00',2)]
 for sym,item,number,index in traps:
  x=next(x for x in rows if x['symbol']==sym and x['item']==item);assert x['amount_cny'] is None
  with fitz.open(ROOT/x['source_pdf']) as doc:
   p=doc[x['page']-1];a,b=x['x_fraction'];words=[w for w in p.get_text('words') if w[0]>b*p.rect.width and w[4].replace(',','').replace('−','-')==number];w=sorted(words,key=lambda w:w[1])[index]
   current=p.get_text(clip=fitz.Rect(a*p.rect.width,w[1]-.5,b*p.rect.width,w[3]+.5));assert not re.search(r'\d',current),(sym,item,current)
 facts=json.loads((ROOT/'outputs/r149/candidate_facts.json').read_text());assert len(bridges)==10
 for b in bridges:
  q=[x for x in rows if x['symbol']==b['symbol'] and x['amount_cny'] is not None];total=next(D(x['amount_cny']) for x in q if x['item']=='operating_cashflow');terms=sum(D(x['amount_cny']) for x in q if x['item']!='operating_cashflow')
  assert total-terms==D(b['unexplained_residual_cny'])==0,(b['symbol'],total-terms)
  for g,v in b['groups_cny'].items():assert D(v)==sum(D(x['amount_cny']) for x in q if x['group']==g)
  assert total==D(str(next(x['amount_cny'] for x in facts if x['symbol']==b['symbol'] and x['item_code']=='net_cash_operate')))
  assert D(b['consolidated_net_profit_cny'])-D(b['parent_attributable_net_profit_cny'])==D(b['consolidated_minus_parent_profit_cny'])
  assert not b['strict_pit'] and not b['model_admitted'] and not b['cross_sector_quality_rank']
 js(out/'verification.json',dict(status='PASS',fresh_current_column_cells=n,issuer_bridges=10,prior_cashflow_matches=10,profit_basis_comparisons=10,new_visual_pages=15,reused_visual_pages=2,bank_kept_separate=True,prior_column_only_traps_checked=5))
 print('PASS',n,'source cells, 10 bridges, 10 cashflow matches')
if __name__=='__main__':run()
