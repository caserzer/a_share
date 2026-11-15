"""Extend local cashflow reconciliation to all ten issuers, bank separately."""
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r153';rows=json.loads((out/'reviewed_cells.json').read_text());facts=json.loads((ROOT/'outputs/r149/candidate_facts.json').read_text());results=[]
 for sym in sorted({x['symbol'] for x in rows}):
  q=[x for x in rows if x['symbol']==sym];values={x['item']:D(x['amount_cny']) for x in q if x['amount_cny'] is not None};groups={}
  for x in q:
   if x['amount_cny'] is not None and x['group']!='total':groups[x['group']]=groups.get(x['group'],D(0))+D(x['amount_cny'])
  prior={x['item_code']:D(str(x['amount_cny'])) for x in facts if x['symbol']==sym};total=values['operating_cashflow'];profit=values['net_profit'];assert total==prior['net_cash_operate']
  results.append(dict(symbol=sym,issuer_type='bank' if sym=='002948.SZ' else 'nonbank',reported_operating_cashflow_cny=str(total),consolidated_net_profit_cny=str(profit),parent_attributable_net_profit_cny=str(prior['net_profit']),consolidated_minus_parent_profit_cny=str(profit-prior['net_profit']),groups_cny={k:str(v) for k,v in groups.items()},unexplained_residual_cny=str(total-sum(groups.values())),reported_cells=sum(x['amount_cny'] is not None for x in q),null_cells=[x['item'] for x in q if x['amount_cny'] is None],strict_pit=False,model_admitted=False,cross_sector_quality_rank=False))
 js(out/'bridges.json',results);js(out/'receipt.json',dict(status='LOCAL_COVERAGE_AND_RECONCILIATION',issuers=len(results),reported_cells=sum(x['reported_cells'] for x in results),new_visual_pages=15,reused_visual_pages=2,source_scope='same ten existing PDFs',inputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'reviewed_cells.json',ROOT/'outputs/r149/candidate_facts.json',ROOT/'outputs/r152/unreported_cells.json',ROOT/'protocols/r153.json']},outputs={'bridges.json':sha(out/'bridges.json')}))
 for x in results:print(x['symbol'],'CFO',x['reported_operating_cashflow_cny'],'RESIDUAL',x['unexplained_residual_cny'],'WC',x['groups_cny'].get('working_capital'),'PROFIT_BASIS_DIFF',x['consolidated_minus_parent_profit_cny'])
if __name__=='__main__':run()
