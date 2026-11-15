from decimal import Decimal
from collections import Counter
import statistics
from common import *
def run():
 out=ROOT/'outputs/r87';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 old={(x['stock_code'],x['fiscal_year']):x for x in json.loads((ROOT/'outputs/r86/company_pairs.json').read_text())};rows=json.loads((out/'company_metrics.json').read_text());seen=set()
 for x in rows:
  key=x['stock_code'],x['fiscal_year'];assert key in old and key not in seen;seen.add(key);v=old[key]
  for field in ['june_forecast','december_forecast','actual_profit_cny','paired_brokers']:assert x[field]==v[field]
  known=all(v[k] is not None for k in ['june_forecast','december_forecast','actual_profit_cny'])
  if not known:
   assert x['amount_class']=='unknown' and x['change_cny'] is None and x['fixed_error_change'] is None;continue
  a,b,r=[Decimal(str(v[k])) for k in ['june_forecast','december_forecast','actual_profit_cny']];e0=abs(a-r);e1=abs(b-r);delta=e1-e0;scale=abs(a)+abs(r)
  for field,val in [('scale',scale),('june_error_cny',e0),('december_error_cny',e1),('change_cny',delta)]:assert np.isclose(x[field],float(val),atol=.001)
  for field,val in [('june_fixed_error',e0),('december_fixed_error',e1),('fixed_error_change',delta)]:assert x[field] is None if scale==0 else np.isclose(x[field],float(val/scale),atol=1e-12)
  label='improved' if delta<Decimal('-.01') else 'worsened' if delta>Decimal('.01') else 'unchanged';assert x['amount_class']==label
  z=v['absolute_error_change'];label='unknown' if z is None else 'improved' if z<-1e-12 else 'worsened' if z>1e-12 else 'unchanged';assert x['symmetric_class']==label
  assert x['opposite_sign_both']==(a*r<0 and b*r<0)
 assert seen==set(old)
 for s in json.loads((out/'summary.json').read_text()):
  allrows=[x for x in rows if x['fiscal_year']==s['fiscal_year']];q=[x for x in allrows if x['change_cny'] is not None];assert s['company_years']==len(allrows) and s['amount_evaluable']==len(q) and s['fixed_evaluable']==sum(x['fixed_error_change'] is not None for x in q)
  for target,source in [('june_mean_cny','june_error_cny'),('december_mean_cny','december_error_cny'),('mean_change_cny','change_cny'),('june_mean_fixed','june_fixed_error'),('december_mean_fixed','december_fixed_error'),('mean_change_fixed','fixed_error_change')]:assert np.isclose(s[target],statistics.mean(x[source] for x in q if x[source] is not None))
  assert s['amount_classes']==dict(Counter(x['amount_class'] for x in q));assert s['classification_changes']==sum(x['amount_class']!=x['symmetric_class'] for x in q)
 assert json.loads((out/'changed_cases.json').read_text())==[x for x in rows if x['amount_class']!=x['symmetric_class']]
 matrix={(x['symmetric_class'],x['amount_class']):x['rows'] for x in json.loads((out/'classification_matrix.json').read_text())};assert matrix==dict(Counter((x['symmetric_class'],x['amount_class']) for x in rows))
 # Explicit opposite-sign saturation counterexample.
 assert abs((10-(-5))/(abs(10)+abs(-5)))==abs((2-(-5))/(abs(2)+abs(-5)))==1
 assert abs(2-(-5))<abs(10-(-5))
 js(out/'verification.json',dict(status='PASS',company_years=len(rows),paired=sum(x['change_cny'] is not None for x in rows),scope='all fixed forecasts and decimal monetary distances, all yearly summaries and changed cases; saturation counterexample',verifier_sha256=sha(Path(__file__)),receipt_sha256=sha(out/'receipt.json')))
 print('R87 VERIFIED',len(rows))
if __name__=='__main__':run()
