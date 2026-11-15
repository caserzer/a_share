from pathlib import Path
from decimal import Decimal
from collections import Counter
import json,hashlib,re,fitz
R=Path(__file__).resolve().parents[1];O=R/'outputs/r302'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cents(v):return int(Decimal(str(v))*100)
receipt=read(O/'receipt.json')
for p,h in receipt['inputs'].items():assert sha(R/p)==h,p
for p,h in receipt['outputs'].items():assert sha(O/p)==h,p
cells=read(O/'disclosed_cells.json');bridges=read(O/'bridges.json');review=read(R/'outputs/cnequity_fundamental_review_20261114/reviewed_financial_cells.json');old=read(R/'outputs/r301/comparative_cells.json')
assert len(bridges)==10 and {x['symbol'] for x in cells}=={x['symbol'] for x in bridges}
word_checks=0;profit_scope=[]
for b in bridges:
 s=b['symbol'];a,z=b['source_pages'];pdf=R/'data/cnequity_fundamental_review_20261114'/s/'2026H1.pdf';doc=fitz.open(pdf);group=[x for x in cells if x['symbol']==s]
 # Independently count all printed numbers in original full-table text; do not use main column selector.
 pages=read(pdf.parent/'pages.json');text='\n'.join(x['text'] for x in pages if a<=x['page']<=z)
 text=re.split(r'\n净利润\s',text,maxsplit=1)[1]
 text=re.split(r'经营活动产生(?:/（所用）)?的现金流量净额',text,maxsplit=1)[0]
 if b['financial']:
  nums=[]
  for line in text.splitlines():nums.extend(re.findall(r'\(?-?\d[\d,]*\)?',line)[:2])
 else:nums=re.findall(r'-?\d[\d,]*\.\d{2}',text)
 assert Counter(nums)==Counter(x['raw'] for x in group),(s,Counter(nums)-Counter(x['raw'] for x in group),Counter(x['raw'] for x in group)-Counter(nums))
 for x in group:
  words=doc[x['page']-1].get_text('words');matches=[w for w in words if w[4]==x['raw'] and abs(w[0]-x['bbox'][0])<1 and abs(w[1]-x['bbox'][1])<1];assert len(matches)==1,(s,x)
  t=x['raw'];v=Decimal(t.replace(',','').replace('(','-').replace(')',''))*b['unit_multiplier'];assert v==Decimal(x['value']);word_checks+=1
 for i,v in enumerate(b['values']):
  g=[x for x in group if x['period']==v['period']];cs={k:sum(cents(x['value']) for x in g if x['kind']==k) for k in ['consolidated_profit','inventory','operating_receivables','operating_payables','other_disclosed_adjustment']}
  assert cs['consolidated_profit']==cents(v['profit']);assert sum(cs[k] for k in ['inventory','operating_receivables','operating_payables'])==cents(v['operating_balances']);assert cs['other_disclosed_adjustment']==cents(v['other_disclosed_adjustments']);assert sum(cs.values())==cents(v['cashflow']);assert cents(v['unexplained_residual'])==0
  origin=next(x for x in (review if i==0 else old) if x['symbol']==s and x['item_code']=='net_cash_operate');assert cents(origin['item_value'] if i==0 else origin['normalized_value'])==cents(v['cashflow'])
  attr=next(x for x in (review if i==0 else old) if x['symbol']==s and x['item_code']=='net_profit');attrval=attr['item_value'] if i==0 else attr['normalized_value'];profit_scope.append(dict(symbol=s,period=v['period'],consolidated=v['profit'],attributable=str(attrval),difference_yuan=str(Decimal(v['profit'])-Decimal(str(attrval)))))
 for k,v in b['delta'].items():assert cents(v)==cents(b['values'][0][k])-cents(b['values'][1][k])
assert len(profit_scope)==20
(O/'profit_scope_comparison.json').write_text(json.dumps(profit_scope,ensure_ascii=False,indent=2)+'\n')
result=dict(status='PASS',issuers=10,period_reconciliations=20,printed_cells=word_checks,source_table_number_multisets=10,total_cashflow_source_matches=20,profit_scope_differences=sum(Decimal(x['difference_yuan'])!=0 for x in profit_scope),all_residuals_zero=True,strict_pit=False,predictive_validation=False,visual_pages=6,limitation='Text multiset completeness plus word coordinate verification uses same PDF engine, not independent OCR; six pages visually inspected, not all seventeen',verifier_sha256=sha(Path(__file__)),inputs={str(p.relative_to(R)):sha(p) for p in [O/'receipt.json',O/'disclosed_cells.json',O/'bridges.json',O/'profit_scope_comparison.json']})
(O/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
