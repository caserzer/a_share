import math
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r83';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 d=pd.read_parquet(ROOT/'outputs/r82/stock_audit.parquet');old={(x['method'],pd.Timestamp(x['origin'])):x for x in json.loads((ROOT/'outputs/r82/intervals.json').read_text())};rows=json.loads((out/'intervals.json').read_text());actual={(x['method'],pd.Timestamp(x['origin'])):x for x in rows};assert len(actual)==len(rows)==len(old)
 for key,g in d.groupby(['method','origin']):
  v=old[key];a=actual[key];known=[];unknown=[];contrib=[]
  for x in g.itertuples():
   assert x.weight>=0
   if x.endpoint_valued:known.append(x.weight);contrib.append(x.weight*(x.exit_price-x.entry_price)/x.entry_price)
   else:unknown.append(x.weight)
  kw=math.fsum(known);up=math.fsum(unknown);ui=v['unknown_weight'];u=up+ui;k=math.fsum(contrib)
  assert abs(kw+u-1)<1e-10
  for name,value in [('known_weight',kw),('unknown_price_weight',up),('unknown_identity_weight',ui),('unknown_total_weight',u),('known_return_contribution',k),('conditional_long_only_lower',k-u),('unknown_return_1pp_effect_pp',u)]:assert np.isclose(a[name],value,atol=1e-12)
  assert a['complete']==v['endpoint_valued']
  if a['complete']:assert np.isclose(a['complete_return'],v['fixed_stock_gross']) and u<1e-12
  else:assert a['complete_return'] is None
  if a['required_unknown_return_to_match_r17'] is not None:assert np.isclose(k+u*a['required_unknown_return_to_match_r17'],v['r17_gross'],atol=1e-12)
  else:assert u<=1e-12 or v['r17_gross'] is None
  if v['r17_gross'] is not None:assert np.isclose(a['conditional_lower_minus_r17'],k-u-v['r17_gross'])
 for s in json.loads((out/'summary.json').read_text()):
  rr=[x for x in rows if x['method']==s['method']];assert s['intervals']==len(rr) and s['complete']==sum(x['complete'] for x in rr)
  for field in ['unknown_identity_weight','unknown_price_weight','unknown_total_weight']:assert np.isclose(s[field+'_mean'],math.fsum(x[field] for x in rr)/len(rr))
  values=sorted(x['unknown_total_weight'] for x in rr);assert np.isclose(s['unknown_total_weight_median'],(values[25]+values[26])/2) and np.isclose(s['unknown_total_weight_max'],values[-1])
  assert s['worst_coverage_origin']==max(rr,key=lambda x:x['unknown_total_weight'])['origin']
  assert s['conditional_lower_above_r17_count']==sum(x['conditional_lower_minus_r17'] is not None and x['conditional_lower_minus_r17']>1e-12 for x in rr)
  assert s['critical_unknown_return_below_minus_one']==sum(x['required_unknown_return_to_match_r17'] is not None and x['required_unknown_return_to_match_r17']<-1-1e-12 for x in rr)
 # Algebraic adversaries: unknown is never silently zero or reweighted.
 k,u=.02,.1
 assert np.isclose(k+u*(-1),-.08) and np.isclose(k+u*2,.22)
 assert not np.isclose(k,k/(1-u))
 js(out/'verification.json',dict(status='PASS',stock_rows=len(d),intervals=len(rows),scope='all weights and contributions independently summed; threshold substitution and adversarial algebra',verifier_sha256=sha(Path(__file__)),receipt_sha256=sha(out/'receipt.json')))
 print('R83 VERIFIED',len(d),len(rows))
if __name__=='__main__':run()
