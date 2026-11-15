"""Reconcile issuer equity movements without treating blanks as zeros."""
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r151';cells=json.loads((out/'reviewed_cells.json').read_text());structure=json.loads((out/'reviewed_structure.json').read_text());balances=json.loads((ROOT/'outputs/r150/reviewed_comparatives.json').read_text());facts=json.loads((ROOT/'outputs/r149/candidate_facts.json').read_text());results=[]
 for sym,s in structure.items():
  q={x['item']:D(x['amount_cny']) for x in cells if x['symbol']==sym};b=next(x for x in balances if x['symbol']==sym and x['item_code']=='total_equity')
  assert q['opening']==D(b['prior_cny']) and q['closing']==D(b['current_cny'])
  known=sum(q[k] for k in s['components']);delta=q['closing']-q['opening'];assert delta==q['change']
  results.append(dict(symbol=sym,opening_cny=str(q['opening']),closing_cny=str(q['closing']),change_cny=str(delta),components={k:str(q[k]) for k in s['components']},known_component_sum_cny=str(known),unexplained_residual_cny=str(delta-known),undisclosed_blank_categories=s['blank'],comprehensive_income_share_of_net_change=float(q['comprehensive_income']/delta),r149_context={x['item_code']:x['amount_cny'] for x in facts if x['symbol']==sym and x['item_code'] in ['net_profit','net_cash_operate']},strict_pit=False,model_admitted=False,interpretation='accounting_bridge_not_causal_or_predictive',cash_payment_equivalence=False))
 js(out/'bridges.json',results)
 js(out/'receipt.json',dict(status='DESCRIPTIVE_ACCOUNTING_BRIDGES',issuer_count=3,reviewed_cells=len(cells),pages=8,inputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'reviewed_cells.json',out/'reviewed_structure.json',ROOT/'protocols/r151.json',ROOT/'outputs/r150/reviewed_comparatives.json']},outputs={'bridges.json':sha(out/'bridges.json')}))
 print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
