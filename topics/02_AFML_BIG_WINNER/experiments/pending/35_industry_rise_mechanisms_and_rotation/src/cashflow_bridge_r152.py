"""Single issuer reported cashflow reconciliation, not a quality score."""
from decimal import Decimal as D
from common import *
def run():
 out=ROOT/'outputs/r152';rows=json.loads((out/'reviewed_cells.json').read_text());groups={};q={x['item']:D(x['amount_cny']) for x in rows}
 for x in rows:
  if x['group']!='total':groups[x['group']]=groups.get(x['group'],D(0))+D(x['amount_cny'])
 result=dict(symbol='600955.SH',period='2026H1',groups_cny={k:str(v) for k,v in groups.items()},reported_operating_cashflow_cny=str(q['operating_cashflow']),disclosed_sum_cny=str(sum(groups.values())),unexplained_residual_cny=str(q['operating_cashflow']-sum(groups.values())),working_capital_share_of_operating_cashflow=float(groups['working_capital']/q['operating_cashflow']),depreciation_share_of_operating_cashflow=float(q['depreciation']/q['operating_cashflow']),operating_cashflow_less_disclosed_working_capital_cny=str(q['operating_cashflow']-groups['working_capital']),sustainable_cashflow_estimate=False,strict_pit=False,model_admitted=False,unreported=json.loads((out/'unreported_cells.json').read_text()))
 js(out/'bridge.json',result);js(out/'receipt.json',dict(status='LOCAL_CASE_RECONCILIATION',numeric_cells=len(rows),inputs={str(p.relative_to(ROOT)):sha(p) for p in [out/'reviewed_cells.json',out/'unreported_cells.json',ROOT/'protocols/r152.json']},outputs={'bridge.json':sha(out/'bridge.json')}));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':run()
